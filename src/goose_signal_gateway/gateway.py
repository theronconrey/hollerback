"""
Main gateway loop.

Signal SSE stream → goosed session → SSE reply → Signal send.
"""

import asyncio
import logging

from .goosed_client import GoosedClient, discover_goosed
from .session_store import SessionStore
from .signal_client import IncomingMessage, SignalClient

log = logging.getLogger(__name__)


class Gateway:
    def __init__(self, signal_account: str):
        self._signal_account = signal_account
        self._sessions = SessionStore()
        self._goosed: GoosedClient | None = None
        self._signal: SignalClient | None = None

    async def start(self):
        config = discover_goosed()
        log.info("Found goosed at port %d", config.port)

        self._goosed = GoosedClient(config)
        self._signal = SignalClient(self._signal_account)

        if not await self._goosed.status():
            raise RuntimeError("goosed health check failed")
        log.info("goosed healthy")

        await self._run_loop()

    async def _run_loop(self):
        log.info("Gateway running. Subscribed to Signal SSE stream.")
        while True:
            try:
                async for msg in self._signal.subscribe():
                    asyncio.create_task(self._handle(msg))
            except Exception as e:
                log.warning("SSE stream error: %s — reconnecting in 5s", e)
                await asyncio.sleep(5)

    async def _handle(self, msg: IncomingMessage):
        sender = msg.sender
        text = msg.text.strip()
        log.info("Signal ← %s: %r", sender, text[:80])

        session_id = self._sessions.get(sender)
        if session_id is None:
            session_id = await self._goosed.create_session()
            self._sessions.set(sender, session_id)
            log.info("Created session %s for %s", session_id, sender)

        text_by_id: dict[str, list[str]] = {}
        msg_order: list[str] = []
        async for event in self._goosed.reply(session_id, text):
            if event["type"] == "Message":
                goose_msg = event["message"]
                mid = goose_msg["id"]
                if mid not in text_by_id:
                    text_by_id[mid] = []
                    msg_order.append(mid)
                for part in goose_msg.get("content", []):
                    if part.get("type") == "text":
                        text_by_id[mid].append(part["text"])
            elif event["type"] == "Error":
                log.error("goosed error for session %s: %s", session_id, event)
                await self._signal.send(sender, "(Goose error — please try again)")
                return
            elif event["type"] == "Finish":
                break

        reply = "".join(
            "".join(text_by_id[mid]) for mid in msg_order
        ).strip()

        if reply:
            log.info("Signal → %s: %r", sender, reply[:80])
            await self._signal.send(sender, reply)
        else:
            log.warning("Empty reply for session %s", session_id)

    async def stop(self):
        if self._goosed:
            await self._goosed.close()
        if self._signal:
            await self._signal.close()
