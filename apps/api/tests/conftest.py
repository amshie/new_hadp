"""Test configuration and fixtures.

Tests run against a real PostgreSQL (synthetic data only). The application connects as
the non-superuser `hadp_app` role so row-level security is exercised exactly as in
production; an `admin_session` (superuser) is provided for test setup that needs to
bypass RLS. Each test runs against a truncated database.
"""

from __future__ import annotations

# --- Environment must be configured before any hadp_api import. ---
import os

_DEFAULT_ADMIN = "postgresql+psycopg://postgres:postgres@127.0.0.1:55433/hadp_test"
_DEFAULT_APP = "postgresql+psycopg://hadp_app:hadp_app@127.0.0.1:55433/hadp_test"

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _DEFAULT_ADMIN)
os.environ["APP_DATABASE_URL"] = os.environ.get("TEST_APP_DATABASE_URL", _DEFAULT_APP)

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import URL, create_engine, make_url, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from hadp_api.config import get_settings  # noqa: E402


def _ensure_database_exists(admin_url: str) -> None:
    url = make_url(admin_url)
    maintenance = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    engine = create_engine(maintenance, isolation_level="AUTOCOMMIT", future=True)
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _provision_schema() -> None:
    """Ensure the test database exists and is migrated to head."""
    get_settings.cache_clear()
    settings = get_settings()
    _ensure_database_exists(settings.database_url)

    from alembic import command
    from alembic.config import Config

    from hadp_api.db.engine import reset_engine

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(here, "alembic.ini"))
    command.upgrade(cfg, "head")
    reset_engine()

    # Seed the global, read-only KPI catalog once (reference data; not truncated between tests).
    from hadp_api.modules.kpi.service import seed_kpi_catalog

    seed_engine = create_engine(settings.database_url, future=True)
    with Session(seed_engine) as seed_session:
        seed_kpi_catalog(seed_session)
        seed_session.commit()
    seed_engine.dispose()


@pytest.fixture()
def admin_engine():  # type: ignore[no-untyped-def]
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_db(admin_engine) -> None:  # type: ignore[no-untyped-def]
    """Truncate all tables before each test (admin bypasses RLS; truncate not blocked)."""
    import hadp_api.modules  # noqa: F401  registers models
    from hadp_api.db.base import Base

    # The KPI catalog is global read-only reference data seeded once — never truncated per test.
    reference = {
        "kpi_catalog",
        "kpi_catalog_release",
        "kpi_external_code",
        "kpi_alias",
        "kpi_secondary_domain",
    }
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name not in reference)
    with admin_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def admin_session(admin_engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    with Session(admin_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture()
def client() -> Iterator[TestClient]:  # type: ignore[name-defined]  # noqa: F821
    from fastapi.testclient import TestClient

    from hadp_api.db.engine import reset_engine
    from hadp_api.main import app

    reset_engine()
    with TestClient(app) as test_client:
        yield test_client
