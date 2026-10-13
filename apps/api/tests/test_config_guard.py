"""Production configuration fail-fast guards (no silent RLS fail-open)."""

from __future__ import annotations

import ipaddress

import pytest

from hadp_api.config import MAX_PROXY_HOPS, Settings, parse_trusted_proxies

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
        "session_cookie_name": "__Host-hadp_session",
        "csrf_cookie_name": "__Host-hadp_csrf",
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


def test_production_requires_host_prefixed_cookies() -> None:
    with pytest.raises(ValueError, match="SESSION_COOKIE_NAME"):
        _prod(session_cookie_name="hadp_session")
    with pytest.raises(ValueError, match="CSRF_COOKIE_NAME"):
        _prod(csrf_cookie_name="hadp_csrf")


def test_development_allows_defaults() -> None:
    # Dev/test must NOT enforce production constraints.
    settings = Settings(app_env="development", app_database_url=None)
    assert not settings.is_production


def test_a_refused_configuration_does_not_quote_the_values_it_was_given() -> None:
    """The refusal is raised at import and printed by whatever starts the process."""
    secret = "session-secret-" + "s" * 30
    with pytest.raises(ValueError, match="SESSION_COOKIE_NAME") as refused:
        _prod(
            session_secret=secret,
            database_url="postgresql+psycopg://postgres:admin-password@db:5432/hadp",
            app_database_url="postgresql+psycopg://hadp_app:app-password@db:5432/hadp",
            s3_secret_access_key="object-store-secret",
            session_cookie_name="hadp_session",
        )
    text = str(refused.value)
    for value in (secret, secret[-12:], "admin-password", "app-password", "object-store-secret"):
        assert value not in text


# --- Whose word the API takes for a client's address (security/client_address.py) -----------


def test_by_default_no_peer_is_believed() -> None:
    settings = Settings(app_env="development")
    assert parse_trusted_proxies(settings.trusted_proxies) == ()
    assert settings.trusted_proxy_hops == 1
    assert parse_trusted_proxies(_prod().trusted_proxies) == ()


def test_trusted_proxies_are_addresses_and_networks() -> None:
    settings = _prod(trusted_proxies=" 10.20.0.5 , 10.30.0.0/24, fd00:1::/64 ,")
    assert parse_trusted_proxies(settings.trusted_proxies) == (
        ipaddress.ip_network("10.20.0.5/32"),
        ipaddress.ip_network("10.30.0.0/24"),
        ipaddress.ip_network("fd00:1::/64"),
    )


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
@pytest.mark.parametrize(
    "value",
    [
        "*",  # "everyone" is how this setting is usually got wrong
        "0.0.0.0/0",
        "::/0",
        "10.20.0.5, 0.0.0.0/0",
        "web",  # a host name is not an address
        "10.20.0.5, the-web-server.internal",
        "10.20.0.5;10.20.0.6",
    ],
)
def test_a_trusted_proxy_setting_that_cannot_be_read_or_holds_everyone_is_refused(
    app_env: str, value: str
) -> None:
    """In every environment, at start — and without quoting what it was given."""
    with pytest.raises(ValueError, match="TRUSTED_PROXIES must be") as refused:
        if app_env == "production":
            _prod(trusted_proxies=value)
        else:
            Settings(app_env=app_env, trusted_proxies=value)  # type: ignore[arg-type]
    assert value not in str(refused.value)
    assert "the-web-server.internal" not in str(refused.value)


@pytest.mark.parametrize("hops", [0, -1, MAX_PROXY_HOPS + 1])
def test_the_number_of_proxies_is_bounded(hops: int) -> None:
    with pytest.raises(ValueError, match="TRUSTED_PROXY_HOPS must be between"):
        Settings(app_env="development", trusted_proxy_hops=hops)


def test_the_bounds_of_the_number_of_proxies_are_accepted() -> None:
    assert Settings(app_env="development", trusted_proxy_hops=1).trusted_proxy_hops == 1
    assert _prod(trusted_proxy_hops=MAX_PROXY_HOPS).trusted_proxy_hops == MAX_PROXY_HOPS
