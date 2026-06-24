"""
JDK Smart Factory Platform — Flask REST API Backend
Re-architected: every module exposed as API endpoint, DeepSeek AI chat integration.
"""

import hashlib
import json
import os
import secrets
import time
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_file, session
from flask_cors import CORS

from mrp_engine import MRPEngine, MRPValidationError

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.parent
DATA     = BASE / "data"
CONFIG   = BASE / "config"
REPORTS  = BASE / "reports"
MASTER   = DATA / "master_data.json"
ORDERS   = DATA / "customer_orders.json"
CUSTOMERS= DATA / "customers.json"
AUTH     = CONFIG / "auth.json"
SETTINGS = CONFIG / "settings.json"
for p in (DATA, CONFIG, REPORTS):
    p.mkdir(parents=True, exist_ok=True)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

# Secret key must be STABLE across restarts — a new random key every start
# invalidates all sessions and causes infinite reload loops in the browser.
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
    SESSION_COOKIE_SECURE=False,   # allow HTTP on localhost/dev
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
CORS(app, supports_credentials=True, origins=["*"])

ORDER_STATUSES = ["Open", "Approved", "Production Planned", "In Production",
                  "Ready For Shipment", "Shipped", "Closed", "Cancelled"]
STATUS_TERMINAL = frozenset({"Shipped", "Closed", "Cancelled"})
ROLE_PERMS = {
    "Super Admin":        {"read", "write", "admin", "orders", "inventory"},
    "Production Planner": {"read", "write", "orders"},
    "Warehouse User":     {"read", "inventory"},
    "Purchasing User":    {"read", "write"},
    "Management Viewer":  {"read"},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _load_json(p: Path):
    if not p.exists():
        return [] if p in (ORDERS, CUSTOMERS) else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [] if p in (ORDERS, CUSTOMERS) else {}

def _save_json(p: Path, data) -> bool:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False

def _load_master():
    return _load_json(MASTER)

def _engine(master=None):
    return MRPEngine(master or _load_master())

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
#  AUTH ROUTES                                                                 #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return err("Username and password required")
    if not AUTH.exists():
        return err("Auth config missing — run setup first", 500)
    data = _load_json(AUTH)
    users = data.get("users", []) if isinstance(data, dict) else []
    pw_hash = _sha256(password)
    for u in users:
        if u.get("username", "").lower() == username.lower():
            if u.get("password_hash") == pw_hash:
                session.permanent = True
                session["user"] = {k: v for k, v in u.items() if k != "password_hash"}
                return ok({"username": u["username"], "role": u["role"],
                           "display_name": u.get("display_name", u["username"])})
    return err("Invalid username or password", 401)


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    display  = body.get("display_name", username).strip()
    email    = body.get("email", "").strip()
    if not username or not password:
        return err("Username and password required")
    if len(password) < 6:
        return err("Password must be at least 6 characters")
    data = _load_json(AUTH) if AUTH.exists() else {"users": []}
    if not isinstance(data, dict):
        data = {"users": []}
    users = data.get("users", [])
    if any(u.get("username", "").lower() == username.lower() for u in users):
        return err("Username already taken")
    users.append({
        "username": username,
        "password_hash": _sha256(password),
        "display_name": display,
        "email": email,
        "role": "Management Viewer",  # default role for self-signup
        "created_at": datetime.utcnow().isoformat(),
    })
    data["users"] = users
    _save_json(AUTH, data)
    return ok({"message": "Account created. Please log in."})


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    email    = body.get("email", "").strip()
    if not AUTH.exists():
        return err("Auth config missing", 500)
    data = _load_json(AUTH)
    users = data.get("users", []) if isinstance(data, dict) else []
    for u in users:
        match = (u.get("username", "").lower() == username.lower() if username
                 else u.get("email", "").lower() == email.lower())
        if match:
            # In production send email; here we return a reset token
            token = secrets.token_urlsafe(32)
            u["reset_token"] = token
            u["reset_expires"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            _save_json(AUTH, data)
            # Dev mode: return token directly. Prod: send email.
            return ok({"message": "Reset token issued (dev mode — check response).",
                       "reset_token": token})
    return err("No account found for that username/email")


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    body = request.get_json() or {}
    token    = body.get("token", "")
    password = body.get("password", "")
    if not token or not password:
        return err("Token and new password required")
    if len(password) < 6:
        return err("Password must be at least 6 characters")
    if not AUTH.exists():
        return err("Auth config missing", 500)
    data = _load_json(AUTH)
    users = data.get("users", []) if isinstance(data, dict) else []
    for u in users:
        if u.get("reset_token") == token:
            expires = u.get("reset_expires", "")
            if expires and datetime.utcnow() > datetime.fromisoformat(expires):
                return err("Reset token expired")
            u["password_hash"] = _sha256(password)
            u.pop("reset_token", None)
            u.pop("reset_expires", None)
            _save_json(AUTH, data)
            return ok({"message": "Password updated. Please log in."})
    return err("Invalid or expired reset token")


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
    s = _load_json(SETTINGS) if SETTINGS.exists() else {}
    # Never expose actual API key value — just whether it's set
    safe = dict(s)
    if safe.get("deepseek_api_key"):
        safe["deepseek_api_key"] = "••••••••" + safe["deepseek_api_key"][-4:]
    return ok(safe)


@app.route("/api/settings", methods=["POST"])
@require_perm("admin")
def save_settings():
    body = request.get_json() or {}
    s = _load_json(SETTINGS) if SETTINGS.exists() else {}
    if "deepseek_api_key" in body and body["deepseek_api_key"] and not body["deepseek_api_key"].startswith("••"):
        s["deepseek_api_key"] = body["deepseek_api_key"]
    for field in ("deepseek_model", "deepseek_base_url", "app_name", "daily_capacity_kg",
                  "batch_size_kg", "planning_horizon_days"):
        if field in body:
            s[field] = body[field]
    _save_json(SETTINGS, s)
    return ok({"message": "Settings saved"})


# ════════════════════════════════════════════════════════════════════════════ #
#  AI CHAT                                                                     #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/chat", methods=["POST"])
@login_required
def ai_chat():
    """DeepSeek-powered natural language interface that maps queries to API actions."""
    import urllib.request as _req
    body    = request.get_json() or {}
    message = body.get("message", "").strip()
    history = body.get("history", [])
    if not message:
        return err("Message required")
    settings = _load_json(SETTINGS) if SETTINGS.exists() else {}
    api_key  = settings.get("deepseek_api_key", "")
    if not api_key:
        return ok({"reply": "⚙️ No DeepSeek API key configured. Please go to **Settings** and add your key.", "action": None})

    master    = _load_master()
    products  = list(master.get("products", {}).keys())
    materials = list(master.get("raw_materials", {}).keys())
    orders    = _load_json(ORDERS)
    open_ord  = [o for o in orders if o.get("status") not in STATUS_TERMINAL]
    customers = _load_json(CUSTOMERS)

    system_prompt = f"""You are the JDK Smart Factory AI assistant. You help users query and control a manufacturing ERP platform.

Current factory state:
- Products: {', '.join(products) or 'none'}
- Raw materials: {', '.join(materials) or 'none'}
- Open orders: {len(open_ord)}
- Customers: {len(customers)}
- User role: {session['user'].get('role', 'Unknown')}

You can:
1. Answer questions about inventory, orders, products using the data above
2. Suggest what actions to take (add material, create order, run MRP, etc.)
3. Explain factory metrics and concepts

Respond conversationally in 1-3 short paragraphs. Be direct and actionable. 
If the user asks to DO something (create order, update stock, run MRP), reply with a JSON action block like:
{{"action": "navigate", "page": "orders"}} or {{"action": "run_mrp"}} or {{"action": "check_inventory", "material": "X"}}

Always end your response with the JSON action on its own line if applicable, otherwise omit it.
Format: plain text response first, then optionally: ACTION: {{...}}"""

    messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
                for m in history[-10:]]
    messages.append({"role": "user", "content": message})

    payload = json.dumps({
        "model": settings.get("deepseek_model", "deepseek-chat"),
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()

    base_url = settings.get("deepseek_base_url", "https://api.deepseek.com")
    req = _req.Request(
        f"{base_url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with _req.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        raw = result["choices"][0]["message"]["content"]
        # Parse action if present
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
    master    = _load_master()
    orders    = _load_json(ORDERS)
    customers = _load_json(CUSTOMERS)
    engine    = _engine(master)
    open_ord  = [o for o in orders if o.get("status", "Open") not in STATUS_TERMINAL]
    critical  = [o for o in open_ord if o.get("priority") == "Critical"]
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
            "active_products": len([p for p, d in prods.items() if d.get("status") == "Active"]),
            "customers": len(customers),
            "open_orders": len(open_ord),
            "critical_orders": len(critical),
            "suppliers": sum(len(v) for v in master.get("suppliers", {}).values()),
            "stock_alerts": len(crit_mats) + len(low_mats),
            "critical_stock": len(crit_mats),
        },
        "finished_goods": fg_rows,
        "inventory_health": df_to_list(inv_health),
        "open_orders": open_ord[:20],
        "alerts": {
            "critical_materials": [m["material"] for m in crit_mats],
            "low_materials":      [m["material"] for m in low_mats],
            "critical_orders":    len(critical),
        },
    })


# ════════════════════════════════════════════════════════════════════════════ #
#  CUSTOMERS                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/customers", methods=["GET"])
@login_required
def get_customers():
    return ok(_load_json(CUSTOMERS))

@app.route("/api/customers", methods=["POST"])
@require_perm("admin")
def add_customer():
    body = request.get_json() or {}
    name = body.get("customer", "").strip()
    if not name:
        return err("Customer name required")
    customers = _load_json(CUSTOMERS)
    if any(c.get("customer", "").lower() == name.lower() for c in customers):
        return err(f"Customer '{name}' already exists")
    customers.append({"customer": name, "customer_type": body.get("customer_type", "Other"),
                      "delivery_location": body.get("delivery_location", ""),
                      "terms": body.get("terms", "")})
    _save_json(CUSTOMERS, customers)
    return ok(customers)

@app.route("/api/customers/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_customer(name):
    customers = [c for c in _load_json(CUSTOMERS) if c.get("customer") != name]
    _save_json(CUSTOMERS, customers)
    return ok(customers)


# ════════════════════════════════════════════════════════════════════════════ #
#  PRODUCTS                                                                    #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    master = _load_master()
    rows = [{"name": p, **d} for p, d in master.get("products", {}).items()]
    return ok(rows)

@app.route("/api/products", methods=["POST"])
@require_perm("admin")
def upsert_product():
    body = request.get_json() or {}
    name = body.get("name", "").strip()
    if not name:
        return err("Product name required")
    master = _load_master()
    old    = body.get("old_name", name)
    if old in master.get("products", {}) and old != name:
        master["products"][name] = master["products"].pop(old)
    master.setdefault("products", {}).setdefault(name, {"formula": {}})
    master["products"][name].update({
        "category": body.get("category", ""),
        "default_bag_size_kg": float(body.get("default_bag_size_kg", 25)),
        "status": body.get("status", "Active"),
    })
    _save_json(MASTER, master)
    return ok({"name": name, **master["products"][name]})

@app.route("/api/products/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_product(name):
    master = _load_master()
    master.get("products", {}).pop(name, None)
    _save_json(MASTER, master)
    return ok({"deleted": name})


# ════════════════════════════════════════════════════════════════════════════ #
#  FORMULAS                                                                    #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/formulas/<product>", methods=["GET"])
@login_required
def get_formula(product):
    master  = _load_master()
    formula = master.get("products", {}).get(product, {}).get("formula", {})
    total   = _engine(master).formula_total(product)
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
    master = _load_master()
    master.setdefault("products", {}).setdefault(product, {"formula": {}})
    master["products"][product].setdefault("formula", {})[mat] = pct
    _save_json(MASTER, master)
    return ok({"material": mat, "percentage": pct})

@app.route("/api/formulas/<product>/<material>", methods=["DELETE"])
@require_perm("admin")
def delete_formula_line(product, material):
    master = _load_master()
    master.get("products", {}).get(product, {}).get("formula", {}).pop(material, None)
    _save_json(MASTER, master)
    return ok({"deleted": material})


# ════════════════════════════════════════════════════════════════════════════ #
#  RAW MATERIALS                                                               #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/raw-materials", methods=["GET"])
@login_required
def get_raw_materials():
    master = _load_master()
    health = _engine(master).inventory_health()
    return ok(df_to_list(health))

@app.route("/api/raw-materials", methods=["POST"])
@require_perm("admin")
def upsert_raw_material():
    body = request.get_json() or {}
    name = body.get("name", "").strip()
    if not name:
        return err("Material name required")
    master = _load_master()
    master.setdefault("raw_materials", {})[name] = {"unit": body.get("unit", "kg")}
    master.setdefault("inventory", {})[name] = {
        "current_stock":  float(body.get("current_stock", 0)),
        "minimum_stock":  float(body.get("minimum_stock", 0)),
        "reorder_point":  float(body.get("reorder_point", 0)),
        "lead_time_days": float(body.get("lead_time_days", 0)),
    }
    _save_json(MASTER, master)
    return ok({"name": name})

@app.route("/api/raw-materials/<name>", methods=["DELETE"])
@require_perm("admin")
def delete_raw_material(name):
    master = _load_master()
    master.get("raw_materials", {}).pop(name, None)
    master.get("inventory", {}).pop(name, None)
    _save_json(MASTER, master)
    return ok({"deleted": name})


# ════════════════════════════════════════════════════════════════════════════ #
#  SUPPLIERS                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    master = _load_master()
    rows = []
    for mat, sups in master.get("suppliers", {}).items():
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
    master = _load_master()
    master.setdefault("suppliers", {}).setdefault(mat, []).append({
        "supplier_name": name,
        "price": float(body.get("price", 0)),
        "lead_time_days": float(body.get("lead_time_days", 0)),
        "minimum_order_qty": float(body.get("minimum_order_qty", 0)),
        "payment_terms": body.get("payment_terms", ""),
        "delivery_cost": float(body.get("delivery_cost", 0)),
    })
    _save_json(MASTER, master)
    return ok({"message": f"Supplier '{name}' added for {mat}"})

@app.route("/api/suppliers/<material>/<supplier_name>", methods=["DELETE"])
@require_perm("admin")
def delete_supplier(material, supplier_name):
    master = _load_master()
    sups   = master.get("suppliers", {}).get(material, [])
    master["suppliers"][material] = [s for s in sups if s.get("supplier_name") != supplier_name]
    _save_json(MASTER, master)
    return ok({"deleted": supplier_name})


# ════════════════════════════════════════════════════════════════════════════ #
#  INVENTORY                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/inventory/finished-goods", methods=["GET"])
@login_required
def get_fg():
    master = _load_master()
    fg     = master.get("finished_goods", {})
    prods  = master.get("products", {})
    rows   = [{"product": p, "category": prods.get(p, {}).get("category", "—"),
               "available_kg": float(v.get("available_kg", 0)),
               "available_bags": float(v.get("available_bags", 0))} for p, v in fg.items()]
    return ok(rows)

@app.route("/api/inventory/finished-goods", methods=["POST"])
@require_perm("inventory", "admin")
def update_fg():
    body    = request.get_json() or {}
    product = body.get("product", "").strip()
    if not product:
        return err("Product required")
    master = _load_master()
    master.setdefault("finished_goods", {})[product] = {
        "available_kg":   float(body.get("available_kg", 0)),
        "available_bags": float(body.get("available_bags", 0)),
    }
    _save_json(MASTER, master)
    return ok(master["finished_goods"][product])

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
        orders  = _load_json(ORDERS)
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
    orders = _load_json(ORDERS)
    status   = request.args.get("status")
    priority = request.args.get("priority")
    product  = request.args.get("product")
    if status:    orders = [o for o in orders if o.get("status") == status]
    if priority:  orders = [o for o in orders if o.get("priority") == priority]
    if product:   orders = [o for o in orders if o.get("product") == product]
    return ok(orders)

@app.route("/api/orders", methods=["POST"])
@require_perm("orders", "admin")
def create_order():
    body    = request.get_json() or {}
    orders  = _load_json(ORDERS)
    order_no = body.get("order_no", f"SO-{len(orders)+1:04d}").strip()
    if any(o.get("order_no") == order_no for o in orders):
        return err(f"Order number '{order_no}' already exists")
    if float(body.get("quantity", 0)) <= 0:
        return err("Quantity must be positive")
    order = {
        "order_no":     order_no,
        "customer":     body.get("customer", ""),
        "product":      body.get("product", ""),
        "quantity":     float(body.get("quantity", 0)),
        "unit":         body.get("unit", "kg"),
        "bag_size_kg":  float(body.get("bag_size_kg", 25)),
        "priority":     body.get("priority", "Normal"),
        "status":       body.get("status", "Open"),
        "delivery_date":body.get("delivery_date", str(date.today())),
        "reserved_fg_kg": 0,
        "created_at":   datetime.utcnow().isoformat(),
        "created_by":   session["user"].get("username", ""),
    }
    orders.append(order)
    _save_json(ORDERS, orders)
    return ok(order)

@app.route("/api/orders/<order_no>", methods=["PATCH"])
@require_perm("orders", "admin")
def update_order(order_no):
    body   = request.get_json() or {}
    orders = _load_json(ORDERS)
    for o in orders:
        if o.get("order_no") == order_no:
            allowed = {"status", "priority", "delivery_date", "quantity", "unit", "bag_size_kg"}
            for k in allowed:
                if k in body:
                    o[k] = body[k]
            _save_json(ORDERS, orders)
            return ok(o)
    return err("Order not found", 404)

@app.route("/api/orders/<order_no>", methods=["DELETE"])
@require_perm("orders", "admin")
def delete_order(order_no):
    orders = [o for o in _load_json(ORDERS) if o.get("order_no") != order_no]
    _save_json(ORDERS, orders)
    return ok({"deleted": order_no})


# ════════════════════════════════════════════════════════════════════════════ #
#  MRP RUN                                                                     #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/mrp/run", methods=["POST"])
@require_perm("write", "admin")
def run_mrp():
    orders = _load_json(ORDERS)
    try:
        reports = _engine().run_fulfillment_mrp(orders)
        return ok({
            "order_feasibility":              df_to_list(reports["order_feasibility"]),
            "order_material_detail":          df_to_list(reports["order_material_detail"]),
            "raw_material_requirements_summary": df_to_list(reports["raw_material_requirements_summary"]),
            "fg_reservations":                df_to_list(reports["fg_reservations"]),
            "reorder_alerts":                 df_to_list(reports["reorder_alerts"]),
        })
    except MRPValidationError as e:
        return err(str(e))

@app.route("/api/mrp/export", methods=["POST"])
@require_perm("write", "admin")
def export_mrp():
    orders = _load_json(ORDERS)
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
    return send_file(str(MASTER), as_attachment=True, download_name="master_data_backup.json",
                     mimetype="application/json")

@app.route("/api/backup/orders", methods=["GET"])
@require_perm("admin")
def backup_orders():
    return send_file(str(ORDERS), as_attachment=True, download_name="customer_orders_backup.json",
                     mimetype="application/json")

@app.route("/api/backup/customers", methods=["GET"])
@require_perm("admin")
def backup_customers():
    return send_file(str(CUSTOMERS), as_attachment=True, download_name="customers_backup.json",
                     mimetype="application/json")

@app.route("/api/restore/master", methods=["POST"])
@require_perm("admin")
def restore_master():
    if "file" not in request.files:
        return err("No file provided")
    f = request.files["file"]
    try:
        data = json.loads(f.read().decode("utf-8"))
    except json.JSONDecodeError as e:
        return err(f"Invalid JSON: {e}")
    required = {"products", "raw_materials", "inventory"}
    missing  = required - set(data.keys())
    if missing:
        return err(f"File missing required keys: {missing}")
    _save_json(MASTER, data)
    return ok({"message": "Master data restored"})


# ════════════════════════════════════════════════════════════════════════════ #
#  HEALTH CHECK                                                                #
# ════════════════════════════════════════════════════════════════════════════ #

@app.route("/api/health", methods=["GET"])
def health():
    return ok({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


def _bootstrap():
    """Run once at startup — creates default auth.json if missing."""
    if not AUTH.exists():
        default_users = {"users": [
            {"username": "admin",     "password_hash": _sha256("admin123"),     "display_name": "Administrator",      "role": "Super Admin",        "email": ""},
            {"username": "planner",   "password_hash": _sha256("planner123"),   "display_name": "Production Planner", "role": "Production Planner", "email": ""},
            {"username": "warehouse", "password_hash": _sha256("warehouse123"), "display_name": "Warehouse User",     "role": "Warehouse User",     "email": ""},
            {"username": "purchase",  "password_hash": _sha256("purchase123"),  "display_name": "Purchasing User",    "role": "Purchasing User",    "email": ""},
            {"username": "viewer",    "password_hash": _sha256("view123"),      "display_name": "Management Viewer",  "role": "Management Viewer",  "email": ""},
        ]}
        AUTH.parent.mkdir(parents=True, exist_ok=True)
        AUTH.write_text(json.dumps(default_users, indent=2))
        print("✓ Default auth.json created (admin/admin123)")

# Bootstrap runs whenever this module is imported (by serve.py or directly)
_bootstrap()


if __name__ == "__main__":
    print("=" * 60)
    print("  JDK Smart Factory Platform v2.0")
    print("  Open: http://localhost:5000")
    print("  Default login: admin / admin123")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0", use_reloader=False, threaded=True)


# ════════════════════════════════════════════════════════════════════════════ #
#  PRODUCTION SCHEDULES                                                        #
# ════════════════════════════════════════════════════════════════════════════ #

SCHEDULES = DATA / "production_schedules.json"

def _load_schedules():
    return _load_json(SCHEDULES) if SCHEDULES.exists() else []

def _save_schedules(data):
    return _save_json(SCHEDULES, data)

def _schedule_alerts(schedule: dict, master: dict, all_schedules: list) -> list:
    """Return list of alert dicts for a single schedule entry."""
    alerts = []
    engine  = MRPEngine(master)
    config  = engine.config
    product = schedule.get("product", "")
    qty_kg  = float(schedule.get("planned_qty_kg", 0))
    manpower= float(schedule.get("manpower_available", 0))
    manpower_req = float(schedule.get("manpower_required", 0))
    start_str = schedule.get("start_date", "")
    end_str   = schedule.get("end_date", "")

    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_dt   = datetime.strptime(end_str,   "%Y-%m-%d").date()
        work_days = max((end_dt - start_dt).days, 1)
    except ValueError:
        work_days = 1
        start_dt = date.today()
        end_dt   = start_dt

    # ── Time / capacity check ────────────────────────────────────────────────
    daily_cap = config.daily_production_capacity_kg
    capacity_window = work_days * daily_cap
    if qty_kg > capacity_window:
        alerts.append({
            "type": "TIME_SHORTAGE",
            "severity": "CRITICAL",
            "message": (
                f"Planned {qty_kg:,.0f} kg exceeds {work_days}-day capacity "
                f"({capacity_window:,.0f} kg at {daily_cap:,.0f} kg/day). "
                f"Need {max(0, (qty_kg/daily_cap) - work_days):.1f} more days."
            ),
        })

    # ── Manpower check ───────────────────────────────────────────────────────
    if manpower_req > 0 and manpower < manpower_req:
        deficit = manpower_req - manpower
        alerts.append({
            "type": "MANPOWER_SHORTAGE",
            "severity": "CRITICAL",
            "message": f"Manpower deficit: {manpower:.0f} available vs {manpower_req:.0f} required ({deficit:.0f} short).",
        })

    # ── Material availability check ──────────────────────────────────────────
    if product and qty_kg > 0 and product in engine.products:
        formula = engine.products[product].get("formula", {})
        if formula:
            try:
                ratios = engine._ratios(formula)
                for mat, ratio in ratios.items():
                    required = qty_kg * ratio
                    stock    = float(engine.inventory.get(mat, {}).get("current_stock", 0))
                    shortage = max(required - stock, 0.0)
                    lead     = float(engine.inventory.get(mat, {}).get("lead_time_days", 0))
                    if shortage > 0:
                        alerts.append({
                            "type": "MATERIAL_SHORTAGE",
                            "severity": "CRITICAL",
                            "material": mat,
                            "message": (
                                f"Material shortage: {mat} needs {required:,.1f} kg, "
                                f"only {stock:,.1f} kg in stock (short {shortage:,.1f} kg). "
                                f"Lead time: {lead:.0f} days."
                            ),
                        })
            except Exception:
                pass
        else:
            alerts.append({
                "type": "NO_FORMULA",
                "severity": "WARNING",
                "message": f"Product '{product}' has no formula configured — cannot verify material requirements.",
            })
    elif product and product not in engine.products:
        alerts.append({
            "type": "UNKNOWN_PRODUCT",
            "severity": "WARNING",
            "message": f"Product '{product}' not found in master data.",
        })

    # ── Overlap / double-booking check ───────────────────────────────────────
    sid = schedule.get("schedule_id")
    for other in all_schedules:
        if other.get("schedule_id") == sid:
            continue
        try:
            os_start = datetime.strptime(other.get("start_date", ""), "%Y-%m-%d").date()
            os_end   = datetime.strptime(other.get("end_date",   ""), "%Y-%m-%d").date()
            if start_dt <= os_end and end_dt >= os_start:
                other_qty = float(other.get("planned_qty_kg", 0))
                combined  = qty_kg + other_qty
                window    = max((max(end_dt, os_end) - min(start_dt, os_start)).days, 1) * daily_cap
                if combined > window:
                    alerts.append({
                        "type": "CAPACITY_OVERLAP",
                        "severity": "WARNING",
                        "message": (
                            f"Schedule overlaps with {other.get('schedule_id')} ({other.get('product')}). "
                            f"Combined demand {combined:,.0f} kg exceeds window capacity {window:,.0f} kg."
                        ),
                    })
        except ValueError:
            pass

    return alerts


@app.route("/api/production-schedule", methods=["GET"])
@login_required
def get_schedules():
    schedules = _load_schedules()
    master    = _load_master()
    status_filter = request.args.get("status")
    if status_filter:
        schedules = [s for s in schedules if s.get("status") == status_filter]
    # Enrich with alerts
    all_sched = _load_schedules()
    for s in schedules:
        s["alerts"] = _schedule_alerts(s, master, all_sched)
        s["alert_count"]  = len(s["alerts"])
        s["has_shortage"]  = any(a["severity"] == "CRITICAL" for a in s["alerts"])
    return ok(schedules)


@app.route("/api/production-schedule", methods=["POST"])
@require_perm("write", "admin")
def create_schedule():
    body = request.get_json() or {}
    schedules = _load_schedules()
    sched_id = body.get("schedule_id", f"PS-{len(schedules)+1:04d}").strip()
    if any(s.get("schedule_id") == sched_id for s in schedules):
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
        "manpower_available": float(body.get("manpower_available", 0)),
        "manpower_required":  float(body.get("manpower_required", 0)),
        "notes":              body.get("notes", ""),
        "status":             body.get("status", "Planned"),
        "linked_order_no":    body.get("linked_order_no", ""),
        "created_at":         datetime.utcnow().isoformat(),
        "created_by":         session["user"].get("username", ""),
    }
    schedules.append(schedule)
    _save_schedules(schedules)
    # Compute alerts after save
    all_sched = _load_schedules()
    master    = _load_master()
    schedule["alerts"]      = _schedule_alerts(schedule, master, all_sched)
    schedule["alert_count"] = len(schedule["alerts"])
    schedule["has_shortage"] = any(a["severity"] == "CRITICAL" for a in schedule["alerts"])
    return ok(schedule)


@app.route("/api/production-schedule/<schedule_id>", methods=["PATCH"])
@require_perm("write", "admin")
def update_schedule(schedule_id):
    body      = request.get_json() or {}
    schedules = _load_schedules()
    for s in schedules:
        if s.get("schedule_id") == schedule_id:
            allowed = {
                "product", "planned_qty_kg", "start_date", "end_date",
                "shift", "manpower_available", "manpower_required",
                "notes", "status", "linked_order_no",
            }
            for k in allowed:
                if k in body:
                    s[k] = float(body[k]) if k in ("planned_qty_kg", "manpower_available", "manpower_required") else body[k]
            s["updated_at"] = datetime.utcnow().isoformat()
            _save_schedules(schedules)
            all_sched = _load_schedules()
            master    = _load_master()
            s["alerts"]       = _schedule_alerts(s, master, all_sched)
            s["alert_count"]  = len(s["alerts"])
            s["has_shortage"] = any(a["severity"] == "CRITICAL" for a in s["alerts"])
            return ok(s)
    return err("Schedule not found", 404)


@app.route("/api/production-schedule/<schedule_id>", methods=["DELETE"])
@require_perm("write", "admin")
def delete_schedule(schedule_id):
    schedules = [s for s in _load_schedules() if s.get("schedule_id") != schedule_id]
    _save_schedules(schedules)
    return ok({"deleted": schedule_id})


@app.route("/api/production-schedule/alerts", methods=["GET"])
@login_required
def schedule_alerts_summary():
    schedules = _load_schedules()
    master    = _load_master()
    result = []
    for s in schedules:
        if s.get("status") in ("Completed", "Cancelled"):
            continue
        alerts = _schedule_alerts(s, master, schedules)
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
