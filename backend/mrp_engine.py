"""
JDK Smart Factory Platform — MRP Engine
Hardened: typed config, validated inputs, cumulative ATP simulation, cost estimation.
"""

from dataclasses import dataclass, fields as dc_fields
from math import ceil
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class MRPConfig:
    batch_size_kg: float = 1000.0
    normalize_formulas: bool = True
    include_finished_goods_stock: bool = True
    default_bags_per_pallet: int = 50
    planning_horizon_days: int = 30
    daily_production_capacity_kg: float = 20000.0

    @classmethod
    def from_dict(cls, d: dict) -> "MRPConfig":
        """Safe constructor — ignores unknown keys instead of crashing."""
        valid = {f.name for f in dc_fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ── Constants ─────────────────────────────────────────────────────────────────

UNIT_ALIASES: Dict[str, str] = {
    "bags": "bags", "bag": "bags",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "tons": "tons", "ton": "tons", "tonne": "tons", "tonnes": "tons",
}

PRIORITY_ORDER: Dict[str, int] = {
    "Critical": 0, "High": 1, "Normal": 2, "Low": 3,
}

STATUS_TERMINAL = frozenset({"Shipped", "Closed", "Cancelled"})

FEASIBILITY_READY    = "READY FOR SHIPMENT"
FEASIBILITY_PRODUCE  = "CAN PRODUCE"
FEASIBILITY_SHORTAGE = "RAW MATERIAL SHORTAGE"


# ── Exception ─────────────────────────────────────────────────────────────────

class MRPValidationError(ValueError):
    pass


# ── Engine ────────────────────────────────────────────────────────────────────

class MRPEngine:
    def __init__(self, master: dict) -> None:
        self.master        = master
        self.config        = MRPConfig.from_dict(master.get("config", {}))
        self.products:  dict = master.get("products", {})
        self.raw_materials: dict = master.get("raw_materials", {})
        self.inventory: dict = master.get("inventory", {})
        self.finished_goods: dict = master.get("finished_goods", {})
        self.suppliers: dict = master.get("suppliers", {})

    # ── Unit helpers ──────────────────────────────────────────────────────────

    def _resolve_unit(self, unit: str) -> str:
        key = str(unit).lower().strip()
        resolved = UNIT_ALIASES.get(key)
        if resolved is None:
            raise MRPValidationError(
                f"Unknown unit '{unit}'. Accepted: bags, kg, tons."
            )
        return resolved

    def _to_kg(
        self,
        product: str,
        qty: float,
        unit: str,
        bag_size: Optional[float] = None,
    ) -> Tuple[float, float]:
        """Return (qty_kg, effective_bag_size_kg). Raises MRPValidationError on bad input."""
        if product not in self.products:
            raise MRPValidationError(f"Product '{product}' not found in master data.")

        qty = float(qty)
        if qty < 0:
            raise MRPValidationError(f"Quantity cannot be negative (got {qty}).")

        # bag_size=0 or None → fall back to product default
        bs = float(bag_size) if bag_size else 0.0
        if bs <= 0:
            bs = float(self.products[product].get("default_bag_size_kg", 25))
        if bs <= 0:
            raise MRPValidationError(f"Bag size must be positive (got {bs}).")

        unit_key = self._resolve_unit(unit)
        if unit_key == "bags":
            return qty * bs, bs
        if unit_key == "kg":
            return qty, bs
        if unit_key == "tons":
            return qty * 1_000.0, bs
        raise MRPValidationError(f"Unhandled unit after resolve: {unit_key}")

    # ── Formula helpers ───────────────────────────────────────────────────────

    def _ratios(self, formula: dict) -> Dict[str, float]:
        """Normalize formula dict to ratios that sum to 1.0."""
        if not formula:
            raise MRPValidationError("Formula is empty.")
        total = sum(float(v) for v in formula.values())
        if total <= 0:
            raise MRPValidationError("Formula percentages must sum to a positive value.")
        if self.config.normalize_formulas:
            return {k: float(v) / total for k, v in formula.items()}
        return {k: float(v) / 100.0 for k, v in formula.items()}

    def formula_total(self, product: str) -> float:
        formula = self.products.get(product, {}).get("formula", {})
        return sum(float(v) for v in formula.values())

    # ── Reservation helpers ───────────────────────────────────────────────────

    def open_reservations_by_product(
        self, orders: List[dict]
    ) -> Dict[str, float]:
        reserved: Dict[str, float] = {}
        for o in orders:
            if o.get("status", "Open") in STATUS_TERMINAL:
                continue
            product = o.get("product", "")
            kg = float(o.get("reserved_fg_kg", 0))
            reserved[product] = reserved.get(product, 0.0) + kg
        return reserved

    # ── Cost helpers ──────────────────────────────────────────────────────────

    def _cheapest_supplier_price(self, material: str) -> Optional[float]:
        sups = self.suppliers.get(material, [])
        prices = [float(s["price"]) for s in sups if "price" in s]
        return min(prices) if prices else None

    def _production_material_cost(
        self, product: str, planned_kg: float
    ) -> Tuple[float, List[dict]]:
        formula = self.products.get(product, {}).get("formula", {})
        if not formula or planned_kg <= 0:
            return 0.0, []
        ratios = self._ratios(formula)
        cost_rows: List[dict] = []
        total_cost = 0.0
        for mat, ratio in ratios.items():
            required  = planned_kg * ratio
            price     = self._cheapest_supplier_price(mat) or 0.0
            line_cost = required * price
            total_cost += line_cost
            cost_rows.append({
                "material":    mat,
                "required_kg": round(required, 3),
                "unit_price":  price,
                "line_cost":   round(line_cost, 2),
            })
        return round(total_cost, 2), cost_rows

    # ── Single-order feasibility ──────────────────────────────────────────────

    def feasibility_single_order(
        self,
        order: dict,
        existing_orders: Optional[List[dict]] = None,
    ) -> Tuple[dict, pd.DataFrame]:
        existing_orders = existing_orders or []
        product = order.get("product", "")
        if not product:
            raise MRPValidationError("Order must specify a product.")

        qty_kg, bag_size = self._to_kg(
            product,
            order.get("quantity", 0),
            order.get("unit", "kg"),
            order.get("bag_size_kg"),
        )

        # ── Finished goods ATP ────────────────────────────────────────────────
        fg_stock = float(self.finished_goods.get(product, {}).get("available_kg", 0))
        reserved = self.open_reservations_by_product(existing_orders).get(product, 0.0)
        atp_kg   = max(fg_stock - reserved, 0.0)

        shipment_ready_kg      = min(atp_kg, qty_kg)
        production_required_kg = max(qty_kg - shipment_ready_kg, 0.0)

        batches = (
            ceil(production_required_kg / self.config.batch_size_kg)
            if production_required_kg > 0 else 0
        )
        planned_production_kg = batches * self.config.batch_size_kg

        # ── Raw material check ────────────────────────────────────────────────
        material_rows: List[dict] = []
        limiting_material = ""
        can_produce       = True
        max_lead_time     = 0.0

        if planned_production_kg > 0:
            formula = self.products[product].get("formula", {})
            if not formula:
                can_produce       = False
                limiting_material = "No formula configured"
            else:
                ratios = self._ratios(formula)
                for mat, ratio in ratios.items():
                    required = planned_production_kg * ratio
                    stock    = float(self.inventory.get(mat, {}).get("current_stock", 0))
                    shortage = max(required - stock, 0.0)
                    lead     = float(self.inventory.get(mat, {}).get("lead_time_days", 0))
                    price    = self._cheapest_supplier_price(mat)

                    if shortage > 0:
                        can_produce = False
                        if not limiting_material:
                            limiting_material = mat
                        max_lead_time = max(max_lead_time, lead)

                    material_rows.append({
                        "material":       mat,
                        "required_qty":   round(required, 3),
                        "current_stock":  stock,
                        "shortage_qty":   round(shortage, 3),
                        "lead_time_days": lead,
                        "unit_price":     price if price is not None else None,
                        "status":         "SHORTAGE" if shortage > 0 else "OK",
                    })

                # Packaging bags (separate constraint)
                bags_needed = ceil(planned_production_kg / bag_size)
                bag_stock   = float(self.inventory.get("Packaging bags", {}).get("current_stock", 0))
                bag_short   = max(bags_needed - bag_stock, 0)
                bag_lead    = float(self.inventory.get("Packaging bags", {}).get("lead_time_days", 0))
                bag_price   = self._cheapest_supplier_price("Packaging bags")

                if bag_short > 0:
                    can_produce = False
                    if not limiting_material:
                        limiting_material = "Packaging bags"
                    max_lead_time = max(max_lead_time, bag_lead)

                material_rows.append({
                    "material":       "Packaging bags",
                    "required_qty":   bags_needed,
                    "current_stock":  bag_stock,
                    "shortage_qty":   bag_short,
                    "lead_time_days": bag_lead,
                    "unit_price":     bag_price if bag_price is not None else None,
                    "status":         "SHORTAGE" if bag_short > 0 else "OK",
                })

        # ── Cost ──────────────────────────────────────────────────────────────
        material_cost, _ = self._production_material_cost(product, planned_production_kg)

        # ── Timing & status ───────────────────────────────────────────────────
        daily_cap = self.config.daily_production_capacity_kg or 20_000.0
        production_days = (
            ceil(planned_production_kg / daily_cap)
            if planned_production_kg > 0 else 0
        )
        today = date.today()

        if production_required_kg == 0:
            earliest          = today
            feasibility_status = FEASIBILITY_READY
        elif can_produce:
            earliest          = today + timedelta(days=production_days)
            feasibility_status = FEASIBILITY_PRODUCE
        else:
            earliest          = today + timedelta(days=int(max_lead_time) + production_days)
            feasibility_status = FEASIBILITY_SHORTAGE

        summary = {
            "product":                      product,
            "customer":                     order.get("customer", ""),
            "order_qty":                    order.get("quantity", 0),
            "unit":                         order.get("unit", "kg"),
            "bag_size_kg":                  bag_size,
            "order_demand_kg":              qty_kg,
            "finished_goods_stock_kg":      fg_stock,
            "reserved_existing_orders_kg":  reserved,
            "available_to_promise_kg":      atp_kg,
            "shipment_ready_kg":            shipment_ready_kg,
            "production_required_kg":       production_required_kg,
            "batches_required":             batches,
            "planned_production_kg":        planned_production_kg,
            "raw_materials_available":      "YES" if can_produce else "NO",
            "limiting_material":            limiting_material,
            "estimated_production_days":    production_days,
            "earliest_delivery_date":       str(earliest),
            "estimated_material_cost":      material_cost,
            "feasibility_status":           feasibility_status,
        }
        return summary, pd.DataFrame(material_rows)

    # ── Full MRP run ──────────────────────────────────────────────────────────

    def run_fulfillment_mrp(self, orders: List[dict]) -> Dict[str, pd.DataFrame]:
        rows: List[dict] = []
        material_details: List[pd.DataFrame] = []
        virtual_fg_reserved: List[dict] = []

        active_orders = [
            o for o in orders
            if o.get("status", "Open") not in STATUS_TERMINAL
        ]
        sorted_orders = sorted(
            active_orders,
            key=lambda x: (
                PRIORITY_ORDER.get(x.get("priority", "Normal"), 2),
                x.get("delivery_date", "9999-12-31"),
            ),
        )

        simulated_existing: List[dict] = []
        for idx, o in enumerate(sorted_orders, 1):
            summary, detail = self.feasibility_single_order(o, simulated_existing)
            summary["order_no"]               = o.get("order_no", f"SO-{idx:04d}")
            summary["priority"]               = o.get("priority", "Normal")
            summary["delivery_date_requested"]= o.get("delivery_date", "")
            rows.append(summary)

            if not detail.empty:
                d = detail.copy()
                d.insert(0, "order_no", summary["order_no"])
                d.insert(1, "product",  summary["product"])
                material_details.append(d)

            simulated_existing.append({
                **o,
                "reserved_fg_kg": summary["shipment_ready_kg"],
                "status":         o.get("status", "Open"),
            })
            virtual_fg_reserved.append({
                "order_no":       summary["order_no"],
                "product":        summary["product"],
                "reserved_fg_kg": summary["shipment_ready_kg"],
            })

        fulfill = pd.DataFrame(rows) if rows else pd.DataFrame()

        if material_details:
            material_detail = pd.concat(material_details, ignore_index=True)
        else:
            material_detail = pd.DataFrame(columns=[
                "order_no", "product", "material",
                "required_qty", "current_stock", "shortage_qty",
                "lead_time_days", "unit_price", "status",
            ])

        if not material_detail.empty:
            summary_req = (
                material_detail
                .groupby("material", as_index=False)["required_qty"]
                .sum()
                .sort_values("required_qty", ascending=False)
                .reset_index(drop=True)
            )
            summary_req["current_stock"] = summary_req["material"].map(
                lambda m: self.inventory.get(m, {}).get("current_stock", 0)
            )
            summary_req["net_shortage"] = (
                summary_req["required_qty"] - summary_req["current_stock"]
            ).clip(lower=0)
        else:
            summary_req = pd.DataFrame(
                columns=["material", "required_qty", "current_stock", "net_shortage"]
            )

        # ── Reorder alerts ────────────────────────────────────────────────────
        reorder_rows: List[dict] = []
        for mat, inv in self.inventory.items():
            stock   = float(inv.get("current_stock", 0))
            reorder = float(inv.get("reorder_point", 0))
            minimum = float(inv.get("minimum_stock", 0))
            if stock <= reorder:
                severity = "CRITICAL" if stock <= minimum else "WARNING"
                reorder_rows.append({
                    "material":       mat,
                    "current_stock":  stock,
                    "reorder_point":  reorder,
                    "minimum_stock":  minimum,
                    "lead_time_days": inv.get("lead_time_days", 0),
                    "severity":       severity,
                })

        if reorder_rows:
            # Sort CRITICAL before WARNING
            reorder_df = pd.DataFrame(reorder_rows).sort_values("severity")
        else:
            reorder_df = pd.DataFrame(columns=[
                "material", "current_stock", "reorder_point",
                "minimum_stock", "lead_time_days", "severity",
            ])

        return {
            "order_feasibility":              fulfill,
            "order_material_detail":          material_detail,
            "raw_material_requirements_summary": summary_req,
            "fg_reservations":                pd.DataFrame(virtual_fg_reserved),
            "reorder_alerts":                 reorder_df,
        }

    # ── Inventory health snapshot ─────────────────────────────────────────────

    def inventory_health(self) -> pd.DataFrame:
        rows = []
        for mat, inv in self.inventory.items():
            stock   = float(inv.get("current_stock", 0))
            minimum = float(inv.get("minimum_stock", 0))
            reorder = float(inv.get("reorder_point", 0))
            lead    = float(inv.get("lead_time_days", 0))

            pct = round(stock / reorder * 100, 1) if reorder > 0 else 100.0

            if stock <= minimum:
                status = "CRITICAL"
            elif stock <= reorder:
                status = "LOW"
            else:
                status = "OK"

            rows.append({
                "material":           mat,
                "current_stock":      stock,
                "minimum_stock":      minimum,
                "reorder_point":      reorder,
                "stock_vs_reorder_%": pct,
                "lead_time_days":     lead,
                "status":             status,
            })

        if not rows:
            return pd.DataFrame(columns=[
                "material", "current_stock", "minimum_stock",
                "reorder_point", "stock_vs_reorder_%", "lead_time_days", "status",
            ])

        # Sort: CRITICAL → LOW → OK
        order_map = {"CRITICAL": 0, "LOW": 1, "OK": 2}
        df = pd.DataFrame(rows)
        df["_sort"] = df["status"].map(order_map)
        return df.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

    # ── Excel export ──────────────────────────────────────────────────────────

    def export_excel(self, reports: Dict[str, pd.DataFrame], path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            wb = writer.book

            hdr_fmt = wb.add_format({
                "bold": True, "bg_color": "#0f1f3d",
                "font_color": "#FFFFFF", "border": 1, "font_size": 10,
            })
            ok_fmt   = wb.add_format({"bg_color": "#d4edda", "border": 1})
            warn_fmt = wb.add_format({"bg_color": "#fff3cd", "border": 1})
            err_fmt  = wb.add_format({"bg_color": "#f8d7da", "border": 1})

            for sheet_name, df in reports.items():
                if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                    continue

                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)
                ws = writer.sheets[safe_name]

                # Re-write header row with formatting
                for ci, col in enumerate(df.columns):
                    ws.write(0, ci, col, hdr_fmt)

                # Auto-width columns
                for ci, col in enumerate(df.columns):
                    try:
                        max_data = df[col].astype(str).str.len().max()
                        col_w = max(len(str(col)), int(max_data) if pd.notna(max_data) else 0)
                    except Exception:
                        col_w = len(str(col))
                    ws.set_column(ci, ci, min(col_w + 3, 45))

                # Conditional row colouring for status columns
                status_col_idx = None
                if "status" in df.columns:
                    status_col_idx = df.columns.get_loc("status")
                elif "severity" in df.columns:
                    status_col_idx = df.columns.get_loc("severity")

                if status_col_idx is not None:
                    for ri, val in enumerate(df.iloc[:, status_col_idx].astype(str), start=1):
                        v = val.upper()
                        fmt = (
                            err_fmt  if v in ("SHORTAGE", "CRITICAL", "RAW MATERIAL SHORTAGE") else
                            warn_fmt if v in ("LOW", "WARNING") else
                            ok_fmt   if v in ("OK", "READY FOR SHIPMENT", "CAN PRODUCE") else
                            None
                        )
                        if fmt:
                            for ci in range(len(df.columns)):
                                try:
                                    cell_val = df.iloc[ri - 1, ci]
                                    ws.write(ri, ci, cell_val, fmt)
                                except Exception:
                                    pass

        return path
