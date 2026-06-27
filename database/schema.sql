-- ════════════════════════════════════════════════════════════════════════════
--  JDK Smart Factory Platform — MySQL Schema
--  Engine: InnoDB | Charset: utf8mb4
--  Run once against the jdk_factory database.
-- ════════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS jdk_factory
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE jdk_factory;

-- ── Users & Auth ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(80)  NOT NULL UNIQUE,
  password_hash CHAR(64)     NOT NULL,          -- SHA-256 hex
  role          ENUM('admin','manager','operator','viewer','write') NOT NULL DEFAULT 'viewer',
  reset_token   VARCHAR(64)  NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── App Settings ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
  key_name  VARCHAR(120) NOT NULL PRIMARY KEY,
  val       TEXT         NOT NULL,
  updated_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Factory Config ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS factory_config (
  key_name   VARCHAR(120) NOT NULL PRIMARY KEY,
  val        TEXT         NOT NULL
) ENGINE=InnoDB;

-- ── Customers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
  id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  customer   VARCHAR(200) NOT NULL UNIQUE,
  email      VARCHAR(200) NULL,
  phone      VARCHAR(50)  NULL,
  address    TEXT         NULL,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Products (Finished Goods definitions) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
  id                   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name                 VARCHAR(200) NOT NULL UNIQUE,
  category             VARCHAR(100) NULL,
  default_bag_size_kg  DECIMAL(10,3) NOT NULL DEFAULT 50,
  status               ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Finished Goods Inventory ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS finished_goods (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_name   VARCHAR(200) NOT NULL UNIQUE,
  available_kg   DECIMAL(14,3) NOT NULL DEFAULT 0,
  available_bags INT           NOT NULL DEFAULT 0,
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (product_name) REFERENCES products(name) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Raw Materials ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_materials (
  id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL UNIQUE,
  unit VARCHAR(20)  NOT NULL DEFAULT 'kg'
) ENGINE=InnoDB;

-- ── Inventory (stock levels per raw material) ────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory (
  id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  material_name   VARCHAR(200) NOT NULL UNIQUE,
  current_stock   DECIMAL(14,3) NOT NULL DEFAULT 0,
  minimum_stock   DECIMAL(14,3) NOT NULL DEFAULT 0,
  reorder_point   DECIMAL(14,3) NOT NULL DEFAULT 0,
  lead_time_days  SMALLINT      NOT NULL DEFAULT 0,
  updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (material_name) REFERENCES raw_materials(name) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Product Formulas (BOM lines) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_formulas (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_name   VARCHAR(200) NOT NULL,
  material_name  VARCHAR(200) NOT NULL,
  percentage     DECIMAL(8,4) NOT NULL,
  UNIQUE KEY uq_formula_line (product_name, material_name),
  FOREIGN KEY (product_name)  REFERENCES products(name)      ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (material_name) REFERENCES raw_materials(name) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Suppliers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
  id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  material_name     VARCHAR(200) NOT NULL,
  supplier_name     VARCHAR(200) NOT NULL,
  price             DECIMAL(12,4) NOT NULL DEFAULT 0,
  lead_time_days    SMALLINT      NOT NULL DEFAULT 0,
  minimum_order_qty DECIMAL(14,3) NOT NULL DEFAULT 0,
  payment_terms     VARCHAR(100)  NULL,
  delivery_cost     DECIMAL(12,2) NOT NULL DEFAULT 0,
  UNIQUE KEY uq_supplier (material_name, supplier_name),
  FOREIGN KEY (material_name) REFERENCES raw_materials(name) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Customer Orders ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customer_orders (
  id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_no     VARCHAR(50)   NOT NULL UNIQUE,
  customer     VARCHAR(200)  NOT NULL,
  product      VARCHAR(200)  NOT NULL,
  quantity_kg  DECIMAL(14,3) NOT NULL,
  bag_size_kg  DECIMAL(10,3) NOT NULL DEFAULT 50,
  bags         INT           NOT NULL DEFAULT 0,
  delivery_date DATE         NULL,
  status       ENUM('Pending','Confirmed','In Production','Ready','Shipped','Closed','Cancelled')
               NOT NULL DEFAULT 'Pending',
  notes        TEXT          NULL,
  created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Production Schedules ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS production_schedules (
  id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  schedule_id         VARCHAR(50)   NOT NULL UNIQUE,
  product             VARCHAR(200)  NOT NULL,
  planned_qty_kg      DECIMAL(14,3) NOT NULL,
  start_date          DATE          NOT NULL,
  end_date            DATE          NOT NULL,
  shift               ENUM('Day','Night','Full Day') NOT NULL DEFAULT 'Day',
  manpower_available  SMALLINT      NOT NULL DEFAULT 0,
  manpower_required   SMALLINT      NOT NULL DEFAULT 0,
  status              ENUM('Planned','Confirmed','In Progress','Completed','Cancelled')
                      NOT NULL DEFAULT 'Planned',
  linked_order_no     VARCHAR(50)   NULL,
  notes               TEXT          NULL,
  created_by          VARCHAR(80)   NULL,
  created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Note: the first 'admin' user is created automatically by the app on first
-- boot (see backend/app.py _bootstrap()) when this users table is empty —
-- not seeded here, so no credential ever lives in source control. Set
-- DEFAULT_ADMIN_PASSWORD in your .env to control it.

-- ── Default factory config ────────────────────────────────────────────────────
INSERT IGNORE INTO factory_config (key_name, val) VALUES
  ('batch_size_kg',                  '1000'),
  ('normalize_formulas',             'true'),
  ('daily_production_capacity_kg',   '20000'),
  ('working_days_per_week',          '6'),
  ('company_name',                   'JDK Smart Factory');
