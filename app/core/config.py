"""
Central application configuration.

All secrets and environment-dependent values come from the process
environment (.env in dev, real env vars / secrets manager in
staging-production) — never hardcoded, never with a working default for
anything sensitive. Pydantic validates everything on import, so a
missing/misconfigured secret fails at startup instead of surfacing later
as a mysterious runtime error (or, worse, silently degrading — e.g. the
old DATABASE_URL fallback to SQLite).

Extend this as the app grows (Twilio, WhatsApp Business API, payment
webhook secrets, etc.) rather than reading os.environ ad hoc elsewhere in
the codebase — one source of truth makes it possible to audit exactly
what the app depends on.
"""

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment -------------------------------------------------
    app_env: Literal["dev", "staging", "production"] = Field(default="production")
    debug: bool = Field(default=False)

    # --- Database ------------------------------------------------------
    # No default here on purpose — see database.py, which raises at
    # startup outside of app_env=dev if this is unset. Config.py mirrors
    # that: no silent fallback baked in at the settings layer either.
    database_url: str | None = Field(default=None)
    
    # --- Authentication ---------------------------------------------
    jwt_secret_key: str = Field(...)
   
    # --- LLM -------------------------------------------------------
    gemini_api_key: str = Field(...)  # required — no default, ever

    # --- CORS --------------------------------------------------------
    # Comma-separated in the env var, e.g.
    #   CORS_ALLOWED_ORIGINS=https://app.yellamma.com,https://yellamma.com
    # Deliberately no "*" default — that was the old main.py bug.
    cors_allowed_origins: str = Field(default="")

    @field_validator("gemini_api_key")
    @classmethod
    def _no_placeholder_key(cls, v: str) -> str:
        placeholders = {"", "your_google_gemini_api_key_here", "changeme"}
        if v.strip().lower() in placeholders:
            raise ValueError(
                "GEMINI_API_KEY looks like a placeholder value from the "
                "README example, not a real key."
            )
        return v

    @field_validator("database_url")
    @classmethod
    def _no_credentials_in_logs(cls, v: str | None) -> str | None:
        # Not a transformation — just documents intent: never log this
        # field. Enforced by convention in logging config, not code,
        # since pydantic settings objects can still be str()'d by
        # accident (e.g. in a debug endpoint). See note in __repr__ below.
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    def __repr__(self) -> str:
        # Prevent accidental leakage of database_url / api keys via
        # logging a Settings instance, str(settings) in an error
        # message, etc. Access fields directly when you actually need
        # the value.
        return "Settings(app_env=%r, debug=%r)" % (self.app_env, self.debug)

    __str__ = __repr__


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton — Settings() re-reads and re-validates the
    environment every time it's constructed, which is wasteful and
    (for the validators above) unnecessary to repeat per-request.
    Import get_settings and call it, rather than constructing
    Settings() directly, everywhere else in the app.
    """
    settings = Settings()
    if settings.app_env == "production" and settings.debug:
        # Not fatal, but should never happen — surfaced loudly instead
        # of silently running production with debug on (verbose
        # tracebacks, potential info disclosure).
        logger.warning(
            "DEBUG=true while APP_ENV=production — this should not "
            "normally be the case."
        )
    return settings


settings = get_settings()
