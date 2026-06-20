"""
JDK Smart Factory Platform — MRP Engine
Material Requirements Planning and ATP (Available-to-Promise) calculations.
"""

from dataclasses import dataclass, fields as dc_fields
from math import ceil
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from .models import (
    Product, RawMaterial, RawMaterialInventory, FinishedGoodsInventory,
    ProductFormula, Supplier, CustomerOrder, Customer
)


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
        valid = {f.name for f in dc_fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


UNIT_ALIASES: Dict[str, str] = {
    "bags": "bags", "bag": "bags",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "tons": "tons", "ton": "tons", "tonne": "tons", "tonnes": "tons",
}

PRIORITY_ORDER: Dict[str, int] = {
    "Critical": 0, "High": 1, "Normal": 2, "Low": 3,
}

STATUS_TERMINAL = frozenset({"Shipped", "Closed", "Cancelled"})

FEASIBILITY_READY = "READY FOR SHIPMENT"
FEASIBILITY_PRODUCE = "CAN PRODUCE"
FEASIBILITY_SHORTAGE = "RAW MATERIAL SHORTAGE"


class MRPValidationError(ValueError):
    pass


class MRPEngine:
    """MRP calculation engine using database session."""
    
    def __init__(self, db: Session, config: Optional[MRPConfig] = None):
        self.db = db
        self.config = config or MRPConfig()

    def _to_kg(self, product: Product, qty: float, unit: str, bag_size: Optional[float] = None) -> Tuple[float, float]:
        """Convert quantity to kg. Returns (qty_kg, effective_bag_size_kg)."""
        qty = float(qty)
        if qty < 0:
            raise MRPValidationError(f"Quantity cannot be negative (got {qty}).")

        bs = float(bag_size) if bag_size else 0.0
        if bs <= 0:
            bs = float(product.default_bag_size_kg or 25.0)
        if bs <= 0:
            raise MRPValidationError(f"Bag size must be positive (got {bs}).")

        unit_key = unit.lower().strip()
        unit_key = UNIT_ALIASES.get(unit_key, unit_key)
        
        if unit_key == "bags":
            return qty * bs, bs
        if unit_key == "kg":
            return qty, bs
        if unit_key == "tons":
            return qty * 1000.0, bs
        raise MRPValidationError(f"Unknown unit: {unit}")

    def _get_formula_ratios(self, product_id: int) -> Dict[str, float]:
        """Get formula ratios for a product."""
        formulas = self.db.query(ProductFormula).filter(
            ProductFormula.product_id == product_id
        ).all()
        
        if not formulas:
            return {}
        
        total = sum(f.percentage for f in formulas)
        if total <= 0:
            raise MRPValidationError("Formula percentages must sum to a positive value.")
        
        ratios = {}
        for f in formulas:
            material = self.db.query(RawMaterial).filter(RawMaterial.id == f.material_id).first()
            if material:
                if self.config.normalize_formulas:
                    ratios[material.material_name] = f.percentage / total
                else:
                    ratios[material.material_name] = f.percentage / 100.0
        return ratios

    def _get_inventory(self, material_name: str) -> Tuple[float, int]:
        """Get current stock and lead time for a material."""
        material = self.db.query(RawMaterial).filter(
            RawMaterial.material_name == material_name
        ).first()
        if not material:
            return 0.0, 0
        
        inv = self.db.query(RawMaterialInventory).filter(
            RawMaterialInventory.material_id == material.id
        ).first()
        if not inv:
            return 0.0, 0
        
        return inv.current_stock, inv.lead_time_days

    def _get_supplier_price(self, material_name: str) -> Optional[float]:
        """Get cheapest supplier price for a material."""
        material = self.db.query(RawMaterial).filter(
            RawMaterial.material_name == material_name
        ).first()
        if not material:
            return None
        
        suppliers = self.db.query(Supplier).filter(
            Supplier.material_id == material.id,
            Supplier.is_active == True
        ).all()
        
        if not suppliers:
            return None
        
        return min(s.price_per_unit for s in suppliers)

    def _get_finished_goods_atp(self, product_id: int, exclude_order_id: Optional[int] = None) -> float:
        """Calculate available-to-promise for finished goods."""
        fg = self.db.query(FinishedGoodsInventory).filter(
            FinishedGoodsInventory.product_id == product_id
        ).first()
        
        if not fg:
            return 0.0
        
        # Get reserved quantities from active orders
        query = self.db.query(CustomerOrder).filter(
            CustomerOrder.product_id == product_id,
            CustomerOrder.status.notin_(list(STATUS_TERMINAL))
        )
        if exclude_order_id:
            query = query.filter(CustomerOrder.id != exclude_order_id)
        
        orders = query.all()
        reserved = sum(o.reserved_fg_kg or 0.0 for o in orders)
        
        return max(fg.available_kg - reserved, 0.0)

    def feasibility_single_order(
        self,
        order: CustomerOrder,
        existing_orders: Optional[List[CustomerOrder]] = None,
    ) -> Tuple[dict, List[dict]]:
        """Calculate feasibility for a single order."""
        product = self.db.query(Product).filter(Product.id == order.product_id).first()
        if not product:
            raise MRPValidationError("Product not found for order.")
        
        customer = self.db.query(Customer).filter(Customer.id == order.customer_id).first()
        customer_name = customer.customer_name if customer else "Unknown"
        
        # Convert order quantity to kg
        qty_kg, bag_size = self._to_kg(product, order.quantity, order.unit, order.bag_size_kg)
        
        # Calculate ATP
        atp_kg = self._get_finished_goods_atp(order.product_id, exclude_order_id=order.id if existing_orders is None else None)
        
        # Determine how much can be shipped from stock
        shipment_ready_kg = min(atp_kg, qty_kg)
        production_required_kg = max(qty_kg - shipment_ready_kg, 0.0)
        
        # Calculate batches needed
        batches = ceil(production_required_kg / self.config.batch_size_kg) if production_required_kg > 0 else 0
        planned_production_kg = batches * self.config.batch_size_kg
        
        # Check raw materials
        material_rows = []
        limiting_material = ""
        can_produce = True
        max_lead_time = 0.0
        
        if planned_production_kg > 0:
            ratios = self._get_formula_ratios(product.id)
            if not ratios:
                can_produce = False
                limiting_material = "No formula configured"
            else:
                for mat_name, ratio in ratios.items():
                    required = planned_production_kg * ratio
                    stock, lead_time = self._get_inventory(mat_name)
                    shortage = max(required - stock, 0.0)
                    price = self._get_supplier_price(mat_name)
                    
                    if shortage > 0:
                        can_produce = False
                        if not limiting_material:
                            limiting_material = mat_name
                        max_lead_time = max(max_lead_time, lead_time)
                    
                    material_rows.append({
                        "material": mat_name,
                        "required_qty": round(required, 3),
                        "current_stock": stock,
                        "shortage_qty": round(shortage, 3),
                        "lead_time_days": lead_time,
                        "unit_price": price,
                        "status": "SHORTAGE" if shortage > 0 else "OK",
                    })
                
                # Check packaging bags
                bags_needed = ceil(planned_production_kg / bag_size)
                bag_stock, bag_lead = self._get_inventory("Packaging bags")
                bag_short = max(bags_needed - bag_stock, 0)
                bag_price = self._get_supplier_price("Packaging bags")
                
                if bag_short > 0:
                    can_produce = False
                    if not limiting_material:
                        limiting_material = "Packaging bags"
                    max_lead_time = max(max_lead_time, bag_lead)
                
                material_rows.append({
                    "material": "Packaging bags",
                    "required_qty": bags_needed,
                    "current_stock": bag_stock,
                    "shortage_qty": bag_short,
                    "lead_time_days": bag_lead,
                    "unit_price": bag_price,
                    "status": "SHORTAGE" if bag_short > 0 else "OK",
                })
        
        # Calculate material cost
        material_cost = 0.0
        if planned_production_kg > 0:
            ratios = self._get_formula_ratios(product.id)
            for mat_name, ratio in ratios.items():
                required = planned_production_kg * ratio
                price = self._get_supplier_price(mat_name) or 0.0
                material_cost += required * price
        
        # Calculate timing
        daily_cap = self.config.daily_production_capacity_kg or 20000.0
        production_days = ceil(planned_production_kg / daily_cap) if planned_production_kg > 0 else 0
        today = date.today()
        
        if production_required_kg == 0:
            earliest = today
            feasibility_status = FEASIBILITY_READY
        elif can_produce:
            earliest = today + timedelta(days=production_days)
            feasibility_status = FEASIBILITY_PRODUCE
        else:
            earliest = today + timedelta(days=int(max_lead_time) + production_days)
            feasibility_status = FEASIBILITY_SHORTAGE
        
        summary = {
            "order_no": order.order_no,
            "product": product.product_name,
            "customer": customer_name,
            "priority": order.priority.value if hasattr(order.priority, 'value') else str(order.priority),
            "order_qty": order.quantity,
            "unit": order.unit,
            "order_demand_kg": qty_kg,
            "shipment_ready_kg": shipment_ready_kg,
            "production_required_kg": production_required_kg,
            "planned_production_kg": planned_production_kg,
            "raw_materials_available": "YES" if can_produce else "NO",
            "limiting_material": limiting_material,
            "estimated_production_days": production_days,
            "earliest_delivery_date": str(earliest),
            "estimated_material_cost": round(material_cost, 2),
            "feasibility_status": feasibility_status,
        }
        
        return summary, material_rows

    def run_fulfillment_mrp(self, orders: Optional[List[CustomerOrder]] = None) -> dict:
        """Run MRP for all active orders."""
        if orders is None:
            orders = self.db.query(CustomerOrder).filter(
                CustomerOrder.status.notin_(list(STATUS_TERMINAL))
            ).all()
        
        # Sort by priority and delivery date
        sorted_orders = sorted(
            orders,
            key=lambda x: (
                PRIORITY_ORDER.get(x.priority.value if hasattr(x.priority, 'value') else str(x.priority), 2),
                x.delivery_date,
            ),
        )
        
        feasibility_rows = []
        all_material_details = []
        simulated_existing = []
        
        for order in sorted_orders:
            summary, detail = self.feasibility_single_order(order, simulated_existing)
            feasibility_rows.append(summary)
            all_material_details.extend(detail)
            
            # Add to simulated reservations
            simulated_existing.append(order)
        
        # Calculate summary requirements by material
        material_summary = {}
        for row in all_material_details:
            mat = row["material"]
            if mat not in material_summary:
                material_summary[mat] = {"required_qty": 0.0, "current_stock": row["current_stock"]}
            material_summary[mat]["required_qty"] += row["required_qty"]
        
        summary_requirements = [
            {
                "material": mat,
                "required_qty": round(data["required_qty"], 2),
                "current_stock": data["current_stock"],
                "net_shortage": round(max(data["required_qty"] - data["current_stock"], 0), 2),
            }
            for mat, data in material_summary.items()
        ]
        
        # Generate reorder alerts
        reorder_alerts = []
        inventory_items = self.db.query(RawMaterialInventory).all()
        for inv in inventory_items:
            material = self.db.query(RawMaterial).filter(RawMaterial.id == inv.material_id).first()
            if material and inv.current_stock <= inv.reorder_point:
                severity = "CRITICAL" if inv.current_stock <= inv.minimum_stock else "WARNING"
                reorder_alerts.append({
                    "material": material.material_name,
                    "current_stock": inv.current_stock,
                    "reorder_point": inv.reorder_point,
                    "minimum_stock": inv.minimum_stock,
                    "severity": severity,
                })
        
        return {
            "order_feasibility": feasibility_rows,
            "material_detail": all_material_details,
            "summary_requirement": summary_requirements,
            "reorder_alerts": reorder_alerts,
        }
