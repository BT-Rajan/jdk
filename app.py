"""
JDK Smart Factory Platform — Enterprise Edition
Auth: credentials loaded from config/auth.json (SHA-256 hashed passwords).
No plaintext secrets in source code.
"""

import hashlib
import json
from pathlib import Path
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from mrp_engine import MRPEngine, MRPValidationError

# ── Paths ─────────────────────────────────────────────────────────────────────
APP      = Path(__file__).parent
DATA     = APP / "data"
CONFIG   = APP / "config"
REPORTS  = APP / "reports"
MASTER   = DATA / "master_data.json"
ORDERS   = DATA / "customer_orders.json"
CUSTOMERS= DATA / "customers.json"
AUTH     = CONFIG / "auth.json"
REPORTS.mkdir(exist_ok=True)

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="JDK Smart Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens ─────────────────────────────────────────────────────────────
NAVY    = "#0f1f3d"
BLUE    = "#1a3a6b"
ACCENT  = "#2563eb"
LIGHT   = "#e8edf7"
SUCCESS = "#16a34a"
WARN_C  = "#d97706"
DANGER  = "#dc2626"
MUTED   = "#64748b"
SURFACE = "#f8fafc"
WHITE   = "#ffffff"

ROLE_COLORS = {
    "Super Admin":        "#7c3aed",
    "Production Planner": "#2563eb",
    "Warehouse User":     "#0891b2",
    "Purchasing User":    "#059669",
    "Management Viewer":  "#64748b",
}

ORDER_STATUSES = [
    "Open", "Approved", "Production Planned",
    "In Production", "Ready For Shipment",
    "Shipped", "Closed", "Cancelled",
]
STATUS_TERMINAL = frozenset({"Shipped", "Closed", "Cancelled"})

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Reset & base ──────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {{
    background: {SURFACE};
}}
[data-testid="stMain"] {{
    padding-top: 1.5rem;
}}

/* ── Sidebar ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {NAVY} !important;
    border-right: 1px solid {BLUE};
    min-width: 220px !important;
}}
[data-testid="stSidebar"] * {{
    color: #cbd5e1 !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: #f1f5f9 !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {BLUE} !important;
    margin: 0.75rem 0;
}}

/* ── Nav radio pills ───────────────────────────────────────────────── */
div[role="radiogroup"] > label {{
    background: rgba(255,255,255,0.04) !important;
    border-radius: 7px !important;
    padding: 0.45rem 0.8rem !important;
    margin-bottom: 3px !important;
    cursor: pointer;
    transition: background 0.15s ease;
    border: 1px solid transparent !important;
}}
div[role="radiogroup"] > label:hover {{
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.1) !important;
}}
div[role="radiogroup"] > label[data-checked="true"] {{
    background: {ACCENT} !important;
    border-color: transparent !important;
}}
div[role="radiogroup"] > label[data-checked="true"] p {{
    color: #fff !important;
    font-weight: 600 !important;
}}
div[role="radiogroup"] > label p {{
    font-size: 0.85rem !important;
    margin: 0 !important;
}}

/* ── Page header ───────────────────────────────────────────────────── */
.pg-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1.5rem;
    padding-bottom: 0.85rem;
    border-bottom: 2px solid {LIGHT};
}}
.pg-title {{
    font-size: 1.5rem;
    font-weight: 800;
    color: {NAVY};
    margin: 0;
    letter-spacing: -0.02em;
    line-height: 1.1;
}}
.pg-sub {{
    font-size: 0.82rem;
    color: {MUTED};
    margin-top: 2px;
}}

