"""Smoke test: runs every tool in mock mode and verifies the loop end-to-end.

Run:  python -m tests.smoke
"""

import json


def main() -> None:
    from app import bloomreach_tool, databricks_tool, shopify_tool

    # 1. Intelligence: segment query
    vip = databricks_tool.query_customers(segment="vip")
    assert vip["rows"], "expected vip customers"
    print(f"[databricks]  {len(vip['rows'])} VIP customers: {[r['email'] for r in vip['rows']]}")  # noqa: RUF001

    # 2. SQL tool (whitelisted)
    churn = databricks_tool.run_readonly_sql(
        "SELECT * FROM catalog.schema.loop_segments WHERE segment = 'churn_risk'")
    assert churn["rows"], "expected churn_risk customers"

    # SQL injection guard
    try:
        databricks_tool.run_readonly_sql("DROP TABLE catalog.schema.loop_segments")
        raise AssertionError("DDL should have been rejected")
    except ValueError:
        print("[databricks]  DDL correctly rejected")

    # 3. Commerce
    orders = shopify_tool.list_orders(email="ava@example.com")
    assert orders["orders"], "expected orders for ava"
    products = shopify_tool.list_products()
    assert products["products"], "expected products"

    emails = [r["email"] for r in churn["rows"]]
    discount = shopify_tool.create_discount(percent=15, segment="churn_risk", customer_emails=emails)
    print(f"[shopify]     discount {discount['code']} ({discount['percent']}%) for {len(emails)} customers")

    # 4. Activation
    campaign = bloomreach_tool.trigger_campaign(
        customer_emails=emails,
        message="We miss you! Here's 15% off your next order.",
        discount_code=discount["code"],
    )
    print(f"[bloomreach]  campaign #{campaign['campaign_run_id']} -> {len(campaign['recipients'])} recipients")

    # 5. Unified profile: one customer, three vantage points
    from app.profile_tool import resolve_customer

    ava = resolve_customer("ava@example.com")
    assert "error" not in ava, f"profile failed: {ava}"
    vp = ava["vantage_points"]
    assert vp["databricks"]["segment"] == "churn_risk"
    assert vp["shopify"]["open_cart"], "ava should have an open cart"
    assert vp["bloomreach"]["signals"]["email_clicks"] >= 1, "ava clicked the winback"
    rec = ava["recommendation"]
    assert rec["action"] == "nudge_not_discount", (
        f"ava is engaged-churn: expected nudge_not_discount, got {rec['action']}"
    )
    print(f"[profile]     ava unified: churn_risk + {vp['bloomreach']['signals']['email_clicks']} clicks + cart -> {rec['action']}")

    maya = resolve_customer("maya@example.com")
    assert maya["recommendation"]["action"] == "early_access"
    print(f"[profile]     maya unified: vip -> {maya['recommendation']['action']}")

    print("\n[OK] Full loop OK (mock mode):", json.dumps(
        {"segment": "churn_risk", "audience": emails, "discount": discount["code"]}, indent=2))


if __name__ == "__main__":
    main()
