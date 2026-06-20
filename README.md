# JDK Smart Factory Platform — Enterprise Edition

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Login credentials
Credentials are stored in `config/auth.json` as SHA-256 hashed passwords.
**No plaintext secrets in source code.**

| Username   | Password      | Role               |
|------------|---------------|--------------------|
| admin      | admin123      | Super Admin        |
| planner    | planner123    | Production Planner |
| warehouse  | warehouse123  | Warehouse User     |
| purchase   | purchase123   | Purchasing User    |
| viewer     | view123       | Management Viewer  |

To add/change users, edit `config/auth.json`. Generate new hashes with:
```python
import hashlib
hashlib.sha256("yourpassword".encode()).hexdigest()
```

## Fixes in this release
**Auth**
- Credentials moved out of source code into `config/auth.json`
- Passwords stored as SHA-256 hashes (never plaintext)
- Login now uses username + password (not role selector)
- `_authenticate()` validates hash; wrong credentials blocked cleanly

**Engine (`mrp_engine.py`)**
- `MRPConfig.from_dict()` ignores unknown config keys (no crash on extra fields)
- `_to_kg()`: bag_size=0 now correctly falls back to product default (was silently wrong)
- `inventory_health()` sorts CRITICAL → LOW → OK using a numeric key, not string sort
- Empty reorder_alerts returns typed empty DataFrame (no KeyError on `.empty`)
- Excel export: conditional row colouring now applied (ok/warn/err formats were defined but never used)
- Excel export: `max_data` NaN guard prevents crash on single-row sheets
- `_production_material_cost` cost rows use `None` for missing price (not string "—")

**App (`app.py`)**
- `_safe_cols()` helper: DataFrame column subset never crashes on missing columns
- Formula form: pct pre-fill reset to 0.0 (not stale value from prior material selection)
- `save_master()` now uses consistent `_alert()` helper (was mixing `st.success()`)
- `st.session_state.reports` cleared before each new MRP run (no stale data displayed)
- Restore: added "Confirm Restore" button guard before overwriting master data
- Inventory page switched from `st.radio` to `st.tabs` (cleaner UX)
- `_safe_cols()` applied to all DataFrame column subsets (no KeyError on new/missing fields)
- All `pd.DataFrame(filtered)[cols]` calls guarded against missing columns

**Design / responsiveness**
- KPI cards use `height:100%` + consistent padding
- `@media (max-width:768px)` breakpoint stacks columns on mobile
- Nav pills use proper `data-checked` selector (active state reliable)
- Login rendered as a centred card without broken column layout
- Alert helper unified as `_alert()` throughout (no more mixed `st.error`/`st.success`)
- Sidebar `min-width: 220px` prevents collapse on narrow desktops
