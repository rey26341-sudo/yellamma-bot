"""
Async database layer.

Replaces the old sync, SQLite-fallback engine. That version silently wrote
every appointment to a local yellamma.db file whenever DATABASE_URL wasn't
set correctly — a data-integrity bug as much as a security one, since it
meant appointments could vanish from what the rest of the app (LangGraph
checkpointer, admin queries, backups) assumed was the single source of
truth.

This version:
  - Requires DATABASE_URL outside of local dev; never falls back to SQLite
    unless you explicitly opt into dev mode.
  - Forces TLS (sslmode=require) on any non-localhost connection.
  - Bounds the connection pool and sets a statement timeout, so a stuck
    query or a leak can't take down every tenant sharing the pool.
  - Never logs the connection string (which contains the DB password).
"""

import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

APP_ENV = os.environ.get("APP_ENV", "production").lower()
_IS_DEV = APP_ENV in ("dev", "development", "local")

_RAW_DATABASE_URL = os.environ.get("DATABASE_URL")

if not _RAW_DATABASE_URL:
    if _IS_DEV:
        # Explicit opt-in only — you must set APP_ENV=dev to get this
        # fallback. In every other case, a missing DATABASE_URL is a
        # config error and should fail loudly rather than silently
        # writing to a local file no one is backing up or auditing.
        _RAW_DATABASE_URL = "sqlite+aiosqlite:///./yellamma.dev.db"
        logger.warning(
            "DATABASE_URL not set; using local SQLite fallback because "
            "APP_ENV=%s. This is only intended for local development.",
            APP_ENV,
        )
    else:
        raise RuntimeError(
            "DATABASE_URL is not set. Refusing to start: in non-dev "
            "environments this must point at the real Postgres instance. "
            "(Set APP_ENV=dev if you intentionally want the local SQLite "
            "fallback for development.)"
        )


def _normalize_url(raw_url: str) -> str:
    """
    Rewrite the URL to use the async driver, and force TLS unless the
    host is local. Doesn't touch or log the credentials themselves.
    """
    parts = urlsplit(raw_url)
    scheme = parts.scheme

    # sync -> async driver
    if scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
        scheme = "postgresql+asyncpg"
    elif scheme in ("sqlite",):
        scheme = "sqlite+aiosqlite"

    is_local = parts.hostname in ("localhost", "127.0.0.1", None)
    is_postgres = scheme.startswith("postgresql")

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if is_postgres and not is_local:
        # asyncpg takes ssl via connect_args, not a query param, so we
        # strip any sslmode here and enforce it via connect_args below.
        query.pop("sslmode", None)

    new_parts = parts._replace(scheme=scheme, query=urlencode(query))
    return urlunsplit(new_parts)


DATABASE_URL = _normalize_url(_RAW_DATABASE_URL)
_parsed = urlsplit(DATABASE_URL)
_is_local_host = _parsed.hostname in ("localhost", "127.0.0.1", None)
_is_postgres = DATABASE_URL.startswith("postgresql")
_is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {}
engine_kwargs = {
    "echo": False,  # never echo SQL (and therefore never echo bound
                     # params that may include PII) outside of a
                     # deliberate, explicit debug session
    "pool_pre_ping": True,  # drop dead connections instead of handing
                             # a request a broken one
}

if _is_postgres:
    connect_args["ssl"] = "require" if (not _is_local_host and not _IS_DEV) else False
    # asyncpg statement timeout, in the "server_settings" it accepts;
    # keeps one slow/runaway query from monopolizing a pooled connection
    connect_args["server_settings"] = {"statement_timeout": "15000"}  # ms
    engine_kwargs.update(
        pool_size=10,
        max_overflow=10,
        pool_recycle=1800,  # recycle connections every 30 min
        pool_timeout=30,
    )
elif _is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_async_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# Compatibility alias so older code importing SessionLocal still resolves
# while the app continues to use AsyncSessionLocal + get_db.
SessionLocal = AsyncSessionLocal

Base = declarative_base()


async def get_db():
    """
    FastAPI dependency — yields an AsyncSession and guarantees it's
    closed, and rolled back on error, even if the caller forgets to.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope():
    """
    Non-FastAPI context manager for scripts/background jobs
    (e.g. the LangGraph checkpointer, migration scripts) that need a
    session outside of a request lifecycle.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_models():
    """
    Dev/test convenience only — creates tables from Base.metadata.
    In staging/production, use Alembic migrations instead so schema
    changes are reviewed and reversible.
    """
    if not _IS_DEV:
        raise RuntimeError(
            "init_models() is dev-only; use Alembic migrations in "
            "staging/production."
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
