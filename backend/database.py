"""
database.py — MySQL connection pool and query helpers for JDK Smart Factory.

All functions return plain Python dicts/lists so the rest of the app
doesn't need to know anything about the DB driver.

Config is read from environment variables (loaded from .env by app.py):
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_CHARSET
"""

import os
import json
import hashlib
from contextlib import contextmanager
from typing import Any

import pymysql
import pymysql.cursors
from pymysql import OperationalError, IntegrityError, ProgrammingError

# ── Connection pool (simple persistent connection per-process) ───────────────
_pool: list = []
_MAX_POOL = 5


def _cfg() -> dict:
    return dict(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "jdk_factory"),
        charset=os.environ.get("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


def _new_conn():
    return pymysql.connect(**_cfg())


@contextmanager
def get_conn():
    """Yield a live connection; return it to the pool after use."""
    conn = None
    if _pool:
        conn = _pool.pop()
        try:
            conn.ping(reconnect=True)
        except Exception:
            conn = None
    if conn is None:
        conn = _new_conn()
    try:
        yield conn
    finally:
        if len(_pool) < _MAX_POOL:
            _pool.append(conn)
        else:
            conn.close()


def query(sql: str, params=None) -> list[dict]:
    """Run a SELECT and return all rows as list of dicts."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def execute(sql: str, params=None) -> int:
    """Run INSERT/UPDATE/DELETE; return lastrowid or rowcount."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid or cur.rowcount


def executemany(sql: str, rows: list) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
            return cur.rowcount


def is_available() -> bool:
    """Return True if MySQL is reachable with current config."""
    try:
        with get_conn() as conn:
            conn.ping()
        return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════════════ #
#  Domain helpers — one section per entity                                    #
# ════════════════════════════════════════════════════════════════════════════ #

# ── Users ────────────────────────────────────────────────────────────────────

def _sha256(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_user(username: str) -> dict | None:
    rows = query("SELECT * FROM users WHERE username=%s", (username,))
    return rows[0] if rows else None


def get_all_users() -> list[dict]:
    return query("SELECT id, username, role, created_at FROM users")


def create_user(username: str, password: str, role: str = "viewer") -> bool:
    try:
        execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
            (username, _sha256(password), role),
        )
        return True
    except IntegrityError:
        return False


def set_reset_token(username: str, token: str):
    execute("UPDATE users SET reset_token=%s WHERE username=%s", (token, username))


def reset_password_by_token(token: str, new_pw: str) -> bool:
    rows = query("SELECT username FROM users WHERE reset_token=%s", (token,))
    if not rows:
        return False
    execute(
        "UPDATE users SET password_hash=%s, reset_token=NULL WHERE reset_token=%s",
        (_sha256(new_pw), token),
    )
    return True


def check_password(username: str, password: str) -> dict | None:
    row = get_user(username)
    if row and row.get("password_hash") == _sha256(password):
        return {"username": row["username"], "role": row["role"]}
    return None


# ── Settings ─────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    rows = query("SELECT key_name, val FROM settings")
    return {r["key_name"]: _try_json(r["val"]) for r in rows}


def save_settings(data: dict):
    for k, v in data.items():
        val = json.dumps(v) if not isinstance(v, str) else v
        execute(
            "INSERT INTO settings (key_name, val) VALUES (%s,%s) "
            "ON DUPLICATE KEY UPDATE val=%s",
            (k, val, val),
        )


# ── Factory Config ────────────────────────────────────────────────────────────

def get_config() -> dict:
    rows = query("SELECT key_name, val FROM factory_config")
    return {r["key_name"]: _try_num(r["val"]) for r in rows}


def set_config(key: str, value):
    val = str(value)
    execute(
        "INSERT INTO factory_config (key_name, val) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE val=%s",
        (key, val, val),
    )


# ── Customers ─────────────────────────────────────────────────────────────────

def get_customers() -> list[dict]:
    return query("SELECT * FROM customers ORDER BY customer")


def upsert_customer(data: dict):
    execute(
        "INSERT INTO customers (customer, email, phone, address) VALUES (%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE email=%s, phone=%s, address=%s",
        (
            data["customer"], data.get("email"), data.get("phone"), data.get("address"),
            data.get("email"), data.get("phone"), data.get("address"),
        ),
    )


def delete_customer(name: str):
    execute("DELETE FROM customers WHERE customer=%s", (name,))


# ── Products ──────────────────────────────────────────────────────────────────

def get_products() -> list[dict]:
    rows = query("SELECT * FROM products ORDER BY name")
    for r in rows:
        r["formula"] = _get_product_formula(r["name"])
    return rows


def get_product(name: str) -> dict | None:
    rows = query("SELECT * FROM products WHERE name=%s", (name,))
    if not rows:
        return None
    r = rows[0]
    r["formula"] = _get_product_formula(name)
    return r


def upsert_product(data: dict):
    execute(
        "INSERT INTO products (name, category, default_bag_size_kg, status) "
        "VALUES (%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE category=%s, default_bag_size_kg=%s, status=%s",
        (
            data["name"], data.get("category"), data.get("default_bag_size_kg", 50),
            data.get("status", "Active"),
            data.get("category"), data.get("default_bag_size_kg", 50),
            data.get("status", "Active"),
        ),
    )
    # Ensure finished_goods row exists
    execute(
        "INSERT IGNORE INTO finished_goods (product_name, available_kg, available_bags) "
        "VALUES (%s, 0, 0)",
        (data["name"],),
    )


def delete_product(name: str):
    execute("DELETE FROM products WHERE name=%s", (name,))


# ── Formulas (BOM) ────────────────────────────────────────────────────────────

def _get_product_formula(product_name: str) -> dict:
    rows = query(
        "SELECT material_name, percentage FROM product_formulas WHERE product_name=%s",
        (product_name,),
    )
    return {r["material_name"]: float(r["percentage"]) for r in rows}


def upsert_formula_line(product_name: str, material_name: str, percentage: float):
    execute(
        "INSERT INTO product_formulas (product_name, material_name, percentage) "
        "VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE percentage=%s",
        (product_name, material_name, percentage, percentage),
    )


def delete_formula_line(product_name: str, material_name: str):
    execute(
        "DELETE FROM product_formulas WHERE product_name=%s AND material_name=%s",
        (product_name, material_name),
    )


# ── Raw Materials ─────────────────────────────────────────────────────────────

def get_raw_materials() -> list[dict]:
    mats  = query("SELECT name, unit FROM raw_materials ORDER BY name")
    invs  = {r["material_name"]: r for r in query("SELECT * FROM inventory")}
    sups  = {}
    for r in query("SELECT * FROM suppliers ORDER BY supplier_name"):
        sups.setdefault(r["material_name"], []).append({
            k: v for k, v in r.items() if k != "material_name"
        })
    result = []
    for m in mats:
        inv = invs.get(m["name"], {})
        result.append({
            "name":           m["name"],
            "unit":           m["unit"],
            "current_stock":  float(inv.get("current_stock", 0)),
            "minimum_stock":  float(inv.get("minimum_stock", 0)),
            "reorder_point":  float(inv.get("reorder_point", 0)),
            "lead_time_days": int(inv.get("lead_time_days", 0)),
            "suppliers":      sups.get(m["name"], []),
        })
    return result


def upsert_raw_material(data: dict):
    name = data["name"]
    execute(
        "INSERT INTO raw_materials (name, unit) VALUES (%s,%s) "
        "ON DUPLICATE KEY UPDATE unit=%s",
        (name, data.get("unit", "kg"), data.get("unit", "kg")),
    )
    execute(
        "INSERT INTO inventory (material_name, current_stock, minimum_stock, reorder_point, lead_time_days) "
        "VALUES (%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE current_stock=%s, minimum_stock=%s, reorder_point=%s, lead_time_days=%s",
        (
            name,
            data.get("current_stock", 0), data.get("minimum_stock", 0),
            data.get("reorder_point", 0), data.get("lead_time_days", 0),
            data.get("current_stock", 0), data.get("minimum_stock", 0),
            data.get("reorder_point", 0), data.get("lead_time_days", 0),
        ),
    )


def delete_raw_material(name: str):
    execute("DELETE FROM raw_materials WHERE name=%s", (name,))


# ── Suppliers ─────────────────────────────────────────────────────────────────

def get_suppliers() -> dict:
    rows = query("SELECT * FROM suppliers ORDER BY material_name, supplier_name")
    result: dict = {}
    for r in rows:
        mat = r.pop("material_name")
        result.setdefault(mat, []).append(r)
    return result


def upsert_supplier(material_name: str, data: dict):
    execute(
        "INSERT INTO suppliers (material_name, supplier_name, price, lead_time_days, "
        "minimum_order_qty, payment_terms, delivery_cost) VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE price=%s, lead_time_days=%s, minimum_order_qty=%s, "
        "payment_terms=%s, delivery_cost=%s",
        (
            material_name, data["supplier_name"], data.get("price", 0),
            data.get("lead_time_days", 0), data.get("minimum_order_qty", 0),
            data.get("payment_terms"), data.get("delivery_cost", 0),
            data.get("price", 0), data.get("lead_time_days", 0),
            data.get("minimum_order_qty", 0), data.get("payment_terms"),
            data.get("delivery_cost", 0),
        ),
    )


def delete_supplier(material_name: str, supplier_name: str):
    execute(
        "DELETE FROM suppliers WHERE material_name=%s AND supplier_name=%s",
        (material_name, supplier_name),
    )


# ── Finished Goods ────────────────────────────────────────────────────────────

def get_finished_goods() -> dict:
    rows = query("SELECT product_name, available_kg, available_bags FROM finished_goods")
    return {
        r["product_name"]: {
            "available_kg":   float(r["available_kg"]),
            "available_bags": int(r["available_bags"]),
        }
        for r in rows
    }


def update_finished_goods(product_name: str, available_kg: float, available_bags: int):
    execute(
        "INSERT INTO finished_goods (product_name, available_kg, available_bags) "
        "VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE available_kg=%s, available_bags=%s",
        (product_name, available_kg, available_bags, available_kg, available_bags),
    )


# ── Orders ────────────────────────────────────────────────────────────────────

def get_orders(status_filter: str = None) -> list[dict]:
    sql = "SELECT * FROM customer_orders"
    params = ()
    if status_filter:
        sql += " WHERE status=%s"
        params = (status_filter,)
    sql += " ORDER BY created_at DESC"
    rows = query(sql, params)
    for r in rows:
        r["delivery_date"] = str(r["delivery_date"]) if r.get("delivery_date") else ""
        r["quantity_kg"]   = float(r["quantity_kg"])
        r["bag_size_kg"]   = float(r["bag_size_kg"])
    return rows


def create_order(data: dict) -> dict:
    execute(
        "INSERT INTO customer_orders "
        "(order_no, customer, product, quantity_kg, bag_size_kg, bags, delivery_date, status, notes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            data["order_no"], data["customer"], data["product"],
            data["quantity_kg"], data.get("bag_size_kg", 50),
            data.get("bags", 0), data.get("delivery_date") or None,
            data.get("status", "Pending"), data.get("notes", ""),
        ),
    )
    return data


