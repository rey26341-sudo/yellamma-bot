"""
app/core/checkpointer.py

Postgres-backed persistence for the LangGraph core. This replaces
BOTH of the old in-memory stores at once:
  - ConversationService.sessions (booking flow state)
  - GeminiService._sessions (chat history)
with one durable store, keyed by a real thread_id, that survives
server restarts and works across multiple workers — neither of the
old dicts did either.

Reuses the same DATABASE_URL your appointments table already uses
(app/database/database.py) — one Postgres instance, one more schema
in it for LangGraph's own checkpoint tables.
"""

import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set — required for the LangGraph Postgres "
        "checkpointer. Check your .env file."
    )


async def build_checkpointer() -> AsyncPostgresSaver:
    """
    Call once at app startup (see app/main.py's lifespan). Returns an
    open AsyncPostgresSaver — the caller is responsible for keeping
    its context alive for the app's lifetime and closing it on
    shutdown.

    NOTE: this has not been run against a live Postgres instance yet.
    The first time you start the app after this change, watch for
    errors here specifically — `.setup()` creates LangGraph's own
    checkpoint tables if they don't exist yet, so it needs a Postgres
    user with CREATE TABLE permission on the target database.
    """
    saver_cm = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
    checkpointer = await saver_cm.__aenter__()
    await checkpointer.setup()
    return checkpointer, saver_cm
