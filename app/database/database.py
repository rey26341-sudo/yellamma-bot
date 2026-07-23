import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Was previously hardcoded to SQLite regardless of environment —
# every appointment write silently went to a local yellamma.db file
# instead of the Postgres database configured everywhere else
# (docker-compose.yml, .env, the LangGraph checkpointer). Now reads
# DATABASE_URL properly, same as the rest of the app, and only falls
# back to SQLite if it's genuinely not set (e.g. a fresh dev checkout
# with no .env yet).
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./yellamma.db")

# connect_args={"check_same_thread": False} is SQLite-specific — it's
# not a valid argument for psycopg's Postgres connections, so it's
# only applied when actually falling back to SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