def update_order(order_no: str, data: dict) -> bool:
    fields = {
        "customer": data.get("customer"), "product": data.get("product"),
        "quantity_kg": data.get("quantity_kg"), "bag_size_kg": data.get("bag_size_kg"),
        "bags": data.get("bags"), "delivery_date": data.get("delivery_date") or None,
        "status": data.get("status"), "notes": data.get("notes"),
    }
    sets   = ", ".join(f"{k}=%s" for k, v in fields.items() if v is not None)
    vals   = [v for v in fields.values() if v is not None]
    if not sets:
        return False
    execute(f"UPDATE customer_orders SET {sets} WHERE order_no=%s", (*vals, order_no))
    return True


def delete_order(order_no: str):
    execute("DELETE FROM customer_orders WHERE order_no=%s", (order_no,))


# ── Production Schedules ──────────────────────────────────────────────────────

def get_schedules(status_filter: str = None) -> list[dict]:
    sql = "SELECT * FROM production_schedules"
    params = ()
    if status_filter:
        sql += " WHERE status=%s"
        params = (status_filter,)
    sql += " ORDER BY start_date"
    rows = query(sql, params)
    for r in rows:
        r["start_date"]         = str(r["start_date"])
        r["end_date"]           = str(r["end_date"])
        r["planned_qty_kg"]     = float(r["planned_qty_kg"])
        r["manpower_available"] = int(r["manpower_available"])
        r["manpower_required"]  = int(r["manpower_required"])
    return rows


