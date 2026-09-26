"""Bloomreach layer: trigger an email campaign for a set of customers. Mock + live.

The live call targets Bloomreach Engagement's Campaign API (`/campaign/v2/trigger`).
Verify the exact payload shape against *your* project's API docs — trigger
payloads differ per campaign trigger node configuration.
"""

from typing import Any

import httpx

from . import state
from .config import (
    BLOOMREACH_API_KEY,
    BLOOMREACH_BASE_URL,
    BLOOMREACH_CAMPAIGN_ID,
    BLOOMREACH_PROJECT_ID,
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
        "customer_ids": customer_emails,  # id-type depends on your tracking plan
        "properties": {
            "message": message,
            **({"discount_code": discount_code} if discount_code else {}),
        },
    }
    r = httpx.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Basic {BLOOMREACH_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    r.raise_for_status()
    state.ACTIVATED.update(customer_emails)
    resp = r.json() if r.content else {}
    return {"mode": "live", "campaign_run_id": resp.get("campaign_run_id"), "recipients": customer_emails}

'''
def get_engagement(email: str, event_type: str | None = None) -> list[dict[str, Any]]:
    """Fetch a customer's engagement events (opens, clicks, views) from Engagement.

    Uses the standard `/track/customers/events` report endpoint; adjust the
    id-type (`email`) to match your project's customer identification.
    """
    #url = f"{BLOOMREACH_BASE_URL}/track/v2/customers/events"
    url = f"{BLOOMREACH_BASE_URL}/track/v2/projects/{BLOOMREACH_PROJECT_ID}/customers/events"
    #url = BLOOMREACH_BASE_URL
    params: dict[str, Any] = {"customer_ids": f'{{"email":"{email}"}}'}
    if event_type:
        params["type"] = event_type
    r = httpx.get(
        url,
        params=params,
        headers={"Authorization": f"Basic {BLOOMREACH_API_KEY}"},
        timeout=30,
    )
    r.raise_for_status()
    raw = r.json() if r.content else []
    events = [
        {"ts": e.get("create_time", "")[:10], "type": e.get("event_type"), "campaign": (e.get("properties") or {}).get("campaign_id")}
        for e in raw
    ]
    return events

'''

def get_engagement(email: str, event_type: str | None = None) -> list[dict[str, Any]]:
    """Fetch a customer's engagement events (opens, clicks, views) from Engagement.

    Updated to use POST method and JSON payload body to prevent 405 errors.
    """
    # 1. Correct route URL with the project token path
    url = f"{BLOOMREACH_BASE_URL}/track/v2/projects/{BLOOMREACH_PROJECT_ID}/customers/events"
    
    # 2. Build the POST JSON payload body instead of query params
    payload: dict[str, Any] = {
        "customer_ids": {
            "email": email
        }
    }
    if event_type:
        payload["type"] = event_type

    # 3. Execute using HTTP POST
    """
    r = httpx.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Basic {BLOOMREACH_API_KEY}",
            "Content-Type": "application/json"
        },
        timeout=30,
    )
    """

    # Execute using HTTP POST with managed authentication
    r = httpx.post(
        url,
        json=payload,
        # ✅ FIX: Use the native auth parameter instead of a custom header string
        auth=(BLOOMREACH_API_KEY, ""), 
        headers={
            "Content-Type": "application/json"
        },
        timeout=30,
    )


    r.raise_for_status()
    
    raw = r.json() if r.content else []
    events = [
        {
            "ts": e.get("create_time", "")[:10], 
            "type": e.get("event_type"), 
            "campaign": (e.get("properties") or {}).get("campaign_id")
        }
        for e in raw
    ]
    return events
