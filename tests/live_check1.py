"""Credential doctor: checks every platform's config and pings the API live.

Run:  python -m tests.live_check

For each platform it reports:
  [OK] LIVE   creds present and a harmless API call succeeded
  [--] SETUP  env vars missing (lists exactly which)
  [XX] ERROR  creds present but the API rejected them (bad key? wrong id?)
"""

import httpx

from app.config import (
    BLOOMREACH_API_KEY,
    BLOOMREACH_BASE_URL,
    BLOOMREACH_CAMPAIGN_ID,
    BLOOMREACH_PROJECT_ID,
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
    GEMINI_API_KEY,
    SHOPIFY_SHOP,
    SHOPIFY_API_KEY,       # Updated parameter
    SHOPIFY_API_SECRET,   # Updated parameter
)

RESULTS: list[tuple[str, str, str]] = []


def _real(value: str) -> bool:
    """True if the env var is set and not the .env.example placeholder."""
    return bool(value) and "your-" not in value


def report(name: str, missing: list[str], ping=None) -> None:
    if missing:
        RESULTS.append((name, "SETUP", "missing: " + ", ".join(missing)))
        return
    try:
        RESULTS.append((name, "LIVE", ping()))
    except Exception as exc:
        RESULTS.append((name, "ERROR", f"{type(exc).__name__}: {str(exc)[:150]}"))


# ------------------------------------------------------------ pings ----

def ping_gemini() -> str:
    from google import genai
    from google.genai import types
    from app.config import GEMINI_MODEL

    client = genai.Client(api_key=GEMINI_API_KEY)
    r = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with the single word: pong",
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCalling(disable=True)
        ),
    )
    return f"{GEMINI_MODEL} replied: {(r.text or '').strip()[:40]!r}"


def ping_databricks() -> str:
    from app.config import DATABRICKS_TABLE

    base = f"{DATABRICKS_HOST}/api/2.0"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
    r = httpx.get(f"{base}/sql/warehouses", headers=headers, timeout=30)
    r.raise_for_status()
    warehouses = {w["id"]: w["state"] for w in r.json().get("warehouses", [])}
    mine = warehouses.get(DATABRICKS_WAREHOUSE_ID, "NOT FOUND")
    detail = f"token OK, {len(warehouses)} warehouse(s) visible; yours is {mine}"
    try:
        from app.databricks_tool import _run_statement

        rows = _run_statement(f"SELECT count(*) AS n FROM {DATABRICKS_TABLE}")
        detail += f"; {DATABRICKS_TABLE} has {rows[0]['n']} rows"
    except Exception as exc:
        detail += f"; [table query failed: {str(exc)[:70]} -- run sql/setup.sql?]"
    return detail


def ping_shopify() -> str:
    # 1. Exchange Client ID & Secret for a short-lived access token
    oauth_url = f"https://{SHOPIFY_SHOP}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
    }
    
    oauth_resp = httpx.post(oauth_url, json=payload, timeout=15)
    oauth_resp.raise_for_status()
    access_token = oauth_resp.json().get("access_token")
    
    if not access_token:
        raise ValueError("OAuth response did not contain an access_token.")

    # 2. Make the GraphQL call with the generated token
    # Overriding the tool execution context safely with the acquired token
    from app.shopify_tool import _gql
    
    # We dynamically pass headers if your custom _gql helper allows it, 
    # otherwise pass the query token inside standard GraphQL requests:
    data = _gql("query { shop { name myshopifyDomain } }", headers={"X-Shopify-Access-Token": access_token})
    s = data["shop"]
    return f"connected to '{s['name']}' ({s['myshopifyDomain']})"


def ping_bloomreach() -> str:
    from app.bloomreach_tool import get_engagement

    get_engagement("credential-doctor@ping.local")
    detail = "token + project valid (events endpoint reachable)"
    if not _real(BLOOMREACH_CAMPAIGN_ID):
        detail += "; [warn] BLOOMREACH_CAMPAIGN_ID not set - trigger_campaign will fail"
    return detail


# ------------------------------------------------------------ main ----

def main() -> None:
    report("Gemini", [] if _real(GEMINI_API_KEY) else ["GEMINI_API_KEY"], ping_gemini)
    report(
        "Databricks",
        [k for k, v in {
            "DATABRICKS_HOST": DATABRICKS_HOST,
            "DATABRICKS_TOKEN": DATABRICKS_TOKEN,
            "DATABRICKS_WAREHOUSE_ID": DATABRICKS_WAREHOUSE_ID,
        }.items() if not _real(v)],
        ping_databricks,
    )
    report(
        "Shopify",
        [k for k, v in {
            "SHOPIFY_SHOP": SHOPIFY_SHOP, 
            "SHOPIFY_API_KEY": SHOPIFY_API_KEY,
            "SHOPIFY_API_SECRET": SHOPIFY_API_SECRET
         }.items() if not _real(v)],
        ping_shopify,
    )
    report(
        "Bloomreach",
        [k for k, v in {
            "BLOOMREACH_PROJECT_ID": BLOOMREACH_PROJECT_ID,
            "BLOOMREACH_API_KEY": BLOOMREACH_API_KEY,
        }.items() if not _real(v)],
        ping_bloomreach,
    )

    icons = {"LIVE": "[OK]", "SETUP": "[--]", "ERROR": "[XX]"}
    print("=" * 64)
    print("THE LOOP - credential doctor")
    print("=" * 64)
    for name, status, detail in RESULTS:
        print(f"{icons[status]} {name:11} {status:5} {detail}")
    print("-" * 64)
    print("Fill missing vars in .env (exact click-paths in CREDENTIALS.md),")
    print("then re-run:  python -m tests.live_check")


if __name__ == "__main__":
    main()