def create_schedule(data: dict) -> dict:
    execute(
        "INSERT INTO production_schedules "
        "(schedule_id, product, planned_qty_kg, start_date, end_date, shift, "
        "manpower_available, manpower_required, status, linked_order_no, notes, created_by) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            data["schedule_id"], data["product"], data["planned_qty_kg"],
            data["start_date"], data["end_date"], data.get("shift", "Day"),
            data.get("manpower_available", 0), data.get("manpower_required", 0),
            data.get("status", "Planned"), data.get("linked_order_no") or None,
            data.get("notes", ""), data.get("created_by", ""),
        ),
    )
    return data


def update_schedule(schedule_id: str, data: dict) -> bool:
    allowed = {
        "product", "planned_qty_kg", "start_date", "end_date", "shift",
        "manpower_available", "manpower_required", "status", "linked_order_no", "notes",
    }
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return False
    sets  = ", ".join(f"{k}=%s" for k in updates)
    vals  = list(updates.values())
    execute(f"UPDATE production_schedules SET {sets} WHERE schedule_id=%s", (*vals, schedule_id))
    return True


def delete_schedule(schedule_id: str):
    execute("DELETE FROM production_schedules WHERE schedule_id=%s", (schedule_id,))


# ── Master data dict (for MRPEngine compatibility) ────────────────────────────

