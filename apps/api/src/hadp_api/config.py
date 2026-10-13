"""Application configuration.

Values come from environment variables (set by `make`, uvicorn, CI, or tests).
For local convenience a repo-root `.env.local` is loaded if present; real env vars
always take precedence. No secrets are hard-coded.
"""

from __future__ import annotations

import ipaddress
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

Network = ipaddress.IPv4Network | ipaddress.IPv6Network

# How many entries of X-Forwarded-For a deployment may have to step over (TRUSTED_PROXY_HOPS).
MAX_PROXY_HOPS = 8


@lru_cache
def parse_trusted_proxies(spec: str) -> tuple[Network, ...]:
    """The networks named in TRUSTED_PROXIES: addresses or CIDR ranges, separated by commas.

    Raises ValueError for an entry that is neither — and for a range that holds every
    address, which would let any caller say on whose behalf it calls.
    """
    networks: list[Network] = []
    for entry in (part.strip() for part in spec.split(",")):
        if not entry:
            continue
        network = ipaddress.ip_network(entry, strict=False)
        if network.prefixlen == 0:
            raise ValueError("a range that holds every address")
        networks.append(network)
    return tuple(networks)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # A refused configuration names what is wrong, never the values it was given: the
        # error is raised at import and printed by whatever starts the process — and the
        # input it would quote holds the session secret and the database passwords.
        hide_input_in_errors=True,
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

    # Whose request it is, for the limits that count per client address
    # (security/client_address.py). The API's peer is the web server for every browser, so the
    # web server passes on the X-Forwarded-For it received — and the API believes that header
    # only from a peer named here (addresses or CIDR ranges, separated by commas: the web
    # server's). Empty: the header is never read and those limits count the peer, which is
    # one budget for everyone behind the web server.
    trusted_proxies: str = ""
    # Which entry of X-Forwarded-For is the client, counted from the right: the number of
    # proxies in front of the web server that each add the address they saw (1 = one TLS
    # proxy). Everything further left was written by the client itself.
    trusted_proxy_hops: int = 1

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
    def _check_trusted_proxies(self) -> Settings:
        """In every environment: a value that cannot be read is refused at start, not at the
        first request that would need it. The message names the setting, never its value."""
        try:
            parse_trusted_proxies(self.trusted_proxies)
        except ValueError:
            raise ValueError(
                "TRUSTED_PROXIES must be addresses or CIDR ranges separated by commas, "
                "and no range may hold every address"
            ) from None
        if not 1 <= self.trusted_proxy_hops <= MAX_PROXY_HOPS:
            raise ValueError(f"TRUSTED_PROXY_HOPS must be between 1 and {MAX_PROXY_HOPS}")
        return self

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
