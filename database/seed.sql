-- ════════════════════════════════════════════════════════════════════════════
--  JDK Smart Factory Platform — Test Data Seed
--  Run AFTER schema.sql against the jdk_factory database.
--  Domain: cement manufacturing (matches data/master_data.json conventions)
--
--  Usage:
--    mysql -u root -p jdk_factory < database/schema.sql
--    mysql -u root -p jdk_factory < database/seed.sql
--
--  This file is idempotent-ish: it clears existing rows from the tables it
--  seeds (NOT the `users` table beyond test accounts) before inserting, so it
--  can be re-run safely during testing. It does not touch `settings` or
--  `factory_config` API-managed secrets beyond a couple of safe defaults.
-- ════════════════════════════════════════════════════════════════════════════

USE jdk_factory;

SET FOREIGN_KEY_CHECKS = 0;

-- ── Reset test data (safe to re-run) ──────────────────────────────────────────
TRUNCATE TABLE production_schedules;
TRUNCATE TABLE customer_orders;
TRUNCATE TABLE suppliers;
TRUNCATE TABLE product_formulas;
TRUNCATE TABLE inventory;
TRUNCATE TABLE finished_goods;
TRUNCATE TABLE raw_materials;
TRUNCATE TABLE products;
TRUNCATE TABLE customers;
DELETE FROM users WHERE username IN ('admin','manager1','operator1','viewer1','writer1');

SET FOREIGN_KEY_CHECKS = 1;

-- ════════════════════════════════════════════════════════════════════════════
--  USERS — one per role for RBAC testing (username / password)
--    admin     / admin123     -> role: admin     (full access)
--    manager1  / manager123   -> role: manager    (read, write, orders, inventory)
--    operator1 / operator123  -> role: operator   (read, write, inventory)
--    viewer1   / viewer123    -> role: viewer     (read-only)
--    writer1   / write123     -> role: write      (read, write — no orders/inventory perms)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO users (username, password_hash, role) VALUES
  ('admin',     '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin'),
  ('manager1',  '866485796cfa8d7c0cf7111640205b83076433547577511d81f8030ae99ecea5', 'manager'),
  ('operator1', 'ec6e1c25258002eb1c67d15c7f45da7945fa4c58778fd7d88faa5e53e3b4698d', 'operator'),
  ('viewer1',   '65375049b9e4d7cad6c9ba286fdeb9394b28135a3e84136404cfccfdcc438894', 'viewer'),
  ('writer1',   '465b53549e851542d13c958b7da49a0a99874b0b6f4a02825f7af4174e7d7ee4', 'write');

-- ════════════════════════════════════════════════════════════════════════════
--  CUSTOMERS — mix of complete and partial contact info (tests optional fields)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO customers (customer, email, phone, address) VALUES
  ('Acme Constructions',     'procurement@acmeconstructions.example.com', '+91 98765 43210', '14 Anna Salai, Chennai, Tamil Nadu 600002'),
  ('BuildRight Developers',  'contact@buildright.example.com',            '+91 98765 11122', '221 MG Road, Bangalore, Karnataka 560001'),
  ('Chennai Infra Projects', 'info@chennaiinfra.example.com',             '+91 99000 22334', '45 OMR, Chennai, Tamil Nadu 600096'),
  ('Kovai Builders',         NULL,                                        '+91 90000 55667', '12 Trichy Road, Coimbatore, Tamil Nadu 641018'),
  ('South Shore Realty',     'sales@southshore.example.com',              NULL,              '8 Marine Drive, Kochi, Kerala 682031'),
  ('Madurai Civil Works',    'civilworks@maduraiworks.example.com',       '+91 98000 99887', '67 Bypass Road, Madurai, Tamil Nadu 625010');

-- ════════════════════════════════════════════════════════════════════════════
--  PRODUCTS — 4 active SKUs + 1 inactive (tests status filtering)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO products (name, category, default_bag_size_kg, status) VALUES
  ('OPC 53 Grade Cement',      'Cement',    50, 'Active'),
  ('PPC Cement',                'Cement',    50, 'Active'),
  ('OPC 43 Grade Cement',      'Cement',    50, 'Active'),
  ('White Cement',             'Cement',    25, 'Active'),
  ('Ready Mix Concrete Mix',   'Concrete',  40, 'Inactive');

