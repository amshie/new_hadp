"""Application configuration.

Values come from environment variables (set by `make`, uvicorn, CI, or tests).
For local convenience a repo-root `.env.local` is loaded if present; real env vars
always take precedence. No secrets are hard-coded.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SESSION_SECRET = "dev-only-not-a-secret-change-me"
_DEV_S3_CREDENTIAL = "minioadmin"

# repo root = .../NEW_HADP (this file is apps/api/src/hadp_api/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[4]

AppEnv = Literal["development", "test", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "development"

    # Admin/migration DSN (superuser). Used by Alembic and the synthetic seeder.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:55433/hadp"
    # Application DSN (non-superuser `hadp_app`) so PostgreSQL RLS is enforced.
    # Unset, it falls back to the admin DSN — which the engine then refuses to use, in every
    # environment (db/engine.py): a superuser ignores RLS, so the app does not run as one.
    app_database_url: str | None = None

    redis_url: str = "redis://127.0.0.1:56379/0"

    # S3-compatible object storage (MinIO locally; EU-region bucket in production).
    s3_endpoint_url: str | None = "http://127.0.0.1:59000"
    s3_region: str = "eu-central-1"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_source_documents: str = "hadp-source-documents"

    session_secret: str = "dev-only-not-a-secret-change-me"
    # Production config must use the __Host- prefix on BOTH cookies (enforced below):
    # the prefix pins Secure + Path=/ + host-only at the browser level. Dev (http)
    # keeps the plain names because __Host- requires HTTPS.
    session_cookie_name: str = "hadp_session"
    csrf_cookie_name: str = "hadp_csrf"
    session_ttl_seconds: int = 60 * 60 * 8  # 8h

    api_base_url: str = "http://127.0.0.1:8000"
    # Laboratory files carry wall-clock times without a zone. They are read in this zone
    # (the DACH pilot default); a time that does not name exactly one instant goes to review.
    # Report statements state a sampling time as wall-clock time in the same zone.
    lab_local_timezone: str = "Europe/Berlin"
    # Web app base URL — used to build the patient-facing view link on report release.
    web_base_url: str = "http://127.0.0.1:3000"

    # Production OIDC provider (gated vendor decision; unset in dev/test).
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def effective_app_database_url(self) -> str:
        return self.app_database_url or self.database_url

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> Settings:
        """Fail-fast in production rather than silently falling open.

        The entire tenant-isolation guarantee depends on the app connecting as the
        non-superuser `hadp_app` role. If APP_DATABASE_URL is unset, the app would fall
        back to the admin/superuser DSN, which bypasses RLS. Refuse to boot in that case,
        and reject known dev-default secrets.
        """
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if not self.app_database_url:
            problems.append("APP_DATABASE_URL must be set (non-superuser role) in production")
        elif self.app_database_url == self.database_url:
            problems.append("APP_DATABASE_URL must differ from the admin DATABASE_URL")
        if self.session_secret == _DEV_SESSION_SECRET or len(self.session_secret) < 32:
            problems.append("SESSION_SECRET must be a strong non-default value (>= 32 chars)")
        if _DEV_S3_CREDENTIAL in (self.s3_access_key_id, self.s3_secret_access_key):
            problems.append("S3 credentials must not be the dev default in production")
        if not self.session_cookie_name.startswith("__Host-"):
            problems.append("SESSION_COOKIE_NAME must use the __Host- prefix in production")
        if not self.csrf_cookie_name.startswith("__Host-"):
            problems.append("CSRF_COOKIE_NAME must use the __Host- prefix in production")
        if problems:
            raise ValueError("unsafe production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
