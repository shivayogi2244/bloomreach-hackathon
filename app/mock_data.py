"""Seed data used when a service runs in mock mode. Mirrors sql/setup.sql."""

MOCK_CUSTOMERS = [
    {"email": "maya@example.com", "first_name": "Maya", "last_name": "Patel",
     "total_spent": 2480.0, "order_count": 9, "last_order_at": "2026-09-01", "segment": "vip"},
    {"email": "liam@example.com", "first_name": "Liam", "last_name": "Chen",
     "total_spent": 1890.0, "order_count": 7, "last_order_at": "2026-08-12", "segment": "vip"},
    {"email": "ava@example.com", "first_name": "Ava", "last_name": "Nolan",
     "total_spent": 1520.0, "order_count": 6, "last_order_at": "2026-05-30", "segment": "churn_risk"},
    {"email": "noah@example.com", "first_name": "Noah", "last_name": "Reid",
     "total_spent": 1100.0, "order_count": 4, "last_order_at": "2026-03-14", "segment": "churn_risk"},
    {"email": "zoe@example.com", "first_name": "Zoe", "last_name": "Marsh",
     "total_spent": 980.0, "order_count": 5, "last_order_at": "2026-04-02", "segment": "churn_risk"},
    {"email": "raj@example.com", "first_name": "Raj", "last_name": "Iyer",
     "total_spent": 640.0, "order_count": 3, "last_order_at": "2026-06-21", "segment": "new"},
]

MOCK_PRODUCTS = [
    {"id": "gid://shopify/Product/1", "title": "Organic Cotton Tee", "price": "29.00"},
    {"id": "gid://shopify/Product/2", "title": "Merino Wool Hoodie", "price": "119.00"},
    {"id": "gid://shopify/Product/3", "title": "Recycled Trail Jacket", "price": "189.00"},
]

MOCK_ORDERS = [
    {"id": "gid://shopify/Order/1001", "email": "maya@example.com", "total": "189.00",
     "created_at": "2026-09-01", "items": ["Recycled Trail Jacket"]},
    {"id": "gid://shopify/Order/1002", "email": "liam@example.com", "total": "119.00",
     "created_at": "2026-08-12", "items": ["Merino Wool Hoodie"]},
    {"id": "gid://shopify/Order/1003", "email": "ava@example.com", "total": "148.00",
     "created_at": "2026-05-30", "items": ["Merino Wool Hoodie", "Organic Cotton Tee"]},
    {"id": "gid://shopify/Order/1004", "email": "noah@example.com", "total": "29.00",
     "created_at": "2026-03-14", "items": ["Organic Cotton Tee"]},
]
