"""Loomi Connect MCP bridge (Bloomreach) — the T6 upgrade.

Concurrency model: FastAPI runs sync endpoints in a worker threadpool, and we
enter the MCP world via asyncio.run() per operation. That means we must NOT
cache sessions across calls (each asyncio.run gets a fresh event loop; a
session bound to an old loop crashes anyio cancel scopes on teardown). So:
connect -> use -> disconnect inside ONE asyncio.run per operation.

Auth: OAuth/SSO via browser (app/mcp_oauth.py), tokens cached on disk (~30
days) — run tests/mcp_check.py once interactively on the demo machine.

Docs pin: mcp>=1.9,<2  (SDK 2.x is NOT certified by Loomi Connect).
"""

import asyncio
from typing import Any

from .config import LOOMI_MCP_URL, MCP_ENABLED


def mcp_available() -> bool:
    # Enabled by config; the connection itself happens per-operation in
    # _run(), and failures are caught by the caller (agent.py).
    return MCP_ENABLED


async def _run(operation) -> Any:
    """Open a fresh MCP session, run `operation(session)`, close cleanly."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    from .mcp_oauth import build_oauth_provider

    async with streamablehttp_client(LOOMI_MCP_URL, auth=build_oauth_provider()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await operation(session)


def list_tools() -> list[dict[str, Any]]:
    """All Loomi tools as Gemini function declarations (name/description/schema)."""

    async def _list(session):
        resp = await session.list_tools()
        return resp.tools

    tools = asyncio.run(_run(_list))
    return [
        {
            "name": f"loomi_{t.name}",
            "description": (t.description or t.name)[:900],
            "parameters": _to_gemini_schema(t.inputSchema),
        }
        for t in tools
    ]


def call_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call a Loomi tool by its ORIGINAL name (no loomi_ prefix)."""

    async def _call(session):
        return await session.call_tool(tool_name, arguments=args)

    result = asyncio.run(_run(_call))

    # Flatten MCP content blocks into a plain JSON-ish structure for Gemini
    out: dict[str, Any] = {"is_error": getattr(result, "isError", False), "content": []}
    for block in getattr(result, "content", []) or []:
        kind = getattr(block, "type", "unknown")
        if kind == "text":
            out["content"].append({"type": "text", "text": getattr(block, "text", "")})
        elif kind == "json":
            out["content"].append({"type": "json", "data": getattr(block, "data", None)})
        else:
            out["content"].append({"type": kind})
    return out


_GEMINI_ALLOWED_KEYS = {"type", "description", "enum", "items", "properties", "required", "format"}


def _sanitize(spec: Any, depth: int = 0) -> Any:
    """Recursively strip JSON-Schema keys Gemini's API rejects (anyOf,
    additionalProperties, $defs, etc.). Best-effort: unrecognized shapes
    degrade to {type: string} with the description preserved."""
    if depth > 6:  # cap recursion on pathological schemas
        return {"type": "string"}
    if isinstance(spec, list):
        return [_sanitize(s, depth + 1) for s in spec]
    if not isinstance(spec, dict):
        return {"type": "string"}

    # Union types don't map cleanly — take the first non-null branch
    if "anyOf" in spec or "oneOf" in spec:
        branches = spec.get("anyOf") or spec.get("oneOf") or []
        non_null = [b for b in branches if isinstance(b, dict) and b.get("type") != "null"]
        merged = _sanitize(non_null[0], depth + 1) if non_null else {"type": "string"}
        if spec.get("description") and isinstance(merged, dict):
            merged["description"] = spec["description"]
        return merged

    out: dict[str, Any] = {}
    stype = spec.get("type", "string")
    if isinstance(stype, list):  # e.g. ["string", "null"]
        stype = next((t for t in stype if t != "null"), "string")
    out["type"] = stype if isinstance(stype, str) else "string"

    if "description" in spec:
        out["description"] = spec["description"]
    if "enum" in spec and isinstance(spec["enum"], list):
        out["enum"] = [str(v) for v in spec["enum"]]
    if "format" in spec and isinstance(spec["format"], str):
        out["format"] = spec["format"]
    if out["type"] == "array" and "items" in spec:
        out["items"] = _sanitize(spec["items"], depth + 1)
    if out["type"] == "object":
        props = {k: _sanitize(v, depth + 1) for k, v in (spec.get("properties") or {}).items()}
        out["properties"] = props
        if spec.get("required"):
            out["required"] = [r for r in spec["required"] if r in props]
    return out


def _to_gemini_schema(mcp_schema: dict[str, Any] | None) -> dict[str, Any]:
    """Adapt a JSON Schema to Gemini's function-declaration subset (recursive)."""
    if not mcp_schema:
        return {"type": "object", "properties": {}}
    return _sanitize(mcp_schema)
