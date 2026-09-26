"""Databricks layer: run SQL, list segments. Mock + live."""

from typing import Any

import httpx

from .config import (
    DATABRICKS_HOST,
    DATABRICKS_TABLE,
    DATABRICKS_TOKEN,
    DATABRICKS_WAREHOUSE_ID,
    mock_for,
)
from .mock_data import MOCK_CUSTOMERS

# Whitelisted patterns: the agent can't run arbitrary DDL/DML through this tool.
_ALLOWED_SQL = ("select", "with")

SEGMENT_HELP = (
    f"Segments live in {DATABRICKS_TABLE} with columns: email, first_name, "
    "last_name, total_spent, order_count, last_order_at, segment "
    "('vip' | 'churn_risk' | 'new' | 'active')."
)


def _run_statement(sql: str) -> list[dict[str, Any]]:
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {DATABRICKS_TOKEN}"},
        json={
            "warehouse_id": DATABRICKS_WAREHOUSE_ID,
            "statement": sql,
            "wait_timeout": "30s",
            "format": "JSON_ARRAY",
        },
        timeout=60,
    )
    r.raise_for_status()
    result = r.json()
    if result.get("status", {}).get("state") == "FAILED":
        raise RuntimeError(f"Databricks error: {result['status'].get('error')}")
    cols = [c["name"] for c in result["manifest"]["schema"]["columns"]]
    rows = result["result"]["data_array"] if result.get("result") else []
    return [dict(zip(cols, row)) for row in rows]


def _mock_segment(segment: str | None, limit: int) -> list[dict[str, Any]]:
    rows = MOCK_CUSTOMERS
    if segment:
        rows = [c for c in rows if c["segment"] == segment]
    return rows[:limit]


def query_customers(segment: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Return customers, optionally filtered by segment (vip/churn_risk/new/active)."""
    if mock_for("DATABRICKS"):
        return {"mode": "mock", "rows": _mock_segment(segment, limit)}

    where = f"WHERE segment = '{segment}'" if segment else ""
    sql = f"SELECT * FROM {DATABRICKS_TABLE} {where} ORDER BY total_spent DESC LIMIT {int(limit)}"
    return {"mode": "live", "rows": _run_statement(sql)}


def run_readonly_sql(sql: str) -> dict[str, Any]:
    """Run a read-only SELECT/WITH query against the warehouse."""
    cleaned = sql.strip().rstrip(";").lower()
    if not cleaned.startswith(_ALLOWED_SQL):
        raise ValueError("Only SELECT/WITH queries are allowed. " + SEGMENT_HELP)

    if mock_for("DATABRICKS"):
        # Best-effort mock: serve segment rows if the query mentions them.
        if "loop_segments" in cleaned or "loop_customers" in cleaned:
            seg = None
            for name in ("vip", "churn_risk", "new", "active"):
                if f"'{name}'" in cleaned:
                    seg = name
                    break
            return {"mode": "mock", "rows": _mock_segment(seg, 20)}
        return {"mode": "mock", "rows": [], "note": "mock mode returns segment data only"}

    return {"mode": "live", "rows": _run_statement(sql)}
