"""
JDK Smart Factory Platform — Flask REST API Backend
Storage: MySQL via database.py (PyMySQL). .env loaded at startup.
"""

import json
import os
import secrets
import time
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything reads os.environ
_ENV_FILE = Path(__file__).parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

import pandas as pd
from flask import Flask, jsonify, request, send_file, session
from flask_cors import CORS

import database as db
from mrp_engine import MRPEngine, MRPValidationError

# ── Paths (still needed for reports, secret key, backups) ─────────────────────
BASE    = Path(__file__).parent.parent
CONFIG  = BASE / "config"
REPORTS = BASE / "reports"
for p in (CONFIG, REPORTS):
    p.mkdir(parents=True, exist_ok=True)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

_KEY_FILE = CONFIG / ".secret_key"

def _get_or_create_secret_key():
    env_key = os.environ.get("SECRET_KEY", "")
    if env_key:
        return env_key
    try:
        if _KEY_FILE.exists():
            return _KEY_FILE.read_text().strip()
    except Exception:
        pass
    key = secrets.token_hex(32)
    try:
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEY_FILE.write_text(key)
    except Exception:
        pass
    return key

app.secret_key = _get_or_create_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
CORS(app, supports_credentials=True, origins=["*"])

STATUS_TERMINAL = frozenset({"Shipped", "Closed", "Cancelled"})
ROLE_PERMS = {
    "admin":              {"read", "write", "admin", "orders", "inventory"},
    "Super Admin":        {"read", "write", "admin", "orders", "inventory"},
    "Production Planner": {"read", "write", "orders"},
    "Warehouse User":     {"read", "inventory"},
    "Purchasing User":    {"read", "write"},
    "Management Viewer":  {"read"},
    "viewer":             {"read"},
    "write":              {"read", "write"},
    "operator":           {"read", "write", "inventory"},
    "manager":            {"read", "write", "orders", "inventory"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _engine():
    return MRPEngine(db.build_master())

def ok(data=None, **kwargs):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)

def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code

def df_to_list(df: pd.DataFrame):
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", default_handler=str))

# ── Auth decorators ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return err("Not authenticated", 401)
        return f(*args, **kwargs)
    return decorated

def require_perm(*perms):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user"):
                return err("Not authenticated", 401)
            role = session["user"].get("role", "")
            allowed = ROLE_PERMS.get(role, set())
            if not any(p in allowed for p in perms):
                return err("Insufficient permissions", 403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ════════════════════════════════════════════════════════════════════════════ #
#  AUTH                                                                        #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return err("Username and password required")
    user = db.check_password(username, password)
    if not user:
        return err("Invalid username or password", 401)
    session.permanent = True
    session["user"] = user
    return ok({"username": user["username"], "role": user["role"],
                "display_name": user.get("display_name", user["username"])})

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return err("Username and password required")
    if len(password) < 6:
        return err("Password must be at least 6 characters")
    if not db.create_user(username, password, role="viewer"):
        return err("Username already taken")
    return ok({"message": "Account created. Please log in."})

@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    if not username:
        return err("Username required")
    user = db.get_user(username)
    if not user:
        return err("No account found for that username")
    token = secrets.token_urlsafe(32)
    db.set_reset_token(username, token)
    return ok({"message": "Reset token issued.", "reset_token": token})

@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    body = request.get_json() or {}
    token    = body.get("token", "")
    password = body.get("password", "")
    if not token or not password:
        return err("Token and new password required")
    if len(password) < 6:
        return err("Password must be at least 6 characters")
    if not db.reset_password_by_token(token, password):
        return err("Invalid or expired reset token")
    return ok({"message": "Password updated. Please log in."})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return ok({"message": "Signed out"})

@app.route("/api/auth/me", methods=["GET"])
@login_required
def me():
    return ok(session["user"])


# ════════════════════════════════════════════════════════════════════════════ #
#  SETTINGS                                                                    #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    s = db.get_settings()
    safe = dict(s)
    if safe.get("deepseek_api_key"):
        safe["deepseek_api_key"] = "••••••••" + str(safe["deepseek_api_key"])[-4:]
    return ok(safe)

@app.route("/api/settings", methods=["POST"])
@require_perm("admin")
def save_settings():
    body = request.get_json() or {}
    current = db.get_settings()
    if "deepseek_api_key" in body and body["deepseek_api_key"] and not str(body["deepseek_api_key"]).startswith("••"):
        current["deepseek_api_key"] = body["deepseek_api_key"]
    for field in ("deepseek_model", "deepseek_base_url", "app_name",
                  "daily_capacity_kg", "batch_size_kg", "planning_horizon_days"):
        if field in body:
            current[field] = body[field]
    db.save_settings(current)
    return ok({"message": "Settings saved"})


# ════════════════════════════════════════════════════════════════════════════ #
#  AI CHAT                                                                     #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/chat", methods=["POST"])
@login_required
def ai_chat():
    import urllib.request as _req
    body    = request.get_json() or {}
    message = body.get("message", "").strip()
    history = body.get("history", [])
    if not message:
        return err("Message required")
    settings = db.get_settings()
    api_key  = settings.get("deepseek_api_key", "")
    if not api_key:
        return ok({"reply": "⚙️ No DeepSeek API key configured. Go to **Settings** to add your key.", "action": None})

    master    = db.build_master()
    products  = list(master.get("products", {}).keys())
    materials = list(master.get("raw_materials", {}).keys())
    orders    = db.get_orders()
    open_ord  = [o for o in orders if o.get("status") not in STATUS_TERMINAL]
    customers = db.get_customers()

    system_prompt = f"""You are the JDK Smart Factory AI assistant for a manufacturing ERP.
Current factory state:
- Products: {', '.join(products) or 'none'}
- Raw materials: {', '.join(materials) or 'none'}
- Open orders: {len(open_ord)}
- Customers: {len(customers)}
- User role: {session['user'].get('role', 'Unknown')}

Respond in 1-3 short paragraphs. Be direct and actionable.
If the user asks to DO something, end with: ACTION: {{"action": "navigate", "page": "orders"}}"""

    messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
                for m in history[-10:]]
    messages.append({"role": "user", "content": message})

    payload = json.dumps({
        "model": settings.get("deepseek_model", "deepseek-chat"),
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 600, "temperature": 0.7,
    }).encode()

    base_url = settings.get("deepseek_base_url", "https://api.deepseek.com")
    req = _req.Request(
        f"{base_url}/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with _req.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        raw    = result["choices"][0]["message"]["content"]
        action = None
        reply  = raw
        if "ACTION:" in raw:
            parts  = raw.split("ACTION:", 1)
            reply  = parts[0].strip()
            try:
                action = json.loads(parts[1].strip())
            except Exception:
                action = None
        return ok({"reply": reply, "action": action})
    except Exception as e:
        return err(f"AI error: {str(e)}", 502)


# ════════════════════════════════════════════════════════════════════════════ #
#  DASHBOARD                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    master    = db.build_master()
    orders    = db.get_orders()
    customers = db.get_customers()
    engine    = MRPEngine(master)
    open_ord  = [o for o in orders if o.get("status", "") not in STATUS_TERMINAL]
    inv_health= engine.inventory_health()
    crit_mats = df_to_list(inv_health[inv_health["status"] == "CRITICAL"]) if not inv_health.empty else []
    low_mats  = df_to_list(inv_health[inv_health["status"] == "LOW"])      if not inv_health.empty else []
    fg        = master.get("finished_goods", {})
    prods     = master.get("products", {})
    fg_rows   = [{"product": p, "category": prods.get(p, {}).get("category", "—"),
                  "available_kg": float(v.get("available_kg", 0)),
                  "available_bags": float(v.get("available_bags", 0)),
                  "status": "In Stock" if float(v.get("available_kg", 0)) > 0 else "Out of Stock"}
                 for p, v in fg.items()]
    return ok({
        "kpis": {
            "active_products":  len([p for p, d in prods.items() if d.get("status") == "Active"]),
            "customers":        len(customers),
            "open_orders":      len(open_ord),
            "suppliers":        sum(len(v) for v in master.get("suppliers", {}).values()),
            "stock_alerts":     len(crit_mats) + len(low_mats),
            "critical_stock":   len(crit_mats),
        },
        "finished_goods":     fg_rows,
        "inventory_health":   df_to_list(inv_health),
        "open_orders":        open_ord[:20],
        "alerts": {
            "critical_materials": [m["material"] for m in crit_mats],
            "low_materials":      [m["material"] for m in low_mats],
        },
    })


# ════════════════════════════════════════════════════════════════════════════ #
#  CUSTOMERS                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/customers", methods=["GET"])
@login_required
def get_customers():
    return ok(db.get_customers())

@app.route("/api/customers", methods=["POST"])
@require_perm("admin")
def add_customer():
    body = request.get_json() or {}
    name = body.get("customer", "").strip()
    if not name:
        return err("Customer name required")
    db.upsert_customer(body)
    return ok(db.get_customers())

@app.route("/api/customers/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_customer(name):
    db.delete_customer(name)
    return ok(db.get_customers())


# ════════════════════════════════════════════════════════════════════════════ #
#  PRODUCTS                                                                    #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    return ok(db.get_products())

@app.route("/api/products", methods=["POST"])
@require_perm("admin")
def upsert_product():
    body = request.get_json() or {}
    name = body.get("name", "").strip()
    if not name:
        return err("Product name required")
    db.upsert_product(body)
    return ok(db.get_product(name))

@app.route("/api/products/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_product(name):
    db.delete_product(name)
    return ok({"deleted": name})


# ════════════════════════════════════════════════════════════════════════════ #
#  FORMULAS                                                                    #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/formulas/<product>", methods=["GET"])
@login_required
def get_formula(product):
    p = db.get_product(product)
    if not p:
        return err("Product not found", 404)
    formula = p.get("formula", {})
    total   = sum(formula.values())
    rows    = [{"material": m, "percentage": pct} for m, pct in formula.items()]
    return ok({"formula": rows, "total": total, "balanced": 99.5 <= total <= 100.5})

@app.route("/api/formulas/<product>", methods=["POST"])
@require_perm("admin")
def upsert_formula_line(product):
    body = request.get_json() or {}
    mat  = body.get("material", "").strip()
    pct  = float(body.get("percentage", 0))
    if not mat or pct <= 0:
        return err("Material and positive percentage required")
    # Ensure the material exists
    db.upsert_raw_material({"name": mat, "unit": "kg"})
    db.upsert_formula_line(product, mat, pct)
    return ok({"material": mat, "percentage": pct})

@app.route("/api/formulas/<product>/<material>", methods=["DELETE"])
@require_perm("admin")
def delete_formula_line(product, material):
    db.delete_formula_line(product, material)
    return ok({"deleted": material})


# ════════════════════════════════════════════════════════════════════════════ #
#  RAW MATERIALS                                                               #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/raw-materials", methods=["GET"])
@login_required
def get_raw_materials():
    master = db.build_master()
    health = MRPEngine(master).inventory_health()
    return ok(df_to_list(health))

@app.route("/api/raw-materials", methods=["POST"])
@require_perm("admin")
def upsert_raw_material():
    body = request.get_json() or {}
    name = body.get("name", "").strip()
    if not name:
        return err("Material name required")
    db.upsert_raw_material(body)
    return ok({"name": name})

@app.route("/api/raw-materials/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_raw_material(name):
    db.delete_raw_material(name)
    return ok({"deleted": name})


# ════════════════════════════════════════════════════════════════════════════ #
#  SUPPLIERS                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    rows = []
    for mat, sups in db.get_suppliers().items():
        for s in sups:
            rows.append({"material": mat, **s})
    return ok(rows)

@app.route("/api/suppliers", methods=["POST"])
@require_perm("admin")
def add_supplier():
    body = request.get_json() or {}
    mat  = body.get("material", "").strip()
    name = body.get("supplier_name", "").strip()
    if not mat or not name:
        return err("Material and supplier name required")
    db.upsert_supplier(mat, body)
    return ok({"message": f"Supplier '{name}' saved for {mat}"})

@app.route("/api/suppliers/<material>/<supplier_name>", methods=["DELETE"])
@require_perm("admin")
def delete_supplier(material, supplier_name):
    db.delete_supplier(material, supplier_name)
    return ok({"deleted": supplier_name})


# ════════════════════════════════════════════════════════════════════════════ #
#  INVENTORY                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/inventory/finished-goods", methods=["GET"])
@login_required
def get_fg():
    fg    = db.get_finished_goods()
    prods = {p["name"]: p for p in db.get_products()}
    rows  = [{"product": p, "category": prods.get(p, {}).get("category", "—"),
               "available_kg": float(v.get("available_kg", 0)),
               "available_bags": float(v.get("available_bags", 0))}
              for p, v in fg.items()]
    return ok(rows)

@app.route("/api/inventory/finished-goods", methods=["POST"])
@require_perm("inventory", "admin")
def update_fg():
    body    = request.get_json() or {}
    product = body.get("product", "").strip()
    if not product:
        return err("Product required")
    db.update_finished_goods(
        product,
        float(body.get("available_kg", 0)),
        int(body.get("available_bags", 0)),
    )
    return ok({"product": product})

@app.route("/api/inventory/health", methods=["GET"])
@login_required
def inventory_health():
    return ok(df_to_list(_engine().inventory_health()))


# ════════════════════════════════════════════════════════════════════════════ #
#  FEASIBILITY                                                                 #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/feasibility", methods=["POST"])
@login_required
def check_feasibility():
    body = request.get_json() or {}
    try:
        orders = db.get_orders()
        summary, detail = _engine().feasibility_single_order(body, orders)
        return ok({"summary": summary, "material_detail": df_to_list(detail)})
    except MRPValidationError as e:
        return err(str(e))


# ════════════════════════════════════════════════════════════════════════════ #
#  ORDERS                                                                      #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/orders", methods=["GET"])
@login_required
def get_orders():
    status  = request.args.get("status")
    product = request.args.get("product")
    orders  = db.get_orders(status_filter=status)
    if product:
        orders = [o for o in orders if o.get("product") == product]
    return ok(orders)

@app.route("/api/orders", methods=["POST"])
@require_perm("orders", "admin")
def create_order():
    body     = request.get_json() or {}
    existing = db.get_orders()
    order_no = body.get("order_no", f"SO-{len(existing)+1:04d}").strip()
    if any(o.get("order_no") == order_no for o in existing):
        return err(f"Order number '{order_no}' already exists")
    qty = float(body.get("quantity_kg", body.get("quantity", 0)))
    if qty <= 0:
        return err("Quantity must be positive")
    order = {
        "order_no":      order_no,
        "customer":      body.get("customer", ""),
        "product":       body.get("product", ""),
        "quantity_kg":   qty,
        "bag_size_kg":   float(body.get("bag_size_kg", 50)),
        "bags":          int(body.get("bags", 0)),
        "delivery_date": body.get("delivery_date", str(date.today())),
        "status":        body.get("status", "Pending"),
        "notes":         body.get("notes", ""),
        "created_by":    session["user"].get("username", ""),
    }
    db.create_order(order)
    return ok(order)

@app.route("/api/orders/<order_no>", methods=["PATCH"])
@require_perm("orders", "admin")
def update_order(order_no):
    body = request.get_json() or {}
    db.update_order(order_no, body)
    orders = db.get_orders()
    found  = next((o for o in orders if o.get("order_no") == order_no), None)
    if not found:
        return err("Order not found", 404)
    return ok(found)

@app.route("/api/orders/<order_no>", methods=["DELETE"])
@require_perm("orders", "admin")
def delete_order(order_no):
    db.delete_order(order_no)
    return ok({"deleted": order_no})


# ════════════════════════════════════════════════════════════════════════════ #
#  MRP                                                                         #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/mrp/run", methods=["POST"])
@require_perm("write", "admin")
def run_mrp():
    orders = db.get_orders()
    try:
        reports = _engine().run_fulfillment_mrp(orders)
        return ok({
            "order_feasibility":                 df_to_list(reports["order_feasibility"]),
            "order_material_detail":             df_to_list(reports["order_material_detail"]),
            "raw_material_requirements_summary": df_to_list(reports["raw_material_requirements_summary"]),
            "fg_reservations":                   df_to_list(reports["fg_reservations"]),
            "reorder_alerts":                    df_to_list(reports["reorder_alerts"]),
        })
    except MRPValidationError as e:
        return err(str(e))

@app.route("/api/mrp/export", methods=["POST"])
@require_perm("write", "admin")
def export_mrp():
    orders = db.get_orders()
    try:
        reports = _engine().run_fulfillment_mrp(orders)
        out     = REPORTS / f"mrp_report_{int(time.time())}.xlsx"
        _engine().export_excel(reports, out)
        return send_file(str(out), as_attachment=True, download_name="jdk_mrp_report.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except MRPValidationError as e:
        return err(str(e))


# ════════════════════════════════════════════════════════════════════════════ #
#  BACKUP / RESTORE                                                            #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/backup/master", methods=["GET"])
@require_perm("admin")
def backup_master():
    data = db.build_master()
    tmp  = REPORTS / "master_data_backup.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return send_file(str(tmp), as_attachment=True, download_name="master_data_backup.json",
                     mimetype="application/json")

@app.route("/api/backup/orders", methods=["GET"])
@require_perm("admin")
def backup_orders():
    data = db.get_orders()
    tmp  = REPORTS / "customer_orders_backup.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return send_file(str(tmp), as_attachment=True, download_name="customer_orders_backup.json",
                     mimetype="application/json")

@app.route("/api/backup/customers", methods=["GET"])
@require_perm("admin")
def backup_customers():
    data = db.get_customers()
    tmp  = REPORTS / "customers_backup.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return send_file(str(tmp), as_attachment=True, download_name="customers_backup.json",
                     mimetype="application/json")

@app.route("/api/restore/master", methods=["POST"])
@require_perm("admin")
def restore_master():
    if "file" not in request.files:
        return err("No file provided")
    try:
        data = json.loads(request.files["file"].read().decode("utf-8"))
    except json.JSONDecodeError as e:
        return err(f"Invalid JSON: {e}")
    required = {"products", "raw_materials", "inventory"}
    missing  = required - set(data.keys())
    if missing:
        return err(f"File missing required keys: {missing}")
    db.migrate_from_json(data, [], [])
    return ok({"message": "Master data restored into MySQL"})


# ════════════════════════════════════════════════════════════════════════════ #
#  PRODUCTION SCHEDULES                                                        #
# ════════════════════════════════════════════════════════════════════════════ #

def _schedule_alerts(schedule: dict, all_schedules: list) -> list:
    alerts  = []
    master  = db.build_master()
    engine  = MRPEngine(master)
    config  = engine.config
    product = schedule.get("product", "")
    qty_kg  = float(schedule.get("planned_qty_kg", 0))
    manpower     = float(schedule.get("manpower_available", 0))
    manpower_req = float(schedule.get("manpower_required", 0))

    try:
        start_dt = datetime.strptime(schedule.get("start_date", ""), "%Y-%m-%d").date()
        end_dt   = datetime.strptime(schedule.get("end_date",   ""), "%Y-%m-%d").date()
        work_days = max((end_dt - start_dt).days, 1)
    except ValueError:
        work_days = 1
        start_dt  = date.today()
        end_dt    = start_dt

    daily_cap       = config.daily_production_capacity_kg
    capacity_window = work_days * daily_cap
    if qty_kg > capacity_window:
        alerts.append({"type": "TIME_SHORTAGE", "severity": "CRITICAL",
                        "message": f"Planned {qty_kg:,.0f} kg exceeds {work_days}-day capacity "
                                   f"({capacity_window:,.0f} kg at {daily_cap:,.0f} kg/day)."})

    if manpower_req > 0 and manpower < manpower_req:
        alerts.append({"type": "MANPOWER_SHORTAGE", "severity": "CRITICAL",
                        "message": f"Manpower deficit: {manpower:.0f} available vs {manpower_req:.0f} required."})

    if product and qty_kg > 0 and product in engine.products:
        formula = engine.products[product].get("formula", {})
        if formula:
            try:
                for mat, ratio in engine._ratios(formula).items():
                    required = qty_kg * ratio
                    stock    = float(engine.inventory.get(mat, {}).get("current_stock", 0))
                    if required > stock:
                        alerts.append({"type": "MATERIAL_SHORTAGE", "severity": "CRITICAL",
                                        "material": mat,
                                        "message": f"{mat}: needs {required:,.1f} kg, "
                                                   f"only {stock:,.1f} kg in stock (short {required-stock:,.1f} kg)."})
            except Exception:
                pass

    sid = schedule.get("schedule_id")
    for other in all_schedules:
        if other.get("schedule_id") == sid:
            continue
        try:
            os_start = datetime.strptime(other.get("start_date", ""), "%Y-%m-%d").date()
            os_end   = datetime.strptime(other.get("end_date",   ""), "%Y-%m-%d").date()
            if start_dt <= os_end and end_dt >= os_start:
                combined = qty_kg + float(other.get("planned_qty_kg", 0))
                window   = max((max(end_dt, os_end) - min(start_dt, os_start)).days, 1) * daily_cap
                if combined > window:
                    alerts.append({"type": "CAPACITY_OVERLAP", "severity": "WARNING",
                                    "message": f"Overlaps with {other.get('schedule_id')} — "
                                               f"combined {combined:,.0f} kg > window {window:,.0f} kg."})
        except ValueError:
            pass
    return alerts


def _enrich(schedule: dict, all_schedules: list) -> dict:
    schedule["alerts"]       = _schedule_alerts(schedule, all_schedules)
    schedule["alert_count"]  = len(schedule["alerts"])
    schedule["has_shortage"] = any(a["severity"] == "CRITICAL" for a in schedule["alerts"])
    return schedule


@app.route("/api/production-schedule", methods=["GET"])
@login_required
def get_schedules():
    status    = request.args.get("status")
    schedules = db.get_schedules(status_filter=status)
    all_sched = db.get_schedules()
    return ok([_enrich(s, all_sched) for s in schedules])

@app.route("/api/production-schedule", methods=["POST"])
@require_perm("write", "admin")
def create_schedule():
    body      = request.get_json() or {}
    existing  = db.get_schedules()
    sched_id  = body.get("schedule_id", f"PS-{len(existing)+1:04d}").strip()
    if any(s.get("schedule_id") == sched_id for s in existing):
        return err(f"Schedule ID '{sched_id}' already exists")
    if float(body.get("planned_qty_kg", 0)) <= 0:
        return err("Planned quantity must be positive")
    schedule = {
        "schedule_id":        sched_id,
        "product":            body.get("product", ""),
        "planned_qty_kg":     float(body.get("planned_qty_kg", 0)),
        "start_date":         body.get("start_date", str(date.today())),
        "end_date":           body.get("end_date", str(date.today())),
        "shift":              body.get("shift", "Day"),
        "manpower_available": int(body.get("manpower_available", 0)),
        "manpower_required":  int(body.get("manpower_required", 0)),
        "status":             body.get("status", "Planned"),
        "linked_order_no":    body.get("linked_order_no", ""),
        "notes":              body.get("notes", ""),
        "created_by":         session["user"].get("username", ""),
    }
    db.create_schedule(schedule)
    all_sched = db.get_schedules()
    return ok(_enrich(schedule, all_sched))

@app.route("/api/production-schedule/<schedule_id>", methods=["PATCH"])
@require_perm("write", "admin")
def update_schedule(schedule_id):
    body = request.get_json() or {}
    db.update_schedule(schedule_id, body)
    all_sched = db.get_schedules()
    found = next((s for s in all_sched if s.get("schedule_id") == schedule_id), None)
    if not found:
        return err("Schedule not found", 404)
    return ok(_enrich(found, all_sched))

@app.route("/api/production-schedule/<schedule_id>", methods=["DELETE"])
@require_perm("write", "admin")
def delete_schedule(schedule_id):
    db.delete_schedule(schedule_id)
    return ok({"deleted": schedule_id})

@app.route("/api/production-schedule/alerts", methods=["GET"])
@login_required
def schedule_alerts_summary():
    schedules = db.get_schedules()
    result = []
    for s in schedules:
        if s.get("status") in ("Completed", "Cancelled"):
            continue
        alerts = _schedule_alerts(s, schedules)
        if alerts:
            result.append({
                "schedule_id": s.get("schedule_id"),
                "product":     s.get("product"),
                "start_date":  s.get("start_date"),
                "end_date":    s.get("end_date"),
                "alerts":      alerts,
                "critical":    sum(1 for a in alerts if a["severity"] == "CRITICAL"),
                "warnings":    sum(1 for a in alerts if a["severity"] == "WARNING"),
            })
    return ok(result)


# ════════════════════════════════════════════════════════════════════════════ #
#  HEALTH CHECK + DB MIGRATION                                                 #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/health", methods=["GET"])
def health():
    return ok({"status": "ok", "db": "mysql" if db.is_available() else "unavailable",
                "timestamp": datetime.utcnow().isoformat()})

@app.route("/api/migrate-json", methods=["POST"])
@require_perm("admin")
def migrate_json():
    """
    One-time migration: upload existing JSON files as a multipart form.
    Fields: master (JSON), orders (JSON), customers (JSON).
    Or POST without body to migrate from disk if data/ files still exist.
    """
    import json as _json
    DATA = BASE / "data"
    AUTH_FILE = CONFIG / "auth.json"

    def _read_file(field, fallback_path):
        if field in request.files:
            return _json.loads(request.files[field].read().decode())
        p = Path(fallback_path)
        return _json.loads(p.read_text()) if p.exists() else None

    master    = _read_file("master",    DATA / "master_data.json")    or {}
    orders    = _read_file("orders",    DATA / "customer_orders.json") or []
    customers = _read_file("customers", DATA / "customers.json")       or []
    users_raw = _json.loads(AUTH_FILE.read_text()) if AUTH_FILE.exists() else None

    db.migrate_from_json(master, orders, customers, users_raw)
    return ok({"message": "Migration complete. All JSON data imported into MySQL."})


# ════════════════════════════════════════════════════════════════════════════ #
#  BOOTSTRAP & STARTUP                                                         #
# ════════════════════════════════════════════════════════════════════════════ #

def _bootstrap():
    """Verify DB connection and create default admin if users table is empty."""
    if not db.is_available():
        print("⚠  MySQL not reachable — check .env DB_* settings and that XAMPP is running.")
        return
    users = db.get_all_users()
    if not users:
        default_password = os.environ.get("DEFAULT_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        db.create_user("admin", default_password, role="admin")
        if os.environ.get("DEFAULT_ADMIN_PASSWORD"):
            print("✔  Default admin user 'admin' created using DEFAULT_ADMIN_PASSWORD from .env")
        else:
            print("✔  Default admin user 'admin' created with a generated password.")
            print("   Set DEFAULT_ADMIN_PASSWORD in .env before first run to choose it yourself,")
            print("   or use the 'Forgot password' flow to set a new one now.")
    print(f"✔  MySQL connected — {len(users) or 1} user(s)")

_bootstrap()

if __name__ == "__main__":
    print("=" * 60)
    print("  JDK Smart Factory Platform v3.0 — MySQL Edition")
    print("  Open: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0", use_reloader=False, threaded=True)
