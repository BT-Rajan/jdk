# JDK Smart Factory Platform v2.0

A modern, AI-powered Smart Manufacturing ERP — re-architected as a clean API + SPA.

## Stack
- **Backend**: Flask REST API (`backend/app.py`)
- **Engine**: MRP Engine (`backend/mrp_engine.py`) — original business logic preserved
- **Frontend**: Vanilla JS SPA (`frontend/`) — zero build step required
- **AI**: DeepSeek Chat API — natural language factory assistant
- **Storage**: JSON flat-files in `data/` and `config/` (zero-DB, easily upgradeable)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the platform (API + frontend, single port)
python serve.py

# 3. Open browser
open http://localhost:5000
```

## Default Login

On first boot (when the `users` table is empty), the app creates a single
default `admin` account automatically. To control its password, set
`DEFAULT_ADMIN_PASSWORD` in your `.env` file **before** the first run:

```
DEFAULT_ADMIN_PASSWORD=choose-a-strong-password
```

If you don't set it, a random password is generated and **not printed
anywhere** — use the "Forgot password" flow on the login screen right after
first boot to set your own password via a reset token.

For local testing with realistic data and one login per role, see
`database/seed.sql` (documented in `database/README.md`).

## API Endpoints

All endpoints under `/api/`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Sign in |
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/forgot-password` | Request reset |
| POST | `/api/auth/reset-password` | Apply reset token |
| POST | `/api/auth/logout` | Sign out |
| GET | `/api/auth/me` | Current user |
| GET | `/api/dashboard` | Dashboard KPIs & data |
| POST | `/api/chat` | AI chat (DeepSeek) |
| GET/POST | `/api/settings` | App settings |
| GET/POST | `/api/customers` | Customers |
| GET/POST | `/api/products` | Products |
| GET/POST | `/api/formulas/<product>` | Formula lines |
| GET/POST | `/api/raw-materials` | Raw materials |
| GET/POST | `/api/suppliers` | Suppliers |
| GET/POST | `/api/inventory/finished-goods` | FG stock |
| GET | `/api/inventory/health` | Inventory health |
| POST | `/api/feasibility` | Single order feasibility |
| GET/POST/PATCH/DELETE | `/api/orders` | Order management |
| POST | `/api/mrp/run` | Full MRP run |
| POST | `/api/mrp/export` | Export MRP to Excel |
| GET | `/api/backup/master` | Download master data |
| POST | `/api/restore/master` | Restore master data |

## AI Chat (DeepSeek)

1. Go to **Settings → AI / DeepSeek**
2. Enter your API key from [platform.deepseek.com](https://platform.deepseek.com)
3. Open **AI Chat** and ask anything in plain English

## UI Configuration

The frontend is fully configurable via CSS variables in `frontend/styles/tokens.css`.
Change colours, fonts, spacing and radii without touching any component code.

## Project Structure

```
jdk/
├── backend/
│   ├── app.py              # Flask REST API (all endpoints)
│   └── mrp_engine.py       # Core MRP business logic
├── frontend/
│   ├── index.html          # SPA shell
│   ├── styles/
│   │   ├── tokens.css      # Design tokens (UI config)
│   │   ├── main.css        # Layout
│   │   └── components.css  # UI components
│   ├── components/
│   │   ├── api.js          # API client
│   │   ├── ui.js           # UI helpers
│   │   └── app.js          # App controller / router
│   └── pages/              # One file per page
├── data/                   # JSON data store
├── config/                 # auth.json, settings.json
├── reports/                # Generated Excel reports
├── serve.py                # Single-process launcher
└── requirements.txt
```
