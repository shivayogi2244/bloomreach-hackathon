"""Browser-based OAuth for the Loomi Connect MCP client (mirrors VS Code).

Flow: 401 -> SDK discovers auth-server metadata -> dynamic client registration
-> redirect_handler opens the browser for SSO -> callback_handler captures the
?code= on a localhost port -> token exchange -> tokens cached to disk
(~30-day session survives restarts).

Demo machine ritual: run `python -m tests.mcp_check` once, sign in with the
Bloomreach-enabled Google account, done.
"""

import json
import os
import threading
import time
import webbrowser
from collections.abc import Awaitable, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientMetadata

TOKEN_CACHE = os.path.join(os.path.expanduser("~"), ".loomi_mcp_tokens.json")
CALLBACK_PORT = 19771  # arbitrary localhost port for the OAuth redirect
CALLBACK_URI = f"http://localhost:{CALLBACK_PORT}/callback"


class _DiskTokenStorage(TokenStorage):
    """Persist tokens + client info so SSO survives process restarts."""

    def __init__(self) -> None:
        self._data: dict = {}
        if os.path.exists(TOKEN_CACHE):
            try:
                with open(TOKEN_CACHE, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except Exception:
                self._data = {}

    def _flush(self) -> None:
        with open(TOKEN_CACHE, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh)

    async def get_tokens(self):
        raw = self._data.get("tokens")
        from mcp.shared.auth import OAuthToken

        return OAuthToken(**raw) if raw else None

    async def set_tokens(self, tokens) -> None:
        self._data["tokens"] = tokens.model_dump(mode="json")
        self._flush()

    async def get_client_info(self):
        raw = self._data.get("client_info")
        from mcp.shared.auth import OAuthClientInformationFull

        return OAuthClientInformationFull(**raw) if raw else None

    async def set_client_info(self, info) -> None:
        self._data["client_info"] = info.model_dump(mode="json")
        self._flush()


class _CallbackWaiter:
    """Tiny localhost HTTP server capturing the OAuth ?code= redirect."""

    def __init__(self) -> None:
        self.authorization_code: str | None = None
        self.state: str | None = None
        self._done = threading.Event()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                qs = parse_qs(urlparse(self.path).query)
                if "code" in qs:
                    outer.authorization_code = qs["code"][0]
                    outer.state = qs.get("state", [None])[0]
                    outer._done.set()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(
                        b"<h2>Login complete.</h2>Close this tab and return to the terminal."
                    )
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing ?code= in callback.")

            def log_message(self, *args):
                pass

        self._server = HTTPServer(("localhost", CALLBACK_PORT), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def wait(self, timeout: float = 300.0) -> tuple[str | None, str | None]:
        self._done.wait(timeout)
        self._server.shutdown()
        return self.authorization_code, self.state


def make_redirect_handler() -> Callable[[str], Awaitable[None]]:
    """Open the browser for the SSO login page."""

    async def redirect_handler(authorization_url: str) -> None:
        print("\n[SSO] Opening browser for Bloomreach login...")
        print(f"[SSO] {authorization_url}")
        webbrowser.open(authorization_url)

    return redirect_handler


def make_callback_handler() -> Callable[[], Awaitable[tuple[str, str | None]]]:
    """Block until the browser redirect delivers ?code=...&state=..."""

    async def callback_handler() -> tuple[str, str | None]:
        waiter = _CallbackWaiter()
        print(f"[SSO] Waiting for callback on localhost:{CALLBACK_PORT} ...")
        code, state = waiter.wait()
        if not code:
            raise RuntimeError("No OAuth callback within timeout — re-run mcp_check and complete the login.")
        print("[SSO] Login captured.")
        return code, state

    return callback_handler


def build_oauth_provider() -> OAuthClientProvider:
    return OAuthClientProvider(
        server_url="https://brx.connect.loomi.ai/mcp",
        client_metadata=OAuthClientMetadata(
            client_name="the-loop-copilot",
            redirect_uris=[CALLBACK_URI],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        ),
        storage=_DiskTokenStorage(),
        redirect_handler=make_redirect_handler(),
        callback_handler=make_callback_handler(),
    )


def cached_token_present() -> bool:
    if not os.path.exists(TOKEN_CACHE):
        return False
    try:
        with open(TOKEN_CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
        return bool(data.get("tokens", {}).get("access_token"))
    except Exception:
        return False
