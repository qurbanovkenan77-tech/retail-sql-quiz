BEGIN;

-- Keep quiz data in its own schema.
CREATE SCHEMA IF NOT EXISTS retail;

-- Access will be granted explicitly when we create the app roles.
REVOKE ALL ON SCHEMA retail FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS retail.customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retail.products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price > 0)
);

CREATE TABLE IF NOT EXISTS retail.orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL
        REFERENCES retail.customers(customer_id),
    order_date DATE NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('completed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS retail.order_items (
    order_id INTEGER NOT NULL
        REFERENCES retail.orders(order_id),
    product_id INTEGER NOT NULL
        REFERENCES retail.products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, product_id)
);

INSERT INTO retail.customers
    (customer_id, customer_name, city)
VALUES
    (1, 'Aylin', 'Durham'),
    (2, 'Ben', 'Raleigh'),
    (3, 'Chloe', 'Durham'),
    (4, 'Diego', 'Cary'),
    (5, 'Emma', 'Raleigh'),
    (6, 'Farid', 'Chapel Hill')
ON CONFLICT DO NOTHING;

INSERT INTO retail.products
    (product_id, product_name, category, price)
VALUES
    (1, 'Notebook', 'Stationery', 5.00),
    (2, 'Pen Set', 'Stationery', 8.00),
    (3, 'Water Bottle', 'Accessories', 20.00),
    (4, 'Backpack', 'Accessories', 50.00),
    (5, 'Desk Lamp', 'Electronics', 35.00),
    (6, 'Headphones', 'Electronics', 80.00)
ON CONFLICT DO NOTHING;

INSERT INTO retail.orders
    (order_id, customer_id, order_date, status)
VALUES
    (101, 1, '2026-09-01', 'completed'),
    (102, 2, '2026-09-02', 'completed'),
    (103, 1, '2026-09-05', 'completed'),
    (104, 3, '2026-09-06', 'cancelled'),
    (105, 4, '2026-09-10', 'completed'),
    (106, 2, '2026-09-12', 'completed'),
    (107, 5, '2026-09-15', 'completed'),
    (108, 3, '2026-09-18', 'completed')
ON CONFLICT DO NOTHING;

INSERT INTO retail.order_items
    (order_id, product_id, quantity, unit_price)
VALUES
    (101, 1, 2, 5.00),
    (101, 3, 1, 20.00),
    (102, 4, 1, 50.00),
    (102, 2, 2, 8.00),
    (103, 6, 1, 80.00),
    (104, 5, 1, 35.00),
    (105, 3, 2, 20.00),
    (105, 1, 3, 5.00),
    (106, 5, 1, 35.00),
    (107, 4, 1, 50.00),
    (107, 3, 1, 20.00),
    (108, 2, 1, 8.00)
ON CONFLICT DO NOTHING;

-- Remove any automatic grants to the API roles.
REVOKE ALL ON ALL TABLES IN SCHEMA retail
FROM PUBLIC, anon, authenticated;

COMMIT;

-- Verify that the dataset was inserted.
SELECT 'customers' AS table_name, COUNT(*) AS row_count
FROM retail.customers
UNION ALL
SELECT 'products', COUNT(*) FROM retail.products
UNION ALL
SELECT 'orders', COUNT(*) FROM retail.orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM retail.order_items
ORDER BY table_name;