"""Extended mock data: cross-platform customer signals.

Each row is the SAME customer seen from three vantage points:
- Databricks: aggregates (spend, orders, last order)
- Shopify:    behavior (orders, carts, discount uses)
- Bloomreach: engagement (email opens, clicks, page views)
"""

MOCK_ENGAGEMENT = {
    "maya@example.com": [
        {"ts": "2026-09-20", "type": "email_open",    "campaign": "Fall drop"},
        {"ts": "2026-09-21", "type": "page_view",     "campaign": None},
        {"ts": "2026-09-22", "type": "email_click",   "campaign": "Fall drop"},
    ],
    "liam@example.com": [
        {"ts": "2026-09-18", "type": "email_open",    "campaign": "Fall drop"},
    ],
    "ava@example.com": [
        {"ts": "2026-08-30", "type": "email_open",    "campaign": "Winback July"},
        {"ts": "2026-09-01", "type": "email_click",   "campaign": "Winback July"},
        {"ts": "2026-09-02", "type": "page_view",     "campaign": None},
    ],
    "noah@example.com": [],
    "zoe@example.com": [
        {"ts": "2026-09-05", "type": "email_open",    "campaign": "Newsletter"},
        {"ts": "2026-09-06", "type": "page_view",     "campaign": None},
    ],
    "raj@example.com": [
        {"ts": "2026-09-10", "type": "email_open",    "campaign": "Newsletter"},
    ],
}

MOCK_CARTS = {
    "ava@example.com": [
        {"title": "Merino Wool Hoodie", "qty": 1, "price": "119.00", "added_at": "2026-09-02"},
    ],
    "zoe@example.com": [
        {"title": "Organic Cotton Tee", "qty": 2, "price": "58.00", "added_at": "2026-09-06"},
    ],
}
