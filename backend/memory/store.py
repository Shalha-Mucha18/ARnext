import json
from typing import Optional
import redis

from core.config import settings
from memory.models import SessionState

class SessionStore:
    def __init__(self):
        self._mem = {}  # fallback
        self._redis = None
        try:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    def _key(self, session_id: str) -> str:
        return f"salesgpt:session:{session_id}"

    def get(self, session_id: str) -> SessionState:
        if self._redis:
            raw = self._redis.get(self._key(session_id))
            if raw:
                return SessionState(**json.loads(raw))
            return SessionState()
        # fallback
        return self._mem.get(session_id, SessionState())

    def set(self, session_id: str, state: SessionState) -> None:
        if self._redis:
            self._redis.setex(
                self._key(session_id),
                settings.SESSION_TTL_SECONDS,
                state.model_dump_json()
            )
        else:
            self._mem[session_id] = state
