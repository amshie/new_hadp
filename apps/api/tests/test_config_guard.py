"""Production configuration fail-fast guards (no silent RLS fail-open)."""

from __future__ import annotations

import pytest

from hadp_api.config import Settings

_ADMIN = "postgresql+psycopg://postgres:postgres@db:5432/hadp"
_APP = "postgresql+psycopg://hadp_app:hadp_app@db:5432/hadp"
_STRONG_SECRET = "x" * 40


def _prod(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "app_env": "production",
        "database_url": _ADMIN,
        "app_database_url": _APP,
        "session_secret": _STRONG_SECRET,
        "s3_access_key_id": "real-key",
        "s3_secret_access_key": "real-secret",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_valid_production_config_boots() -> None:
    settings = _prod()
    assert settings.is_production
    assert settings.effective_app_database_url == _APP


def test_production_requires_app_database_url() -> None:
    with pytest.raises(ValueError, match="APP_DATABASE_URL must be set"):
        _prod(app_database_url=None)


def test_production_app_url_must_differ_from_admin() -> None:
    with pytest.raises(ValueError, match="must differ"):
        _prod(app_database_url=_ADMIN)


def test_production_rejects_default_session_secret() -> None:
    with pytest.raises(ValueError, match="SESSION_SECRET"):
        _prod(session_secret="dev-only-not-a-secret-change-me")


def test_production_rejects_default_s3_credentials() -> None:
    with pytest.raises(ValueError, match="S3 credentials"):
        _prod(s3_access_key_id="minioadmin")


def test_development_allows_defaults() -> None:
    # Dev/test must NOT enforce production constraints.
    settings = Settings(app_env="development", app_database_url=None)
    assert not settings.is_production
