# JDK Smart Factory — MySQL Setup

## 1. Prerequisites
- XAMPP running with MySQL on port 3306

## 2. Create the database
Open phpMyAdmin (http://localhost/phpmyadmin) or MySQL CLI and run:

```sql
SOURCE /path/to/jdk/database/schema.sql;
```

Or via MySQL CLI:
```bash
mysql -u root -p < database/schema.sql
```

## 3. Configure .env
Copy `.env.example` to `.env` in the project root and fill in:

```
SECRET_KEY=any-long-random-string
DB_HOST=localhost
DB_PORT=3306
DB_NAME=jdk_factory
DB_USER=root
DB_PASSWORD=          # blank for default XAMPP root
```

## 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

## 5. Run the app
```bash
python serve.py
```

The app creates a default **admin / admin123** user on first boot if the
users table is empty.

## 6. Migrate existing JSON data (one-time)
If you have existing data in `data/` JSON files, call the migration endpoint
once after startup:

```
POST http://localhost:5000/api/migrate-json
```
(must be logged in as admin)

This imports `master_data.json`, `customer_orders.json`, `customers.json`,
and `config/auth.json` into MySQL. Safe to call multiple times.