-- ════════════════════════════════════════════════════════════════════════════
--  RAW MATERIALS
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO raw_materials (name, unit) VALUES
  ('Limestone',      'kg'),
  ('Clinker',        'kg'),
  ('Gypsum',         'kg'),
  ('Fly Ash',        'kg'),
  ('Slag',           'kg'),
  ('White Pigment',  'kg'),
  ('Packaging bags', 'pcs');

-- ════════════════════════════════════════════════════════════════════════════
--  INVENTORY — current stock levels (Clinker, Slag, White Pigment seeded
--  BELOW reorder point on purpose, to exercise low-stock / MRP shortage logic)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO inventory (material_name, current_stock, minimum_stock, reorder_point, lead_time_days) VALUES
  ('Limestone',       80000,  10000, 25000, 5),
  ('Clinker',          8000,   5000, 15000, 7),   -- below reorder point
  ('Gypsum',           4000,   1000,  3000, 3),
  ('Fly Ash',         20000,   5000, 10000, 4),
  ('Slag',             6000,   2000,  8000, 6),   -- below reorder point
  ('White Pigment',    1200,    500,  1500, 10),  -- below reorder point
  ('Packaging bags',  30000,   5000, 10000, 2);

-- ════════════════════════════════════════════════════════════════════════════
--  PRODUCT FORMULAS (BOM) — percentages sum to 100 per product
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO product_formulas (product_name, material_name, percentage) VALUES
  ('OPC 53 Grade Cement', 'Clinker',   65.0),
  ('OPC 53 Grade Cement', 'Limestone', 20.0),
  ('OPC 53 Grade Cement', 'Gypsum',     5.0),
  ('OPC 53 Grade Cement', 'Fly Ash',   10.0),

  ('PPC Cement', 'Clinker',   55.0),
  ('PPC Cement', 'Fly Ash',   30.0),
  ('PPC Cement', 'Gypsum',     5.0),
  ('PPC Cement', 'Limestone', 10.0),

  ('OPC 43 Grade Cement', 'Clinker',   60.0),
  ('OPC 43 Grade Cement', 'Limestone', 25.0),
  ('OPC 43 Grade Cement', 'Gypsum',     5.0),
  ('OPC 43 Grade Cement', 'Fly Ash',   10.0),

  ('White Cement', 'Clinker',       70.0),
  ('White Cement', 'White Pigment', 15.0),
  ('White Cement', 'Gypsum',         5.0),
  ('White Cement', 'Limestone',     10.0),

  ('Ready Mix Concrete Mix', 'Clinker',   40.0),
  ('Ready Mix Concrete Mix', 'Slag',      30.0),
  ('Ready Mix Concrete Mix', 'Limestone', 20.0),
  ('Ready Mix Concrete Mix', 'Fly Ash',   10.0);

-- ════════════════════════════════════════════════════════════════════════════
--  FINISHED GOODS — current warehouse stock per product
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO finished_goods (product_name, available_kg, available_bags) VALUES
  ('OPC 53 Grade Cement',     5000,  100),
  ('PPC Cement',              2500,   50),
  ('OPC 43 Grade Cement',     7500,  150),
  ('White Cement',             625,   25),
  ('Ready Mix Concrete Mix',     0,    0);

-- ════════════════════════════════════════════════════════════════════════════
--  SUPPLIERS — several materials have 2 suppliers (tests comparison/selection)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO suppliers (material_name, supplier_name, price, lead_time_days, minimum_order_qty, payment_terms, delivery_cost) VALUES
  ('Limestone', 'Rajasthan Mines Ltd',     2.50, 5, 10000, 'Net 30', 5000),
  ('Limestone', 'Tamil Nadu Quarries Co',  2.30, 6,  8000, 'Net 45', 4500),

  ('Clinker',   'ACC Clinker Depot',       4.80, 7,  5000, 'Net 15', 8000),
  ('Clinker',   'UltraTech Clinker Supply',4.60, 8,  6000, 'Net 30', 7500),

  ('Gypsum',    'Gujarat Minerals Co',     3.20, 3,  2000, 'Net 30', 3000),

  ('Fly Ash',   'NTPC Fly Ash Unit',       0.80, 4,  5000, 'Net 30', 4000),
  ('Fly Ash',   'NLC Fly Ash Supply',      0.75, 5,  4000, 'Net 45', 3500),

  ('Slag',      'JSW Slag Traders',        1.50, 6,  3000, 'Net 30', 4000),

  ('White Pigment', 'Kerala Pigments Pvt Ltd', 45.00, 10, 500, 'Net 45', 6000),

  ('Packaging bags', 'Polyplex Packaging', 12.00, 2,  5000, 'Net 15', 2500);

