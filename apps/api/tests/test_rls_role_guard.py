"""The application does not run as a database role that bypasses row-level security.

A superuser or a BYPASSRLS role ignores every tenant policy without an error
(docs/notes/0005), so nothing but this guard says that isolation is off. It holds in every
environment, at startup and for every request, and a refused engine is never kept: the guard
once ran in production only, on the first use only — the first request failed and every later
one was served with RLS bypassed.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import make_url, text

from hadp_api.config import get_settings
from hadp_api.db import engine as engine_module
from hadp_api.db.engine import get_engine, get_sessionmaker, reset_engine
from hadp_api.main import app

_REFUSAL = "bypasses row-level security"


@pytest.fixture()
def run_app_as(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str], None]]:
    """Point the application at another database role for one test, then put it back."""

    def use(url: str) -> None:
        monkeypatch.setenv("APP_DATABASE_URL", url)
        get_settings.cache_clear()
        reset_engine()

    yield use
    monkeypatch.undo()
    get_settings.cache_clear()
    reset_engine()


def test_the_ordinary_app_role_is_accepted_and_the_engine_is_kept() -> None:
    reset_engine()
    first = get_engine()
    assert get_engine() is first
    with first.connect() as conn:
        assert conn.execute(text("SELECT current_setting('is_superuser')")).scalar_one() == "off"


def test_a_superuser_role_is_refused_every_time_not_only_the_first(
    run_app_as: Callable[[str], None],
) -> None:
    run_app_as(get_settings().database_url)  # the admin DSN
    for _ in range(3):
        with pytest.raises(RuntimeError, match=_REFUSAL):
            get_engine()
        assert engine_module._engine is None, "a refused engine was kept"
    with pytest.raises(RuntimeError, match=_REFUSAL):
        get_sessionmaker()


def test_a_role_that_is_not_a_superuser_but_bypasses_rls_is_refused(  # type: ignore[no-untyped-def]
    admin_engine, run_app_as: Callable[[str], None]
) -> None:
    role = f"hadp_test_bypass_{uuid.uuid4().hex[:12]}"
    password = uuid.uuid4().hex
    with admin_engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER BYPASSRLS"))
    try:
        url = make_url(get_settings().database_url).set(username=role, password=password)
        run_app_as(url.render_as_string(hide_password=False))
        with pytest.raises(RuntimeError, match=_REFUSAL):
            get_engine()
        assert engine_module._engine is None
    finally:
        reset_engine()
        with admin_engine.begin() as conn:
            conn.execute(text(f"DROP ROLE {role}"))


_OWNER_REFUSAL = "owns tables"


@pytest.fixture()
def scratch_role(admin_engine):  # type: ignore[no-untyped-def]
    """A login role that is neither a superuser nor BYPASSRLS, and a table to give it.

    The table is a scratch one of its own — no table of the application changes owner.
    """
    suffix = uuid.uuid4().hex[:12]
    role, password, table = f"hadp_test_owner_{suffix}", uuid.uuid4().hex, f"hadp_probe_{suffix}"
    with admin_engine.begin() as conn:
        conn.execute(
            text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS")
        )
        conn.execute(text(f"CREATE TABLE {table} (id integer)"))
    url = make_url(get_settings().database_url).set(username=role, password=password)
    yield role, table, url.render_as_string(hide_password=False)
    reset_engine()
    with admin_engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.execute(text(f"DROP ROLE {role}"))


def test_a_role_that_owns_a_table_is_refused(  # type: ignore[no-untyped-def]
    admin_engine, scratch_role, run_app_as: Callable[[str], None]
) -> None:
    role, table, url = scratch_role
    run_app_as(url)
    # The control: owning nothing, the role is accepted.
    get_engine()
    reset_engine()

    with admin_engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} OWNER TO {role}"))
    for _ in range(2):
        with pytest.raises(RuntimeError, match=_OWNER_REFUSAL):
            get_engine()
        assert engine_module._engine is None, "a refused engine was kept"


def test_a_role_that_is_a_member_of_a_table_owner_is_refused(  # type: ignore[no-untyped-def]
    admin_engine, scratch_role, run_app_as: Callable[[str], None]
) -> None:
    role, table, url = scratch_role
    owner = f"{role}_grp"
    with admin_engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {owner} NOLOGIN"))
        conn.execute(text(f"ALTER TABLE {table} OWNER TO {owner}"))
        conn.execute(text(f"GRANT {owner} TO {role}"))
    try:
        run_app_as(url)
        with pytest.raises(RuntimeError, match=_OWNER_REFUSAL):
            get_engine()
        assert engine_module._engine is None
    finally:
        reset_engine()
        with admin_engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {table}"))
            conn.execute(text(f"DROP ROLE {owner}"))


def test_no_request_is_served_through_a_role_that_bypasses_rls(
    run_app_as: Callable[[str], None],
) -> None:
    # No `with`: the app is taken as already running, so this is the per-request guard alone.
    client = TestClient(app, raise_server_exceptions=False)
    unknown = {"email": "nobody@synthetic.example"}
    # The control: as the ordinary role the lookup runs and says "unknown user".
    reset_engine()
    assert client.post("/api/v1/auth/dev-login", json=unknown).status_code == 401

    run_app_as(get_settings().database_url)
    for _ in range(3):
        resp = client.post("/api/v1/auth/dev-login", json=unknown)
        # 401 would mean the lookup ran — as a role that sees every tenant.
        assert resp.status_code == 500, resp.text
        assert engine_module._engine is None, "a refused engine was kept"


def test_the_api_does_not_start_as_a_role_that_bypasses_rls(
    run_app_as: Callable[[str], None],
) -> None:
    run_app_as(get_settings().database_url)
    # Refused on the way IN: a check that only ran at shutdown would reach the body.
    with pytest.raises(RuntimeError, match=_REFUSAL), TestClient(app):
        pytest.fail("the API started as a role that bypasses row-level security")


def test_two_first_requests_at_once_build_one_engine() -> None:
    """Sync handlers run in a thread pool: the first requests after a start arrive together."""
    from concurrent.futures import ThreadPoolExecutor

    reset_engine()
    with ThreadPoolExecutor(max_workers=8) as pool:
        engines = list(pool.map(lambda _: get_engine(), range(32)))
        factories = list(pool.map(lambda _: get_sessionmaker(), range(32)))
    assert len({id(e) for e in engines}) == 1
    assert len({id(f) for f in factories}) == 1