def build_master() -> dict:
    """
    Reconstruct the master_data dict that MRPEngine expects,
    entirely from MySQL.
    """
    cfg   = get_config()
    prods = {p["name"]: {
        "category":           p.get("category", ""),
        "default_bag_size_kg": float(p.get("default_bag_size_kg", 50)),
        "status":             p.get("status", "Active"),
        "formula":            p.get("formula", {}),
    } for p in get_products()}

    mats_rows = query("SELECT name, unit FROM raw_materials")
    raw_mats  = {r["name"]: {"unit": r["unit"]} for r in mats_rows}

    inv_rows  = query("SELECT * FROM inventory")
    inventory = {r["material_name"]: {
        "current_stock":  float(r["current_stock"]),
        "minimum_stock":  float(r["minimum_stock"]),
        "reorder_point":  float(r["reorder_point"]),
        "lead_time_days": int(r["lead_time_days"]),
    } for r in inv_rows}

    fg        = get_finished_goods()
    sups_rows = query("SELECT * FROM suppliers")
    suppliers: dict = {}
    for r in sups_rows:
        mat = r["material_name"]
        suppliers.setdefault(mat, []).append({
            "supplier_name":     r["supplier_name"],
            "price":             float(r["price"]),
            "lead_time_days":    int(r["lead_time_days"]),
            "minimum_order_qty": float(r["minimum_order_qty"]),
            "payment_terms":     r.get("payment_terms") or "",
            "delivery_cost":     float(r["delivery_cost"]),
        })

    return {
        "config":         cfg,
        "products":       prods,
        "raw_materials":  raw_mats,
        "inventory":      inventory,
        "finished_goods": fg,
        "suppliers":      suppliers,
    }


# ── Migration helper — import existing JSON data into MySQL ───────────────────

def migrate_from_json(
    master: dict,
    orders: list,
    customers: list,
    users_data: dict | None = None,
):
    """
    One-time import of existing JSON flat files into MySQL.
    Safe to call multiple times (uses INSERT IGNORE / ON DUPLICATE KEY).
    """
    # Config
    for k, v in (master.get("config") or {}).items():
        set_config(k, v)

    # Customers
    for c in customers:
        upsert_customer(c)

    # Raw materials + inventory
    for name, mat in (master.get("raw_materials") or {}).items():
        inv = (master.get("inventory") or {}).get(name, {})
        upsert_raw_material({
            "name":           name,
            "unit":           mat.get("unit", "kg"),
            "current_stock":  inv.get("current_stock", 0),
            "minimum_stock":  inv.get("minimum_stock", 0),
            "reorder_point":  inv.get("reorder_point", 0),
            "lead_time_days": inv.get("lead_time_days", 0),
        })

    # Suppliers
    for mat_name, sup_list in (master.get("suppliers") or {}).items():
        for s in sup_list:
            upsert_supplier(mat_name, s)

    # Products + formulas
    for name, prod in (master.get("products") or {}).items():
        upsert_product({**prod, "name": name})
        for mat, pct in (prod.get("formula") or {}).items():
            upsert_formula_line(name, mat, pct)

    # Finished goods
    for name, fg in (master.get("finished_goods") or {}).items():
        update_finished_goods(name, fg.get("available_kg", 0), fg.get("available_bags", 0))

    # Orders
    for o in orders:
        try:
            create_order(o)
        except IntegrityError:
            pass  # already exists

    # Users (from auth.json)
    if users_data:
        for u in users_data.get("users", []):
            try:
                execute(
                    "INSERT IGNORE INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                    (u["username"], u["password_hash"], u.get("role", "viewer")),
                )
            except Exception:
                pass


# ── Utilities ─────────────────────────────────────────────────────────────────

def _try_json(s: str) -> Any:
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return s


def _try_num(s: str) -> Any:
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return s
