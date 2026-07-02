# Install Guide — JDK Smart Factory Platform v2.0

This guide walks through setting up the platform locally: a Flask REST API backend, a vanilla-JS SPA frontend, and a MySQL database.

## Prerequisites

- **Python** 3.9+ and `pip`
- **MySQL** server (the `.env.example` defaults match a local **XAMPP** MySQL install, but any MySQL/MariaDB instance works)
- Git

## 1. Clone the repository

```bash
git clone https://github.com/BT-Rajan/jdk.git
cd jdk
```

## 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
```

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `flask`, `flask-cors` — REST API and CORS support
- `PyMySQL` — MySQL driver
- `python-dotenv` — loads `.env` config
- `pandas`, `xlsxwriter`, `openpyxl` — MRP export / Excel reporting

## 4. Configure environment variables

Copy the example env file and edit it:

```bash
cp .env.example .env
```

Set the following in `.env`:

```
# Flask
SECRET_KEY=change-me-in-production
FLASK_ENV=production

# Optional: password for the auto-created first-run 'admin' account.
# Leave blank to have the app generate a random one-time password
# (never logged) — then use "Forgot password" on first login.
DEFAULT_ADMIN_PASSWORD=

# MySQL (XAMPP defaults shown)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jdk_factory
DB_USER=root
DB_PASSWORD=
DB_CHARSET=utf8mb4
```

At minimum, set a strong `SECRET_KEY` and matching MySQL credentials.

## 5. Set up the MySQL database

Make sure MySQL is running, then create the database referenced by `DB_NAME`:

```sql
CREATE DATABASE jdk_factory CHARACTER SET utf8mb4;
```

For local testing with realistic sample data and one login per role, see `database/seed.sql` (documented in `database/README.md`).

## 6. Start the platform

```bash
python serve.py
```

This launches the Flask API and serves the frontend SPA from a single port.

## 7. Open the app

Navigate to:

```
http://localhost:5000
```

On first boot, if the `users` table is empty, a default `admin` account is created automatically using `DEFAULT_ADMIN_PASSWORD` (if set), or a random one-time password (not logged — use "Forgot password" on the login screen to set your own).

## 8. (Optional) Configure the AI Chat feature

1. Go to **Settings → AI / DeepSeek** in the app
2. Enter your API key from [platform.deepseek.com](https://platform.deepseek.com)
3. Open **AI Chat** and start asking questions in plain English

## 9. (Optional) Customize the UI

Edit `frontend/styles/tokens.css` to change colors, fonts, spacing, and radii without touching component code.

## Troubleshooting

- **Can't connect to MySQL**: verify `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` in `.env` match your MySQL instance, and that the `jdk_factory` database exists.
- **Port 5000 already in use**: stop the conflicting process or adjust the port in `serve.py`.
- **Lost admin password**: use the "Forgot password" flow on the login screen to request a reset token.
