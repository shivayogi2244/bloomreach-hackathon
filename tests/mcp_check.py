"""Loomi Connect MCP connection verifier (T6) — now with browser SSO.

Run INTERACTIVELY once:  python -m tests.mcp_check
A browser opens on first connect; sign in with the Bloomreach-enabled account.
Tokens are cached to ~/.loomi_mcp_tokens.json (session persists ~30 days).
"""

import asyncio

from app.config import LOOMI_MCP_URL, MCP_ENABLED
from app.mcp_oauth import build_oauth_provider


async def main() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    print(f"Connecting to {LOOMI_MCP_URL} ...")
    provider = build_oauth_provider()
    async with streamablehttp_client(LOOMI_MCP_URL, auth=provider) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[OK] initialized (browser SSO completed, tokens cached)")

            resp = await session.list_tools()
            names = sorted(t.name for t in resp.tools)
            print(f"[OK] {len(names)} tools available")
            print("Sample:", ", ".join(names[:12]), "..." if len(names) > 12 else "")

            # Prefer a read tool that needs no required args (or fill a probe value)
            victim, args = None, {}
            tools_by_name = {t.name: t for t in resp.tools}
            for n in names:
                t = tools_by_name[n]
                schema = t.inputSchema or {}
                required = schema.get("required", []) or []
                if any(k in n.lower() for k in ("list_projects", "get_campaign_calendar", "get_cloud_organization_details")):
                    victim, args = n, {}
                    break
                if not required and any(k in n.lower() for k in ("search_segmentations", "search_email_campaigns", "list", "search")):
                    victim, args = n, {}
                    break
                if any(k in n.lower() for k in ("search", "list")) and required == ["q"]:
                    victim, args = n, {"q": "campaign"}
                    break
            if victim:
                print(f"[..] calling harmless tool: {victim} with {args}")
                try:
                    result = await session.call_tool(victim, arguments=args)
                    text = "".join(getattr(b, "text", "") for b in (result.content or []))
                    err = getattr(result, "isError", False)
                    print(f"[{'XX' if err else 'OK'}] {victim} -> {text[:250]!r}")
                    if err and "not enabled" in text.lower():
                        print("     (org lacks the Loomi flag — this login won't work for the demo)")
                except Exception as exc:
                    print(f"[XX] {victim} failed: {str(exc)[:200]}")
            print("\nNext: set MCP_ENABLED=true in .env and restart the server.")


if __name__ == "__main__":
    if not MCP_ENABLED:
        print("NOTE: MCP_ENABLED=false in .env — standalone check only until you flip it.\n")
    asyncio.run(main())
