"""
Signal MCP server.

Exposes Signal send/list capabilities as MCP tools so any MCP-compatible
client (Goose Desktop, Claude Desktop, etc.) can interact with Signal.

Auth: X-Gateway-Key header must match the configured gateway secret.
Transport: Streamable HTTP on 127.0.0.1:<mcp_port>

Register in Goose Desktop → Extensions → Add custom extension:
  Type: HTTP
  Endpoint: http://127.0.0.1:7322/mcp
  Request Headers: X-Gateway-Key: <your_gateway_secret>
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

log = logging.getLogger(__name__)


class _AuthASGI:
    """Raw ASGI wrapper that checks X-Gateway-Key on HTTP requests.
    Passes lifespan events through untouched so FastMCP initialises correctly.
    """

    def __init__(self, app, secret: str):
        self._app = app
        self._secret = secret.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            key = headers.get(b"x-gateway-key", b"")
            if self._secret and key != self._secret:
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [[b"content-length", b"12"]],
                })
                await send({"type": "http.response.body", "body": b"Unauthorized"})
                return
        await self._app(scope, receive, send)


def build_mcp_server(
    signal_account: str,
    session_map,
    signal_client,
    secret: str,
    port: int,
) -> FastMCP:
    """
    Build and return a configured FastMCP instance.

    signal_account: the gateway's Signal phone number
    session_map:    SessionMap instance (live, already loaded)
    signal_client:  SignalClient instance (live)
    secret:         gateway secret for X-Gateway-Key auth
    port:           port to listen on
    """

    @asynccontextmanager
    async def _lifespan(server) -> AsyncIterator[dict]:
        yield {}

    mcp = FastMCP("signal-mcp", lifespan=_lifespan, port=port)

    @mcp.tool()
    async def get_signal_identity() -> dict:
        """Return the Signal account number this gateway is running as."""
        return {"account": signal_account}

    @mcp.tool()
    async def list_signal_contacts() -> list[dict]:
        """
        List Signal contacts who have initiated a conversation through this gateway.
        Only contacts with an active session are returned — these are the numbers
        that can be messaged via send_signal_message.
        """
        from .session_map import ConversationKey
        raw = await session_map.all()
        return [
            {
                "phone_number": ConversationKey.from_str(k).identifier,
                "kind": ConversationKey.from_str(k).kind,
                "session_id": v,
            }
            for k, v in raw.items()
        ]

    @mcp.tool()
    async def send_signal_message(phone_number: str, message: str) -> dict:
        """
        Send a Signal message to a contact.

        The contact must have previously initiated a conversation through this
        gateway (i.e. they appear in list_signal_contacts). Messages cannot be
        sent to unknown numbers.
        """
        from .session_map import ConversationKey
        key = ConversationKey(kind="dm", identifier=phone_number)
        session_id = await session_map.get(key)
        if session_id is None:
            return {
                "success": False,
                "error": f"{phone_number} has not initiated a conversation through this gateway",
            }
        try:
            await signal_client.send(phone_number, message)
            log.info("MCP → Signal %s: %r", phone_number, message[:80])
            return {"success": True}
        except Exception as e:
            log.error("MCP send_signal_message failed: %s", e)
            return {"success": False, "error": str(e)}

    # Patch auth middleware onto the ASGI app
    if secret:
        original_app = mcp.streamable_http_app()
        mcp._auth_wrapped = _AuthASGI(original_app, secret)

    return mcp
