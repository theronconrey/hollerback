"""
In-memory session store mapping Signal sender → goosed session_id.

Simple dict for now. Could be persisted to disk later if restart continuity matters.
"""


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, str] = {}

    def get(self, sender: str) -> str | None:
        return self._sessions.get(sender)

    def set(self, sender: str, session_id: str) -> None:
        self._sessions[sender] = session_id

    def remove(self, sender: str) -> None:
        self._sessions.pop(sender, None)

    def all(self) -> dict[str, str]:
        return dict(self._sessions)
