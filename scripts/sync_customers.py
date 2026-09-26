"""Sync Shopify customers into Bloomreach.

Run:  python -m scripts.sync_customers
"""

from app.bloomreach_tool import sync_customers_bulk
from app.shopify_tool import fetch_shopify_customers


def main() -> None:
    print("Fetching customers from Shopify...")
    customers = fetch_shopify_customers()
    print(f"Found {len(customers)} customer(s). Syncing to Bloomreach...")

    result = sync_customers_bulk(customers)

    print("=" * 64)
    print(f"Total:  {result['total']}")
    print(f"Synced: {result['synced']}")
    print(f"Failed: {result['failed']}")
    print("=" * 64)

    if result["failed"]:
        print("Failures:")
        for detail in result["details"]:
            if detail["status"] == "error":
                print(f"  - {detail['email']}: {detail['detail']}")


if __name__ == "__main__":
    main()