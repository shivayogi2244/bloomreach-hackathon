"""Bloomreach layer: trigger an email campaign for a set of customers. Mock + live.

The live call targets Bloomreach Engagement's Campaign API (`/campaign/v2/trigger`).
"""

from typing import Any
import httpx
from . import state
from .config import (
    BLOOMREACH_BASE_URL,
    BLOOMREACH_CAMPAIGN_ID,
    BLOOMREACH_PROJECT_ID,
    BLOOMREACH_CUSTOMER_ID_TYPE,
    BLOOMREACH_API_KEY_ID,
    BLOOMREACH_API_SECRET,
    mock_for,
)


def trigger_campaign(
    customer_emails: list[str],
    message: str,
    discount_code: str | None = None,
) -> dict[str, Any]:
    """Trigger the campaign for the given customers with a personalized message."""
    if not customer_emails:
        raise ValueError("customer_emails is empty — query a segment first")

    if mock_for("BLOOMREACH"):
        campaign_id = state.next_campaign_id()
        state.ACTIVATED.update(customer_emails)
        return {
            "mode": "mock",
            "campaign_run_id": campaign_id,
            "recipients": customer_emails,
            "message": message,
            "discount_code": discount_code,
            "status": "sent (mock — no real emails)",
        }

    url = f"{BLOOMREACH_BASE_URL}/campaign/v2/trigger"
    payload: dict[str, Any] = {
        "project_id": BLOOMREACH_PROJECT_ID,
        "campaign_id": BLOOMREACH_CAMPAIGN_ID,
        "customer_ids": customer_emails,
        "properties": {
            "message": message,
            **({"discount_code": discount_code} if discount_code else {}),
        },
    }
    r = httpx.post(
        url,
        json=payload,
        auth=(BLOOMREACH_API_KEY_ID, BLOOMREACH_API_SECRET),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    state.ACTIVATED.update(customer_emails)
    resp = r.json() if r.content else {}
    return {"mode": "live", "campaign_run_id": resp.get("campaign_run_id"), "recipients": customer_emails}


def get_engagement(email: str, event_type: str | None = None) -> list[dict[str, Any]]:
    """Fetch a customer's engagement events using the Customer Data Export API."""
    url = f"{BLOOMREACH_BASE_URL}/data/v2/projects/{BLOOMREACH_PROJECT_ID}/customers/events"
    
    # Updated payload schema incorporating the mandatory event_types parameter
    payload: dict[str, Any] = {
        "customer_ids": {
            #"registered": email
            BLOOMREACH_CUSTOMER_ID_TYPE: email
        },
        "event_types": [event_type] if event_type else ["session", "campaign"],
        "limit": 50,
        "order": "desc"
    }

    try:
        r = httpx.post(
            url,
            json=payload,
            auth=(BLOOMREACH_API_KEY_ID, BLOOMREACH_API_SECRET),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
            
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        try:
            error_details = exc.response.json()
            message = error_details.get("message", error_details.get("errors", str(exc.response.content)))
        except Exception:
            message = exc.response.text or "No error message provided."

        if status_code == 401:
            raise RuntimeError(f"🛑 [Bloomreach 401]: Auth failed. Details: {message}") from exc
        elif status_code == 403:
            raise RuntimeError(f"🛑 [Bloomreach 403]: Missing event permissions in API Group. Details: {message}") from exc
        elif status_code == 404:
            raise RuntimeError(f"🛑 [Bloomreach 404]: Token path not found. Details: {message}") from exc
        elif status_code == 400:
            raise RuntimeError(f"🛑 [Bloomreach 400 Bad Request]: Schema rejected. Details: {message}") from exc
        else:
            raise RuntimeError(f"🛑 [Bloomreach HTTP {status_code}]: Server error. Details: {message}") from exc

    raw = r.json() if r.content else {}
    events_data = raw.get("data", []) if isinstance(raw, dict) else raw
    events = [
        {
            "ts": e.get("create_time", "")[:10],
            "type": e.get("event_type"),
            "campaign": (e.get("properties") or {}).get("campaign_id")
        }
        for e in events_data
    ]
    return events


# app/bloomreach_tool.py — add this function

def sync_customer_from_shopify(shopify_customer: dict[str, Any]) -> dict[str, Any]:
    """Upsert a single Shopify customer into Bloomreach, keyed by email_id + shopify_id."""
    email = shopify_customer.get("email")
    if not email:
        raise ValueError("Shopify customer has no email — cannot key by email_id")

    url = f"{BLOOMREACH_BASE_URL}/track/v2/projects/{BLOOMREACH_PROJECT_ID}/customers"
    payload: dict[str, Any] = {
        "customer_ids": {
            "email_id": email,
            "shopify_id": str(shopify_customer.get("id", "")).split("/")[-1],  # numeric part of gid
        },
        "properties": {
            "first_name": shopify_customer.get("firstName", ""),
            "last_name": shopify_customer.get("lastName", ""),
            "email": email,
            "phone": shopify_customer.get("phone", ""),
        },
    }
    r = httpx.post(
        url,
        json=payload,
        auth=(BLOOMREACH_API_KEY_ID, BLOOMREACH_API_SECRET),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return {"email": email, "status": "synced"}


def sync_customers_bulk(shopify_customers: list[dict[str, Any]]) -> dict[str, Any]:
    """Sync a batch of Shopify customers into Bloomreach one at a time."""
    results = []
    for c in shopify_customers:
        try:
            results.append(sync_customer_from_shopify(c))
        except Exception as exc:
            results.append({"email": c.get("email"), "status": "error", "detail": str(exc)[:150]})
    return {
        "total": len(shopify_customers),
        "synced": sum(1 for r in results if r["status"] == "synced"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "details": results,
    }