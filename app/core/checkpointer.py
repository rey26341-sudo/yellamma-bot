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
from contextlib import asynccontextmanager

# Add this import at the top
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def build_checkpointer():
    app_env = os.getenv("APP_ENV", "dev")
    db_url = os.getenv("DATABASE_URL")

    if app_env == "dev" or "sqlite" in db_url:
        # 1. Clean the SQLAlchemy URL to get a standard file path for raw SQLite
        # Converts "sqlite+aiosqlite:///./yellamma.dev.db" to "./yellamma.dev.db"
        sqlite_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

        # 2. Use the SqliteSaver
        saver_cm = AsyncSqliteSaver.from_conn_string(sqlite_path)
    else:
        # Use PostgresSaver for production
        # Note: psycopg requires postgresql:// not postgresql+asyncpg://
        postgres_url = db_url.replace("+asyncpg", "")
        saver_cm = AsyncPostgresSaver.from_conn_string(postgres_url)

    checkpointer = await saver_cm.__aenter__()
    await checkpointer.setup() # Initialize checkpointer tables
    return checkpointer, saver_cm
