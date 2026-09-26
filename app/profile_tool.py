"""Unified customer profile: stitch the three vantage points into one view.

This is the connective tissue the hackathon thesis asks for — the agent can
answer "who is this customer really?" and act on the conclusion.
"""

from typing import Any

from . import bloomreach_tool, databricks_tool, shopify_tool
from .mock_data import MOCK_CUSTOMERS
from .mock_signals import MOCK_CARTS, MOCK_ENGAGEMENT


def _signal_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    opens = sum(1 for e in events if e["type"] == "email_open")
    clicks = sum(1 for e in events if e["type"] == "email_click")
    views = sum(1 for e in events if e["type"] == "page_view")
    last = max((e["ts"] for e in events), default=None)
    return {"email_opens": opens, "email_clicks": clicks, "page_views": views, "last_event": last}


def _cart_value(cart: list[dict[str, Any]]) -> float:
    return sum(float(item["price"]) for item in cart)


def _recommendation(row: dict[str, Any], engagement: dict[str, Any], cart: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules-of-thumb the agent can override with its own reasoning."""
    segment = row.get("segment", "")
    recency_days = row.get("recency_days")

    # Churned by recency BUT still engaging → nudge, don't discount
    if segment == "churn_risk" and (engagement["email_opens"] or engagement["email_clicks"]):
        return {
            "action": "nudge_not_discount",
            "why": "churned by recency but still opening/clicking emails — attention is warm, margin is precious",
            "channel": "email (personal nudge, no discount)",
        }
    if segment == "churn_risk":
        return {
            "action": "winback_discount",
            "why": "churned and cold — no engagement signals in 60+ days",
            "channel": "email + discount",
        }
    if segment == "vip":
        return {
            "action": "early_access",
            "why": "high spend, recent orders — reward with access, not discounts",
            "channel": "email (VIP early access)",
        }
    if segment == "new":
        return {
            "action": "second_purchase",
            "why": "one or two orders — the second purchase is the habit moment",
            "channel": "email (product recommendations)",
        }
    # active
    if cart:
        return {
            "action": "cart_recovery",
            "why": "active customer with items sitting in cart",
            "channel": "email (cart reminder)",
        }
    return {"action": "nurture", "why": "steady, no urgency signal", "channel": "newsletter"}


def resolve_customer(email: str) -> dict[str, Any]:
    """One customer, three vantage points, one verdict.

    Combines:
      - Databricks: aggregates + segment
      - Shopify:    order behavior + open cart
      - Bloomreach: engagement signals
    """
    # 1. Databricks vantage point
    intel = databricks_tool.query_customers(limit=100)
    row = next((r for r in intel["rows"] if r["email"] == email), None)
    if not row:
        return {"error": f"customer not found in warehouse: {email}"}

    # 2. Shopify vantage point
    orders = shopify_tool.list_orders(email=email, limit=10)["orders"]
    cart = MOCK_CARTS.get(email, []) if intel["mode"] == "mock" else []

    # 3. Bloomreach vantage point
    if intel["mode"] == "mock":
        events = MOCK_ENGAGEMENT.get(email, [])
    else:
        events = bloomreach_tool.get_engagement(email)

    engagement = _signal_summary(events)

    return {
        "mode": intel["mode"],
        "identity": {
            "email": email,
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
        },
        "vantage_points": {
            "databricks": {k: row.get(k) for k in ("segment", "total_spent", "order_count", "last_order_at")},
            "shopify": {"orders": orders, "open_cart": cart},
            "bloomreach": {"signals": _signal_summary(events), "recent_events": events[-3:]},
        },
        "recommendation": _recommendation(row, engagement, cart),
    }
