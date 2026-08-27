"""
Async database layer.

Supports both local SQLite (dev mode) and cloud PostgreSQL without configuration conflicts.
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
        _RAW_DATABASE_URL = "sqlite+aiosqlite:///./yellamma.dev.db"
        logger.warning(
            "DATABASE_URL not set; using local SQLite fallback because APP_ENV=%s.",
            APP_ENV,
        )
    else:
        raise RuntimeError(
            "DATABASE_URL is not set. Refusing to start: in non-dev environments "
            "this must point at the real Postgres instance. (Set APP_ENV=dev for local SQLite)."
        )


def _normalize_url(raw_url: str) -> str:
    if not raw_url:
        return raw_url

    # Return clean async SQLite drivers directly without running urlsplit
    if raw_url.startswith("sqlite+aiosqlite"):
        return raw_url

    if raw_url.startswith("sqlite://"):
        return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    parts = urlsplit(raw_url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
        scheme = "postgresql+asyncpg"

    is_local = parts.hostname in ("localhost", "127.0.0.1", None)
    is_postgres = scheme.startswith("postgresql")

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if is_postgres and not is_local:
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
    "echo": False,
}

if _is_postgres:
    engine_kwargs["pool_pre_ping"] = True
    connect_args["ssl"] = "require" if (not _is_local_host and not _IS_DEV) else False
    connect_args["server_settings"] = {"statement_timeout": "15000"}
    engine_kwargs.update(
        pool_size=10,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=30,
    )
elif _is_sqlite:
    pass

engine = create_async_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

SessionLocal = AsyncSessionLocal
Base = declarative_base()


async def get_db():
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
    if not _IS_DEV:
        raise RuntimeError("init_models() is dev-only; use Alembic migrations in production.")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