-- ════════════════════════════════════════════════════════════════════════════
--  CUSTOMER ORDERS — every status represented (tests full order workflow)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO customer_orders (order_no, customer, product, quantity_kg, bag_size_kg, bags, delivery_date, status, notes) VALUES
  ('SO-1001', 'Acme Constructions',     'OPC 53 Grade Cement',    10000, 50, 200, '2026-07-10', 'Pending',       NULL),
  ('SO-1002', 'BuildRight Developers',  'PPC Cement',               5000, 50, 100, '2026-07-05', 'Confirmed',     NULL),
  ('SO-1003', 'Chennai Infra Projects', 'OPC 53 Grade Cement',    20000, 50, 400, '2026-07-15', 'In Production', 'Bulk highway project order'),
  ('SO-1004', 'Kovai Builders',         'OPC 43 Grade Cement',      7500, 50, 150, '2026-06-30', 'Ready',         NULL),
  ('SO-1005', 'South Shore Realty',     'White Cement',              625, 25,  25, '2026-06-20', 'Shipped',       NULL),
  ('SO-1006', 'Madurai Civil Works',    'PPC Cement',               2500, 50,  50, '2026-06-15', 'Closed',        NULL),
  ('SO-1007', 'Acme Constructions',     'OPC 43 Grade Cement',    15000, 50, 300, '2026-07-20', 'Pending',       NULL),
  ('SO-1008', 'BuildRight Developers',  'OPC 53 Grade Cement',      3000, 50,  60, '2026-06-25', 'Cancelled',     'Customer cancelled due to budget revision'),
  ('SO-1009', 'Chennai Infra Projects', 'White Cement',             1250, 25,  50, '2026-07-25', 'Confirmed',     NULL),
  ('SO-1010', 'Kovai Builders',         'PPC Cement',              10000, 50, 200, '2026-08-01', 'Pending',       NULL);

-- ════════════════════════════════════════════════════════════════════════════
--  PRODUCTION SCHEDULES — covers every status + shift type, several linked
--  to the orders above (tests order ↔ schedule linkage)
-- ════════════════════════════════════════════════════════════════════════════
INSERT INTO production_schedules
  (schedule_id, product, planned_qty_kg, start_date, end_date, shift, manpower_available, manpower_required, status, linked_order_no, notes, created_by) VALUES
  ('PS-2001', 'OPC 53 Grade Cement', 10000, '2026-07-01', '2026-07-03', 'Day',      25, 20, 'Planned',     'SO-1001', NULL, 'manager1'),
  ('PS-2002', 'PPC Cement',           5000, '2026-06-28', '2026-06-29', 'Night',    20, 18, 'Confirmed',   'SO-1002', NULL, 'manager1'),
  ('PS-2003', 'OPC 53 Grade Cement', 20000, '2026-06-25', '2026-06-29', 'Full Day', 30, 30, 'In Progress', 'SO-1003', 'Running across two shifts to meet deadline', 'manager1'),
  ('PS-2004', 'OPC 43 Grade Cement',  7500, '2026-06-18', '2026-06-19', 'Day',      22, 20, 'Completed',   'SO-1004', NULL, 'operator1'),
  ('PS-2005', 'White Cement',          625, '2026-06-10', '2026-06-10', 'Day',      10,  8, 'Completed',   'SO-1005', NULL, 'operator1'),
  ('PS-2006', 'PPC Cement',           2500, '2026-06-05', '2026-06-05', 'Night',    15, 12, 'Completed',   'SO-1006', NULL, 'operator1'),
  ('PS-2007', 'OPC 53 Grade Cement',  3000, '2026-06-20', '2026-06-20', 'Day',      12, 10, 'Cancelled',   'SO-1008', 'Cancelled — linked order cancelled by customer', 'manager1');

-- ════════════════════════════════════════════════════════════════════════════
--  Done. Sanity counts:
--    5 users (1 per role) · 6 customers · 5 products (4 active/1 inactive)
--    7 raw materials · 7 inventory rows (3 intentionally below reorder point)
--    20 formula lines · 5 finished-goods rows · 10 supplier rows
--    10 customer orders (every status) · 7 production schedules (every status)
-- ════════════════════════════════════════════════════════════════════════════
