"""
app/voice/session.py

Provider-agnostic call-session storage (Redis). Keyed by an opaque
`session_id` — for Exotel that's `stream_sid`; a future Twilio
adapter would use `streamSid`. Nothing here knows or cares which
telephony provider it came from.
"""

import json
import os
from typing import Optional

import redis.asyncio as redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = 30 * 60  # expire abandoned call sessions after 30 min

DEFAULT_SESSION = {
    "step": "name",
    "name": "",
    "service": "",
    "date": "",
    "time": "",
}

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _key(session_id: str) -> str:
    return f"voice:session:{session_id}"


async def load_session(session_id: str) -> dict:
    r = get_redis()
    raw = await r.get(_key(session_id))
    if raw:
        return json.loads(raw)
    return dict(DEFAULT_SESSION)


async def save_session(session_id: str, session: dict) -> None:
    r = get_redis()
    await r.set(_key(session_id), json.dumps(session), ex=SESSION_TTL_SECONDS)


async def clear_session(session_id: str) -> None:
    r = get_redis()
    await r.delete(_key(session_id))