/* ── KPI cards ─────────────────────────────────────────────────────── */
.kpi {{
    background: {WHITE};
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.1rem 0.85rem;
    position: relative;
    overflow: hidden;
    height: 100%;
}}
.kpi-accent {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 10px 10px 0 0;
}}
.kpi-label {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: {MUTED};
    margin-bottom: 0.3rem;
}}
.kpi-value {{
    font-size: 1.9rem;
    font-weight: 800;
    color: {NAVY};
    line-height: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.kpi-sub {{
    font-size: 0.72rem;
    color: {MUTED};
    margin-top: 0.25rem;
}}

/* ── Alert banners ─────────────────────────────────────────────────── */
.jdk-alert {{
    padding: 0.7rem 1rem;
    border-radius: 8px;
    border-left: 4px solid;
    margin-bottom: 0.65rem;
    font-size: 0.875rem;
    line-height: 1.4;
}}
.jdk-alert.danger  {{ background:#fee2e2; border-color:{DANGER};  color:#7f1d1d; }}
.jdk-alert.warning {{ background:#fef9c3; border-color:{WARN_C};  color:#78350f; }}
.jdk-alert.success {{ background:#dcfce7; border-color:{SUCCESS}; color:#14532d; }}
.jdk-alert.info    {{ background:#dbeafe; border-color:{ACCENT};  color:#1e3a8a; }}

/* ── Section label ─────────────────────────────────────────────────── */
.sec-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {MUTED};
    padding-bottom: 0.45rem;
    border-bottom: 1px solid #f0f4f8;
    margin-bottom: 0.85rem;
    margin-top: 0.25rem;
}}

/* ── Status / priority badges ──────────────────────────────────────── */
.bdg {{
    display: inline-flex;
    align-items: center;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 20px;
    white-space: nowrap;
}}
.bdg-ok     {{ background:#dcfce7; color:#15803d; }}
.bdg-warn   {{ background:#fef9c3; color:#854d0e; }}
.bdg-danger {{ background:#fee2e2; color:#b91c1c; }}
.bdg-info   {{ background:#dbeafe; color:#1d4ed8; }}
.bdg-muted  {{ background:#f1f5f9; color:#475569; }}
.bdg-purple {{ background:#ede9fe; color:#6d28d9; }}

/* ── Role chip ─────────────────────────────────────────────────────── */
.role-chip {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: #fff;
    margin-top: 3px;
}}

/* ── Dataframe container ───────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}}

/* ── Form inputs ───────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    border-radius: 6px !important;
    border-color: #cbd5e1 !important;
    font-size: 0.875rem !important;
}}
.stSelectbox > div > div {{
    border-radius: 6px !important;
    border-color: #cbd5e1 !important;
}}
.stButton > button {{
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: opacity 0.15s;
}}
.stButton > button:hover {{ opacity: 0.88; }}
.stButton > button[kind="primary"] {{
    background: {ACCENT} !important;
    border: none !important;
    color: #fff !important;
}}

/* ── Tab strip ─────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 2px solid {LIGHT};
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 6px 6px 0 0 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.4rem 0.9rem !important;
}}

/* ── Login card ────────────────────────────────────────────────────── */
.login-card {{
    max-width: 400px;
    margin: 6vh auto 0;
    background: {WHITE};
    border-radius: 14px;
    padding: 2.5rem 2rem 2rem;
    box-shadow: 0 4px 28px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}}
.login-icon  {{ font-size: 2.8rem; text-align: center; margin-bottom: 0.5rem; }}
.login-title {{
    font-size: 1.35rem; font-weight: 800; color: {NAVY};
    text-align: center; letter-spacing: -0.02em; margin-bottom: 2px;
}}
.login-sub   {{ font-size: 0.78rem; color: {MUTED}; text-align: center; margin-bottom: 1.5rem; }}

/* ── Responsive: stack columns on narrow viewport ──────────────────── */
@media (max-width: 768px) {{
    .pg-title {{ font-size: 1.2rem !important; }}
    .kpi-value {{ font-size: 1.5rem !important; }}
    [data-testid="column"] {{ min-width: 100% !important; }}
}}

/* ── Misc ──────────────────────────────────────────────────────────── */
hr {{ border-color: #e2e8f0 !important; margin: 1rem 0; }}
.stCaption {{ color: {MUTED}; }}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════ #
#  AUTH                                                                        #
# ════════════════════════════════════════════════════════════════════════════ #

def _sha256(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def _load_auth() -> list:
    """Load users from config/auth.json. Raises RuntimeError on failure (no st calls)."""
    if not AUTH.exists():
        raise RuntimeError(
            "Auth config missing. Create `config/auth.json` with hashed user records. "
            "See README for the format."
        )
    try:
        data = json.loads(AUTH.read_text(encoding="utf-8"))
        return data.get("users", [])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"config/auth.json is malformed: {e}") from e


def _authenticate(username: str, password: str) -> Optional[dict]:
    """Return user dict if credentials match, else None."""
    users = _load_auth()
    pw_hash = _sha256(password)
    for u in users:
        if u.get("username", "").lower() == username.lower():
            if u.get("password_hash") == pw_hash:
                return u
    return None


# ════════════════════════════════════════════════════════════════════════════ #
#  DATA HELPERS                                                                #
# ════════════════════════════════════════════════════════════════════════════ #

def _load_json(p: Path):
    """Pure data load — never calls st.*. Returns empty structure on missing/bad file."""
    if not p.exists():
        return [] if p in (ORDERS, CUSTOMERS) else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [] if p in (ORDERS, CUSTOMERS) else {}


def _save_json(p: Path, data) -> bool:
    """Pure file write — never calls st.*. Returns False on failure."""
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def _save_master(silent: bool = False) -> bool:
    ok = _save_json(MASTER, st.session_state.master)
    if not silent:
        if ok:
            _alert("Master data saved successfully.", "success")
        else:
            _alert(f"Could not write {MASTER.name} — check file permissions.", "danger")
    return ok


def _engine() -> MRPEngine:
    return MRPEngine(st.session_state.master)


# ════════════════════════════════════════════════════════════════════════════ #
#  UI HELPERS                                                                  #
# ════════════════════════════════════════════════════════════════════════════ #

def _header(title: str, subtitle: str = ""):
    sub = f'<div class="pg-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="pg-header"><div><div class="pg-title">{title}</div>{sub}</div></div>',
        unsafe_allow_html=True,
    )


def _kpi(label: str, value, sub: str = "", color: str = ACCENT):
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-accent" style="background:{color};"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {'<div class="kpi-sub">' + sub + '</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)


def _alert(text: str, kind: str = "info"):
    st.markdown(
        f'<div class="jdk-alert {kind}">{text}</div>',
        unsafe_allow_html=True,
    )


def _sec(title: str):
    st.markdown(f'<div class="sec-label">{title}</div>', unsafe_allow_html=True)


def _badge(text: str, style: str = "info") -> str:
    return f'<span class="bdg bdg-{style}">{text}</span>'


def _fmt(n, dec: int = 1) -> str:
    try:
        return f"{float(n):,.{dec}f}"
    except (TypeError, ValueError):
        return str(n)


def _need_admin() -> bool:
    if st.session_state.get("role") != "Super Admin":
        _alert("This section requires <strong>Super Admin</strong> access.", "warning")
        return False
    return True


def _need_role(*roles) -> bool:
    if st.session_state.get("role") not in roles:
        _alert(f"Access restricted to: {', '.join(roles)}.", "warning")
        return False
    return True


def _safe_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Return only the columns from `cols` that actually exist in df."""
    return df[[c for c in cols if c in df.columns]]


# ════════════════════════════════════════════════════════════════════════════ #
#  SESSION INIT                                                                #
# ════════════════════════════════════════════════════════════════════════════ #

for _k, _v in {"role": None, "user": None, "reports": None, "master": None,
               "feas_result": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

if st.session_state.master is None:
    st.session_state.master = _load_json(MASTER)


# ════════════════════════════════════════════════════════════════════════════ #
#  LOGIN                                                                       #
# ════════════════════════════════════════════════════════════════════════════ #

if st.session_state.role is None:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-icon">🏭</div>'
        f'<div class="login-title">JDK Smart Factory</div>'
        f'<div class="login-sub">Enterprise Production Platform</div>',
        unsafe_allow_html=True,
    )

    username = st.text_input("Username", placeholder="Enter your username", key="li_user")
    password = st.text_input("Password", type="password", placeholder="Password", key="li_pw")

    if st.button("Sign In", type="primary", use_container_width=True):
        if not username.strip():
            _alert("Please enter your username.", "warning")
        elif not password:
            _alert("Please enter your password.", "warning")
        else:
            try:
                user = _authenticate(username.strip(), password)
            except RuntimeError as e:
                _alert(str(e), "danger")
                user = None
            if user:
                st.session_state.role = user["role"]
                st.session_state.user = user
                st.rerun()
            elif user is not None:
                _alert("Invalid username or password.", "danger")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ════════════════════════════════════════════════════════════════════════════ #
#  SIDEBAR                                                                     #
# ════════════════════════════════════════════════════════════════════════════ #

role       = st.session_state.role
user       = st.session_state.user or {}
role_color = ROLE_COLORS.get(role, MUTED)
display    = user.get("display_name", role)

st.sidebar.markdown(f"""
<div style="padding:0.5rem 0 1rem;">
  <div style="font-size:1.05rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.01em;">
    🏭 JDK Smart Factory
  </div>
  <div style="font-size:0.68rem;color:#64748b;margin-top:2px;">Enterprise Production Platform</div>
  <div style="margin-top:0.85rem;">
    <div style="font-size:0.68rem;color:#64748b;margin-bottom:2px;">SIGNED IN AS</div>
    <div style="font-size:0.85rem;color:#e2e8f0;font-weight:600;">{display}</div>
    <span class="role-chip" style="background:{role_color};">{role}</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()

NAV = {
    "📊  Dashboard":               "Dashboard",
    "👥  Customer Master":         "Customer Master",
    "📦  Product Master":          "Product Master",
    "🧪  Formula Management":      "Formula Management",
    "🪨  Raw Material Master":     "Raw Material Master",
    "🚚  Supplier Master":         "Supplier Master",
    "🏪  Inventory":               "Inventory",
    "🔍  Order Feasibility":       "Order Feasibility",
    "📋  Customer Orders":         "Customer Orders",
    "⚙️  Run ATP / MRP":           "Run ATP / MRP",
    "💾  Save / Backup":           "Save / Backup",
}

nav_key = st.sidebar.radio(
    "nav", list(NAV.keys()), label_visibility="collapsed"
)
menu = NAV[nav_key]

st.sidebar.divider()
if st.sidebar.button("Sign Out", use_container_width=True):
    for k in ("role", "user", "reports", "master", "feas_result"):
        st.session_state[k] = None
    st.rerun()

master = st.session_state.master


# ════════════════════════════════════════════════════════════════════════════ #
#  DASHBOARD                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #
if menu == "Dashboard":
    _header("Dashboard", "Live production & inventory snapshot")

    orders    = _load_json(ORDERS)
    customers = _load_json(CUSTOMERS)
    engine    = _engine()

    open_orders     = [o for o in orders if o.get("status","Open") not in STATUS_TERMINAL]
    critical_orders = [o for o in open_orders if o.get("priority") == "Critical"]
    inv_health      = engine.inventory_health()

    crit_mats = inv_health[inv_health["status"]=="CRITICAL"] if not inv_health.empty else pd.DataFrame()
    low_mats  = inv_health[inv_health["status"]=="LOW"]      if not inv_health.empty else pd.DataFrame()

    # ── Alert strip ──────────────────────────────────────────────────────────
    if not crit_mats.empty:
        _alert(f"⚠️ <strong>Critical stock:</strong> {', '.join(crit_mats['material'])} — below minimum level.", "danger")
    if not low_mats.empty:
        _alert(f"🔔 <strong>Low stock:</strong> {', '.join(low_mats['material'])} — below reorder point.", "warning")
    if critical_orders:
        _alert(f"🚨 <strong>{len(critical_orders)} Critical order(s)</strong> require immediate attention.", "danger")

    # ── KPI strip ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        active_prods = len([p for p,d in master.get("products",{}).items() if d.get("status")=="Active"])
        _kpi("Active Products", active_prods)
    with c2:
        _kpi("Customers", len(customers))
    with c3:
        _kpi("Open Orders", len(open_orders),
             sub=f"{len(critical_orders)} critical",
             color=DANGER if critical_orders else ACCENT)
    with c4:
        _kpi("Suppliers", sum(len(v) for v in master.get("suppliers",{}).values()))
    with c5:
        n_alerts = len(crit_mats) + len(low_mats)
        _kpi("Stock Alerts", n_alerts,
             sub=f"{len(crit_mats)} critical",
             color=DANGER if not crit_mats.empty else (WARN_C if n_alerts else SUCCESS))

    st.write("")

    # ── Finished goods + Inventory health ─────────────────────────────────────
    ca, cb = st.columns([3, 2], gap="medium")
    with ca:
        _sec("FINISHED GOODS INVENTORY")
        fg   = master.get("finished_goods", {})
        prods= master.get("products", {})
        fg_rows = []
        for p, v in fg.items():
            avail = float(v.get("available_kg", 0))
            fg_rows.append({
                "Product":        p,
                "Category":       prods.get(p, {}).get("category", "—"),
                "Available (kg)": f"{avail:,.0f}",
                "Bags":           f"{float(v.get('available_bags',0)):,.0f}",
                "Status":         "✅ In Stock" if avail > 0 else "⚠️ Out",
            })
        if fg_rows:
            st.dataframe(pd.DataFrame(fg_rows), width="stretch", hide_index=True)
        else:
            _alert("No finished goods records.", "info")

    with cb:
        _sec("INVENTORY HEALTH")
        if not inv_health.empty:
            disp = inv_health[["material","current_stock","reorder_point","status"]].copy()
            disp.columns = ["Material","Stock","Reorder At","Status"]
            st.dataframe(disp, width="stretch", hide_index=True)
        else:
            _alert("No inventory data.", "info")

    # ── Open orders ───────────────────────────────────────────────────────────
    if open_orders:
        st.write("")
        _sec("OPEN ORDERS")
        df_o = pd.DataFrame(open_orders)
        display_cols = ["order_no","customer","product","quantity","unit",
                        "priority","status","delivery_date"]
        df_disp = _safe_cols(df_o, display_cols).rename(columns={
            "order_no":"Order","customer":"Customer","product":"Product",
            "quantity":"Qty","unit":"Unit","priority":"Priority",
            "status":"Status","delivery_date":"Delivery",
        })
        st.dataframe(df_disp, width="stretch", hide_index=True)


# ════════════════════════════════════════════════════════════════════════════ #
#  CUSTOMER MASTER                                                             #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Customer Master":
    _header("Customer Master", "Manage customer accounts")

    customers = _load_json(CUSTOMERS)
    if customers:
        st.dataframe(pd.DataFrame(customers), width="stretch", hide_index=True)
    else:
        _alert("No customers on record yet.", "info")

    if role != "Super Admin":
        st.stop()

    st.divider()
    _sec("ADD NEW CUSTOMER")
    with st.form("add_cust", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name  = c1.text_input("Customer Name *")
        ctype = c2.selectbox("Type", ["Construction Company","Material Shop",
                                       "Government Project","Developer","Other"])
        loc   = c1.text_input("Delivery Location")
        terms = c2.text_input("Payment / Credit Terms")
        if st.form_submit_button("Add Customer", type="primary"):
            nm = name.strip()
            if not nm:
                _alert("Customer name is required.", "danger")
            elif any(c.get("customer","").strip().lower() == nm.lower() for c in customers):
                _alert(f"Customer '{nm}' already exists.", "warning")
            else:
                customers.append({"customer":nm,"customer_type":ctype,
                                  "delivery_location":loc.strip(),"terms":terms.strip()})
                _save_json(CUSTOMERS, customers)
                _alert(f"Customer '{nm}' added.", "success")
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  PRODUCT MASTER                                                              #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Product Master":
    _header("Product Master", "Products and configurations")

    products = master.get("products", {})
    rows = [{
        "Product":      p,
        "Category":     d.get("category","—"),
        "Bag Size (kg)":d.get("default_bag_size_kg",25),
        "Formula Lines":len(d.get("formula",{})),
        "Status":       d.get("status","Active"),
    } for p, d in products.items()]

    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        _alert("No products defined yet.", "info")

    if not _need_admin():
        st.stop()

    st.divider()
    _sec("ADD / EDIT PRODUCT")

    choices  = ["— New Product —"] + list(products.keys())
    selected = st.selectbox("Select to edit", choices)
    existing = products.get(selected, {}) if selected != "— New Product —" else {}

    with st.form("prod_form"):
        c1, c2 = st.columns(2)
        nm   = c1.text_input("Product Name *",
                              value="" if selected == "— New Product —" else selected)
        cat  = c2.text_input("Category", value=existing.get("category",""))
        bag  = c1.number_input("Default Bag Size (kg)", min_value=0.1,
                                value=float(existing.get("default_bag_size_kg",20)), step=0.5)
        stat = c2.selectbox("Status", ["Active","Inactive"],
                             index=0 if existing.get("status","Active")=="Active" else 1)
        if st.form_submit_button("Save Product", type="primary"):
            n = nm.strip()
            if not n:
                _alert("Product name is required.", "danger")
            else:
                # Rename: move old key to new key preserving formula
                if selected not in ("— New Product —", n) and selected in master["products"]:
                    master["products"][n] = master["products"].pop(selected)
                master["products"].setdefault(n, {"formula": {}})
                master["products"][n].update({
                    "category": cat.strip(),
                    "default_bag_size_kg": bag,
                    "status": stat,
                })
                st.session_state.master = master
                _save_master()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  FORMULA MANAGEMENT                                                          #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Formula Management":
    _header("Formula Management", "Bill of materials per product")

    products = master.get("products", {})
    if not products:
        _alert("No products defined yet.", "info")
        st.stop()

    product = st.selectbox("Product", list(products.keys()))
    formula = products[product].get("formula", {})
    total   = _engine().formula_total(product)

    ca, cb = st.columns([3, 1], gap="medium")
    with ca:
        if formula:
            st.dataframe(
                pd.DataFrame([{"Material":m,"Percentage (%)":pct}
                               for m, pct in formula.items()]),
                width="stretch", hide_index=True,
            )
        else:
            _alert("No formula configured for this product.", "warning")

    with cb:
        balanced = 99.5 <= total <= 100.5
        tc = SUCCESS if balanced else (WARN_C if total > 0 else DANGER)
        st.markdown(f"""
        <div class="kpi" style="text-align:center;margin-top:0.25rem;">
          <div class="kpi-accent" style="background:{tc};"></div>
          <div class="kpi-label">Formula Total</div>
          <div class="kpi-value" style="font-size:1.5rem;color:{tc};">{total:.2f}%</div>
          <div class="kpi-sub">{"✓ Balanced" if balanced else "⚠ Check total"}</div>
        </div>""", unsafe_allow_html=True)

    if not _need_admin():
        st.stop()

    st.divider()
    _sec("ADD / EDIT FORMULA LINE")
    raw_mats = list(master.get("raw_materials", {}).keys())
    if not raw_mats:
        _alert("Add raw materials first before configuring formulas.", "warning")
        st.stop()

    with st.form("formula_form"):
        c1, c2 = st.columns(2)
        # Use key to avoid stale pct when material changes
        mat = c1.selectbox("Raw Material", raw_mats, key="fm_mat")
        pct = c2.number_input("Percentage (%)", min_value=0.0, max_value=200.0,
                               value=0.0, step=0.1, key="fm_pct")
        if st.form_submit_button("Save Line", type="primary"):
            if pct <= 0:
                _alert("Percentage must be greater than 0.", "danger")
            else:
                master["products"][product].setdefault("formula", {})[mat] = pct
                st.session_state.master = master
                _save_master(silent=True)
                st.rerun()

    if formula:
        _sec("REMOVE FORMULA LINE")
        rm = st.selectbox("Select line to remove", list(formula.keys()), key="rm_line")
        if st.button("Remove Line", type="secondary"):
            del master["products"][product]["formula"][rm]
            st.session_state.master = master
            _save_master(silent=True)
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  RAW MATERIAL MASTER                                                         #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Raw Material Master":
    _header("Raw Material Master", "Materials, stock levels, and reorder settings")

    engine = _engine()
    health = engine.inventory_health()
    if not health.empty:
        st.dataframe(health, width="stretch", hide_index=True)
    else:
        _alert("No raw materials defined.", "info")

    if not _need_admin():
        st.stop()

    st.divider()
    _sec("ADD / EDIT RAW MATERIAL")

    UNIT_OPTS = ["kg", "pcs", "liter", "ton"]
    mat_names = ["— New Material —"] + list(master.get("raw_materials", {}).keys())
    selected  = st.selectbox("Select material", mat_names)

    if selected == "— New Material —":
        existing_inv  = {}
        existing_unit = "kg"
    else:
        existing_inv  = master.get("inventory", {}).get(selected, {})
        raw_unit = master.get("raw_materials", {}).get(selected, {}).get("unit", "kg")
        existing_unit = raw_unit if raw_unit in UNIT_OPTS else "kg"

    with st.form("rm_form"):
        c1, c2 = st.columns(2)
        nm      = c1.text_input("Material Name *",
                                 value="" if selected == "— New Material —" else selected)
        unit    = c2.selectbox("Unit", UNIT_OPTS,
                                index=UNIT_OPTS.index(existing_unit))
        current = c1.number_input("Current Stock",   min_value=0.0,
                                   value=float(existing_inv.get("current_stock", 0)))
        minimum = c2.number_input("Minimum Stock",   min_value=0.0,
                                   value=float(existing_inv.get("minimum_stock", 0)))
        reorder = c1.number_input("Reorder Point",   min_value=0.0,
                                   value=float(existing_inv.get("reorder_point", 0)))
        lead    = c2.number_input("Lead Time (days)",min_value=0.0,
                                   value=float(existing_inv.get("lead_time_days", 0)))

        if minimum > reorder > 0:
            _alert("Minimum stock is higher than reorder point — this is unusual.", "warning")

        if st.form_submit_button("Save Material", type="primary"):
            m = nm.strip()
            if not m:
                _alert("Material name is required.", "danger")
            else:
                master.setdefault("raw_materials", {})[m] = {"unit": unit}
                master.setdefault("inventory", {})[m] = {
                    "current_stock": current, "minimum_stock": minimum,
                    "reorder_point": reorder, "lead_time_days": lead,
                }
                st.session_state.master = master
                _save_master()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  SUPPLIER MASTER                                                             #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Supplier Master":
    _header("Supplier Master", "Supplier details and pricing by material")

    rows = []
    for mat, sups in master.get("suppliers", {}).items():
        for s in sups:
            rows.append({"Material": mat, **s})

    if rows:
        df = pd.DataFrame(rows).rename(columns={
            "supplier_name": "Supplier",    "price": "Unit Price",
            "lead_time_days": "Lead (days)","minimum_order_qty": "MOQ",
            "payment_terms": "Terms",       "delivery_cost": "Delivery Cost",
        })
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        _alert("No suppliers on record.", "info")

    if not _need_admin():
        st.stop()

    st.divider()
    _sec("ADD SUPPLIER")

    raw_mats = list(master.get("raw_materials", {}).keys())
    if not raw_mats:
        _alert("Add raw materials first before adding suppliers.", "warning")
        st.stop()

    with st.form("sup_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        mat      = c1.selectbox("Material Supplied", raw_mats)
        supplier = c2.text_input("Supplier Name *")
        price    = c1.number_input("Unit Price", min_value=0.0, step=0.001, format="%.3f")
        lead     = c2.number_input("Lead Time (days)", min_value=0.0)
        moq      = c1.number_input("Min. Order Qty",   min_value=0.0)
        pay      = c2.text_input("Payment Terms")
        delivery = c1.number_input("Delivery Cost",    min_value=0.0)
        if st.form_submit_button("Add Supplier", type="primary"):
            s = supplier.strip()
            if not s:
                _alert("Supplier name is required.", "danger")
            else:
                master.setdefault("suppliers", {}).setdefault(mat, []).append({
                    "supplier_name": s, "price": price, "lead_time_days": lead,
                    "minimum_order_qty": moq, "payment_terms": pay.strip(),
                    "delivery_cost": delivery,
                })
                st.session_state.master = master
                _save_master(silent=True)
                _alert(f"Supplier '{s}' added for {mat}.", "success")
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  INVENTORY                                                                   #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Inventory":
    _header("Inventory", "Finished goods and raw material stock")

    tab_fg, tab_rm = st.tabs(["Finished Goods", "Raw Materials"])

    with tab_fg:
        fg = master.get("finished_goods", {})
        rows = [{
            "Product":        p,
            "Available (kg)": float(v.get("available_kg", 0)),
            "Bags":           float(v.get("available_bags", 0)),
            "Status":         "In Stock" if float(v.get("available_kg",0)) > 0 else "Out of Stock",
        } for p, v in fg.items()]

        if rows:
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        else:
            _alert("No finished goods records.", "info")

        if role in ("Super Admin", "Warehouse User"):
            st.divider()
            _sec("UPDATE STOCK")
            prods = list(master.get("products", {}).keys())
            if prods:
                with st.form("fg_form"):
                    c1, c2 = st.columns(2)
                    p    = c1.selectbox("Product", prods)
                    kg   = c1.number_input("Available (kg)", min_value=0.0,
                                           value=float(master.get("finished_goods",{}).get(p,{}).get("available_kg",0)))
                    bags = c2.number_input("Available (bags)", min_value=0.0,
                                           value=float(master.get("finished_goods",{}).get(p,{}).get("available_bags",0)))
                    if st.form_submit_button("Update Stock", type="primary"):
                        master.setdefault("finished_goods", {})[p] = {
                            "available_kg": kg, "available_bags": bags,
                        }
                        st.session_state.master = master
                        _save_master()
                        st.rerun()

    with tab_rm:
        health = _engine().inventory_health()
        if not health.empty:
            st.dataframe(health, width="stretch", hide_index=True)
        else:
            _alert("No raw material inventory data.", "info")


# ════════════════════════════════════════════════════════════════════════════ #
#  ORDER FEASIBILITY CHECK                                                     #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Order Feasibility":
    _header("Order Feasibility Check", "Real-time ATP and production feasibility")

    customers = _load_json(CUSTOMERS)
    products  = list(master.get("products", {}).keys())

    if not products:
        _alert("No products defined. Add products first.", "warning")
        st.stop()

    cust_names = [c.get("customer","") for c in customers if c.get("customer")] or ["Walk-in"]

    col_form, col_res = st.columns([1, 1], gap="large")

    with col_form:
        _sec("ORDER PARAMETERS")
        with st.form("feas_form"):
            customer = st.selectbox("Customer", cust_names)
            product  = st.selectbox("Product", products)
            def_bag  = float(master["products"][product].get("default_bag_size_kg", 20))

            c1, c2 = st.columns(2)
            qty      = c1.number_input("Quantity *", min_value=0.0, step=1.0)
            unit     = c2.selectbox("Unit", ["bags","kg","tons"])
            bag_size = c1.number_input("Bag Size (kg)", min_value=0.1, value=def_bag)
            priority = c2.selectbox("Priority", ["Critical","High","Normal","Low"], index=2)
            delivery = st.date_input("Requested Delivery Date", value=date.today())
            run = st.form_submit_button("Run Feasibility Check", type="primary",
                                        use_container_width=True)

    if run:
        if qty <= 0:
            with col_form:
                _alert("Quantity must be greater than zero.", "danger")
        else:
            with st.spinner("Checking feasibility…"):
                try:
                    order = {
                        "customer": customer, "product": product,
                        "quantity": qty, "unit": unit,
                        "bag_size_kg": bag_size, "priority": priority,
                        "delivery_date": str(delivery),
                    }
                    existing = _load_json(ORDERS)
                    summary, detail = _engine().feasibility_single_order(order, existing)
                    st.session_state.feas_result = (summary, detail)
                except MRPValidationError as e:
                    with col_res:
                        _alert(f"Validation error: {e}", "danger")
                    st.session_state.feas_result = None

    with col_res:
        res = st.session_state.get("feas_result")
        if res:
            summary, detail = res
            fs = summary["feasibility_status"]

            _sec("FEASIBILITY RESULT")
            if "READY" in fs:
                _alert(f"✅ <strong>{fs}</strong> — Stock is available for immediate shipment.", "success")
            elif "PRODUCE" in fs:
                _alert(f"🔧 <strong>{fs}</strong> — All materials in stock. Production can start.", "info")
            else:
                lim = summary.get("limiting_material", "")
                _alert(f"⛔ <strong>{fs}</strong>"
                       + (f" — Procure <strong>{lim}</strong> first." if lim else "."),
                       "danger")

            c1, c2 = st.columns(2)
            with c1: _kpi("ATP (kg)", _fmt(summary["available_to_promise_kg"], 0))
            with c2: _kpi("Earliest Delivery", summary["earliest_delivery_date"], color=SUCCESS)
            st.write("")
            c3, c4 = st.columns(2)
            with c3: _kpi("Production Needed (kg)", _fmt(summary["production_required_kg"], 0))
            with c4: _kpi("Est. Production Days",   summary["estimated_production_days"])

            cost = summary.get("estimated_material_cost", 0)
            if cost > 0:
                st.write("")
                _kpi("Est. Material Cost", f"${_fmt(cost, 2)}", color=MUTED)

            if not detail.empty:
                st.write("")
                _sec("MATERIAL BREAKDOWN")
                st.dataframe(detail, width="stretch", hide_index=True)


# ════════════════════════════════════════════════════════════════════════════ #
#  CUSTOMER ORDERS                                                             #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Customer Orders":
    _header("Customer Orders", "Sales order management")

    orders    = _load_json(ORDERS)
    customers = _load_json(CUSTOMERS)
    products  = list(master.get("products", {}).keys())

    # ── Filters ──────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    f_status   = fc1.selectbox("Status", ["All"] + ORDER_STATUSES)
    f_priority = fc2.selectbox("Priority", ["All","Critical","High","Normal","Low"])
    f_product  = fc3.selectbox("Product",  ["All"] + products)

    filtered = orders
    if f_status   != "All": filtered = [o for o in filtered if o.get("status") == f_status]
    if f_priority != "All": filtered = [o for o in filtered if o.get("priority") == f_priority]
    if f_product  != "All": filtered = [o for o in filtered if o.get("product") == f_product]

    if filtered:
        DISPLAY_COLS = ["order_no","customer","product","quantity","unit",
                        "priority","status","delivery_date","reserved_fg_kg"]
        df_o = _safe_cols(pd.DataFrame(filtered), DISPLAY_COLS).rename(columns={
            "order_no":"Order No","customer":"Customer","product":"Product",
            "quantity":"Qty","unit":"Unit","priority":"Priority",
            "status":"Status","delivery_date":"Delivery","reserved_fg_kg":"Reserved FG (kg)",
        })
        st.dataframe(df_o, width="stretch", hide_index=True)
        st.caption(f"Showing {len(filtered)} of {len(orders)} order(s).")
    else:
        _alert("No orders match the selected filters.", "info")

    if role not in ("Super Admin", "Production Planner"):
        st.stop()

    st.divider()
    _sec("CREATE NEW ORDER")

    cust_names = [c.get("customer","") for c in customers if c.get("customer")] or ["Walk-in"]

    with st.form("order_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        customer = c1.selectbox("Customer", cust_names)
        product  = c2.selectbox("Product", products) if products else c2.selectbox("Product", ["—"])
        def_bag  = float(master["products"].get(product,{}).get("default_bag_size_kg",20)) if products else 20.0

        c3, c4 = st.columns(2)
        qty      = c3.number_input("Quantity *", min_value=0.0, step=1.0)
        unit     = c4.selectbox("Unit", ["bags","kg","tons"])
        bag_size = c3.number_input("Bag Size (kg)", min_value=0.1, value=def_bag)
        priority = c4.selectbox("Priority", ["Critical","High","Normal","Low"], index=2)
        status   = c3.selectbox("Status", ORDER_STATUSES)
        delivery = c4.date_input("Delivery Date", value=date.today())
        order_no = c3.text_input("Order No", value=f"SO-{len(orders)+1:04d}")

        if st.form_submit_button("Create Order", type="primary"):
            if not products:
                _alert("Add products before creating orders.", "danger")
            elif qty <= 0:
                _alert("Quantity must be greater than zero.", "danger")
            elif not order_no.strip():
                _alert("Order number is required.", "danger")
            elif any(o.get("order_no","") == order_no.strip() for o in orders):
                _alert(f"Order number '{order_no}' already exists.", "warning")
            else:
                orders.append({
                    "order_no":     order_no.strip(),
                    "customer":     customer,
                    "product":      product,
                    "quantity":     qty,
                    "unit":         unit,
                    "bag_size_kg":  bag_size,
                    "priority":     priority,
                    "status":       status,
                    "delivery_date":str(delivery),
                    "reserved_fg_kg": 0,
                })
                _save_json(ORDERS, orders)
                _alert(f"Order {order_no} created.", "success")
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════ #
#  RUN ATP / MRP                                                               #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Run ATP / MRP":
    _header("ATP / MRP Run", "Batch feasibility across all open orders")

    orders = _load_json(ORDERS)
    active = [o for o in orders if o.get("status","Open") not in STATUS_TERMINAL]

    if not active:
        _alert("No active orders to plan. All orders are Shipped, Closed, or Cancelled.", "info")
        st.stop()

    st.caption(f"{len(active)} active order(s) — sorted by priority then delivery date.")

    if st.button("▶  Run ATP / MRP", type="primary"):
        # Clear stale results before running
        st.session_state.reports = None
        with st.spinner("Running MRP engine…"):
            try:
                reports = _engine().run_fulfillment_mrp(orders)
                st.session_state.reports = reports
            except MRPValidationError as e:
                _alert(f"MRP error: {e}", "danger")

    rpts = st.session_state.get("reports")
    if rpts:
        f = rpts.get("order_feasibility", pd.DataFrame())

        # ── Summary KPIs ──────────────────────────────────────────────────────
        if not f.empty:
            st.write("")
            k1, k2, k3, k4 = st.columns(4)
            n_ready   = int((f["feasibility_status"] == "READY FOR SHIPMENT").sum())
            n_produce = int((f["feasibility_status"] == "CAN PRODUCE").sum())
            n_short   = int(f["feasibility_status"].str.contains("SHORTAGE").sum())
            total_cost= float(f["estimated_material_cost"].sum()) if "estimated_material_cost" in f.columns else 0.0

            with k1: _kpi("Ready for Shipment", n_ready,   color=SUCCESS)
            with k2: _kpi("Can Produce",         n_produce, color=ACCENT)
            with k3: _kpi("Material Shortage",   n_short,   color=DANGER if n_short else MUTED)
            with k4: _kpi("Est. Material Cost", f"${total_cost:,.0f}", color=MUTED)

        # ── Reorder alerts ─────────────────────────────────────────────────────
        ra = rpts.get("reorder_alerts", pd.DataFrame())
        if ra is not None and not ra.empty:
            st.write("")
            crit = ra[ra["severity"]=="CRITICAL"]
            warn = ra[ra["severity"]=="WARNING"]
            if not crit.empty:
                _alert(f"⛔ <strong>CRITICAL — below minimum stock:</strong> {', '.join(crit['material'])}", "danger")
            if not warn.empty:
                _alert(f"⚠️ <strong>WARNING — below reorder point:</strong> {', '.join(warn['material'])}", "warning")

        st.write("")

        # ── Result tabs ────────────────────────────────────────────────────────
        tab_names = ["Order Feasibility","Material Detail",
                     "Requirements Summary","FG Reservations","Reorder Alerts"]
        tab_keys  = ["order_feasibility","order_material_detail",
                     "raw_material_requirements_summary","fg_reservations","reorder_alerts"]

        tabs = st.tabs(tab_names)
        for tab, key in zip(tabs, tab_keys):
            with tab:
                df = rpts.get(key)
                if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                    st.dataframe(df, width="stretch", hide_index=True)
                else:
                    _alert("No data for this section.", "info")

        # ── Export ─────────────────────────────────────────────────────────────
        st.divider()
        out = REPORTS / "jdk_atp_mrp_report.xlsx"
        try:
            _engine().export_excel(rpts, out)
            with open(out, "rb") as fh:
                st.download_button(
                    "⬇  Download Excel Report",
                    fh.read(),
                    "jdk_atp_mrp_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )
        except Exception as e:
            _alert(f"Could not generate Excel export: {e}", "warning")


# ════════════════════════════════════════════════════════════════════════════ #
#  SAVE / BACKUP                                                               #
# ════════════════════════════════════════════════════════════════════════════ #
elif menu == "Save / Backup":
    _header("Save / Backup", "Persist master data and manage backups")

    if not _need_admin():
        st.stop()

    _sec("SAVE MASTER DATA")
    st.write("Writes the current in-memory master data to disk. Do this after any master changes.")
    if st.button("Save Master Data", type="primary"):
        _save_master()

    st.divider()

    _sec("DOWNLOAD BACKUPS")
    col1, col2, col3 = st.columns(3)
    with col1:
        master_bytes = json.dumps(master, ensure_ascii=False, indent=2).encode()
        st.download_button("⬇ Master Data", master_bytes,
                           "master_data_backup.json", "application/json",
                           use_container_width=True)
    with col2:
        orders_bytes = json.dumps(_load_json(ORDERS), ensure_ascii=False, indent=2).encode()
        st.download_button("⬇ Orders", orders_bytes,
                           "customer_orders_backup.json", "application/json",
                           use_container_width=True)
    with col3:
        cust_bytes = json.dumps(_load_json(CUSTOMERS), ensure_ascii=False, indent=2).encode()
        st.download_button("⬇ Customers", cust_bytes,
                           "customers_backup.json", "application/json",
                           use_container_width=True)

    st.divider()
    _sec("RESTORE MASTER DATA")
    _alert("Restoring will overwrite the current master data. Download a backup first.", "warning")

    uploaded = st.file_uploader("Upload master_data.json", type="json", key="restore_up")
    if uploaded is not None:
        try:
            restored = json.loads(uploaded.read().decode("utf-8"))
            required = {"products", "raw_materials", "inventory"}
            missing  = required - set(restored.keys())
            if missing:
                _alert(f"File is missing required keys: {missing}", "danger")
            else:
                if st.button("✅ Confirm Restore", type="primary"):
                    st.session_state.master = restored
                    # Also clear stale MRP reports
                    st.session_state.reports = None
                    _save_json(MASTER, restored)
                    _alert("Master data restored successfully.", "success")
                    st.rerun()
        except json.JSONDecodeError as e:
            _alert(f"Invalid JSON file: {e}", "danger")
