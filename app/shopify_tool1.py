"""Shopify layer: order history, catalog, discount creation. Mock + live."""

import time
from typing import Any

import httpx

from . import state
from .config import (
    SHOPIFY_API_VERSION,
    SHOPIFY_SHOP,
    SHOPIFY_TOKEN,
    mock_for,
)
from .mock_data import MOCK_ORDERS, MOCK_PRODUCTS


def _gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    r = httpx.post(
        url,
        json={"query": query, "variables": variables or {}},
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(f"Shopify GraphQL error: {data['errors']}")
    return data["data"]


# ---------------------------------------------------------------- mocks ----

def _mock_list_orders(limit: int, email: str | None) -> list[dict]:
    orders = MOCK_ORDERS
    if email:
        orders = [o for o in orders if o["email"] == email]
    return orders[:limit]


def _mock_create_discount(percent: int, segment: str, customer_emails: list[str]) -> dict:
    code = f"LOOP{segment.upper()}{int(time.time()) % 10000}"
    info = {
        "code": code,
        "percent": percent,
        "segment": segment,
        "audience": customer_emails,
        "created_at": state.now_iso(),
    }
    state.DISCOUNTS[code] = info
    return info


# ---------------------------------------------------------------- public API ----

def list_orders(limit: int = 20, email: str | None = None) -> dict[str, Any]:
    """Recent orders, optionally filtered to one customer."""
    if mock_for("SHOPIFY"):
        return {"mode": "mock", "orders": _mock_list_orders(limit, email)}

    q = """
    query orders($first: Int!, $query: String) {
      orders(first: $first, query: $query, reverse: true) {
        nodes {
          id email createdAt totalPriceSet { shopMoney { amount } }
          lineItems(first: 10) { nodes { title quantity } }
        }
      }
    }"""
    query_str = f"email:{email}" if email else None
    data = _gql(q, {"first": limit, "query": query_str})
    orders = [
        {
            "id": o["id"],
            "email": o["email"],
            "total": o["totalPriceSet"]["shopMoney"]["amount"],
            "created_at": o["createdAt"][:10],
            "items": [f"{li['title']} x{li['quantity']}" for li in o["lineItems"]["nodes"]],
        }
        for o in data["orders"]["nodes"]
    ]
    return {"mode": "live", "orders": orders}


def list_products(limit: int = 10) -> dict[str, Any]:
    if mock_for("SHOPIFY"):
        return {"mode": "mock", "products": MOCK_PRODUCTS[:limit]}

    q = """
    query products($first: Int!) {
      products(first: $first) {
        nodes { id title priceRangeV2 { minVariantPrice { amount } } }
      }
    }"""
    data = _gql(q, {"first": limit})
    products = [
        {
            "id": p["id"],
            "title": p["title"],
            "price": p["priceRangeV2"]["minVariantPrice"]["amount"],
        }
        for p in data["products"]["nodes"]
    ]
    return {"mode": "live", "products": products}


def create_discount(percent: int, segment: str, customer_emails: list[str]) -> dict[str, Any]:
    """Create a percent-off basic discount code for the given audience."""
    if mock_for("SHOPIFY"):
        return {"mode": "mock", **_mock_create_discount(percent, segment, customer_emails)}

    code = f"LOOP{segment.upper()}{int(time.time()) % 10000}"
    starts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    q = """
    mutation discount($basicCodeDiscount: DiscountBasicCodeInput!) {
      discountBasicCodeCreate(basicCodeDiscount: $basicCodeDiscount) {
        codeDiscountNode { id codeDiscount { codes(first: 1) { nodes { code } } } }
        userErrors { field message }
      }
    }"""
    variable_values = {
        "basicCodeDiscount": {
            "title": f"Loop win-back {segment} {percent}%",
            "code": code,
            "startsAt": starts,
            "customerGets": {
                "value": {"percentage": percent / 100.0},
                "items": {"all": True},
            },
            "customerSelection": {
                "customers": {"first": 100}
            },
            "appliesOncePerCustomer": True,
        }
    }
    data = _gql(q, variable_values)
    errs = data["discountBasicCodeCreate"].get("userErrors")
    if errs:
        raise RuntimeError(f"Shopify discount error: {errs}")
    info = {
        "code": code,
        "percent": percent,
        "segment": segment,
        "audience": customer_emails,
        "created_at": starts,
        "note": "created for first 100 customers — refine customerSelection for large audiences",
    }
    state.DISCOUNTS[code] = info
    return {"mode": "live", **info}
