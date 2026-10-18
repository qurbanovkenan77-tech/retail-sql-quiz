QUESTIONS = [
    {
        "id": 1,
        "title": "Find expensive products",
        "points": 4,
        "prompt": (
            "Show product_name and price for products costing at least "
            "35. Sort by price from highest to lowest."
        ),
        "hint": "Use WHERE to filter and ORDER BY to sort.",
        "expected_sql": """
SELECT product_name, price
FROM retail.products
WHERE price >= 35
ORDER BY price DESC;
""",
        "expected_result": [
            {"product_name": "Headphones", "price": 80.00},
            {"product_name": "Backpack", "price": 50.00},
            {"product_name": "Desk Lamp", "price": 35.00},
        ],
    },
    {
        "id": 2,
        "title": "Count customers by city",
        "points": 4,
        "prompt": (
            "Show each city and its number of customers as customer_count. "
            "Sort by customer_count descending, then city alphabetically "
            "to break ties."
        ),
        "hint": "Use COUNT(*) with GROUP BY.",
        "expected_sql": """
SELECT city, COUNT(*) AS customer_count
FROM retail.customers
GROUP BY city
ORDER BY customer_count DESC, city ASC;
""",
        "expected_result": [
            {"city": "Durham", "customer_count": 2},
            {"city": "Raleigh", "customer_count": 2},
            {"city": "Cary", "customer_count": 1},
            {"city": "Chapel Hill", "customer_count": 1},
        ],
    },
    {
        "id": 3,
        "title": "Match completed orders to customers",
        "points": 4,
        "prompt": (
            "Show order_id, customer_name, and order_date for completed "
            "orders only. Sort by order_id ascending."
        ),
        "hint": (
            "Join orders to customers using customer_id, "
            "then filter the order status."
        ),
        "expected_sql": """
SELECT o.order_id, c.customer_name, o.order_date
FROM retail.orders AS o
JOIN retail.customers AS c
    ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
ORDER BY o.order_id;
""",
        "expected_result": [
            {
                "order_id": 101,
                "customer_name": "Aylin",
                "order_date": "2026-09-01",
            },
            {
                "order_id": 102,
                "customer_name": "Ben",
                "order_date": "2026-09-02",
            },
            {
                "order_id": 103,
                "customer_name": "Aylin",
                "order_date": "2026-09-05",
            },
            {
                "order_id": 105,
                "customer_name": "Diego",
                "order_date": "2026-09-10",
            },
            {
                "order_id": 106,
                "customer_name": "Ben",
                "order_date": "2026-09-12",
            },
            {
                "order_id": 107,
                "customer_name": "Emma",
                "order_date": "2026-09-15",
            },
            {
                "order_id": 108,
                "customer_name": "Chloe",
                "order_date": "2026-09-18",
            },
        ],
    },
    {
        "id": 4,
        "title": "Find customers with no orders",
        "points": 4,
        "prompt": (
            "Show customer_id and customer_name for customers who have "
            "never placed any order, regardless of status. "
            "Sort by customer_id."
        ),
        "hint": (
            "Use a LEFT JOIN and look for a missing order_id. "
            "A NOT EXISTS query also works."
        ),
        "expected_sql": """
SELECT c.customer_id, c.customer_name
FROM retail.customers AS c
LEFT JOIN retail.orders AS o
    ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;
""",
        "expected_result": [
            {"customer_id": 6, "customer_name": "Farid"},
        ],
    },
    {
        "id": 5,
        "title": "Find high-spending customers",
        "points": 4,
        "prompt": (
            "For completed orders only, find customers whose total "
            "spending exceeds 75. Show customer_id, customer_name, "
            "and total_spent. Calculate spending using quantity "
            "multiplied by unit_price from order_items. "
            "Sort by total_spent descending, then customer_id ascending."
        ),
        "hint": (
            "Join customers, orders, and order_items. "
            "Use SUM and filter grouped totals with HAVING."
        ),
        "expected_sql": """
SELECT
    c.customer_id,
    c.customer_name,
    SUM(oi.quantity * oi.unit_price) AS total_spent
FROM retail.customers AS c
JOIN retail.orders AS o
    ON c.customer_id = o.customer_id
JOIN retail.order_items AS oi
    ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.customer_name
HAVING SUM(oi.quantity * oi.unit_price) > 75
ORDER BY total_spent DESC, c.customer_id ASC;
""",
        "expected_result": [
            {
                "customer_id": 1,
                "customer_name": "Aylin",
                "total_spent": 110.00,
            },
            {
                "customer_id": 2,
                "customer_name": "Ben",
                "total_spent": 101.00,
            },
        ],
    },
]

assert len(QUESTIONS) == 5
assert sum(question["points"] for question in QUESTIONS) == 20