"""The catalog-seeding command, `python -m hadp_api.scripts.seed_catalog` — the seeding step of
a deployment (ADR-0004 §18).

It is run the way a deployment runs it: as its own process, in production mode, with the admin
DSN, against a database that Alembic has just created and nothing else has written to. That
database is this module's own (the suite's database gets its catalog from conftest, so it
could not show that the command seeds anything).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session

import hadp_api.modules  # noqa: F401  (registers all ORM models on Base.metadata)
from hadp_api.db.base import Base
from hadp_api.modules.imports.normalize import automatic_names, unconfirmed_names
from hadp_api.modules.kpi.catalog_data import EXTRA_ALIASES, kpi_rows
from hadp_api.modules.kpi.service import load_terminology, seed_terminology

_API_DIR = Path(__file__).resolve().parents[1]
_CATALOG_TABLES = (
    "kpi_catalog_release",
    "kpi_catalog",
    "kpi_external_code",
    "kpi_alias",
    "kpi_secondary_domain",
)


def _production_env(database_url: str) -> dict[str, str]:
    """The environment of a migrate step: production mode, so the configuration guard runs."""
    database = make_url(database_url).database
    app_url = make_url(os.environ["APP_DATABASE_URL"]).set(database=database)
    return {
        **os.environ,
        "APP_ENV": "production",
        "DATABASE_URL": database_url,
        "APP_DATABASE_URL": app_url.render_as_string(hide_password=False),
        "SESSION_SECRET": "s" * 40,
        "S3_ACCESS_KEY_ID": "synthetic-key-id",
        "S3_SECRET_ACCESS_KEY": "synthetic-key",
        "SESSION_COOKIE_NAME": "__Host-hadp_session",
        "CSRF_COOKIE_NAME": "__Host-hadp_csrf",
    }


def _python(database_url: str, *module_and_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *module_and_args],
        cwd=_API_DIR,
        env=_production_env(database_url),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def _seed_catalog(database_url: str) -> subprocess.CompletedProcess[str]:
    return _python(database_url, "hadp_api.scripts.seed_catalog")


def _unconfirmed(engine: Engine) -> list[str]:
    with Session(engine) as db:
        return unconfirmed_names(load_terminology(db))


def _rows_as_stored(engine: Engine) -> dict[str, list[tuple[str, str]]]:
    """Every catalog row with the id of the transaction that last wrote it: an UPDATE that
    changes nothing still changes this."""
    with engine.connect() as conn:
        return {
            table: [
                (row[0], row[1])
                for row in conn.execute(
                    text(f"SELECT xmin::text, t::text FROM {table} AS t ORDER BY t::text")
                )
            ]
            for table in _CATALOG_TABLES
        }


def _rows_outside_the_catalog(engine: Engine) -> dict[str, int]:
    """Row counts of every application table that is not a catalog table (non-empty only)."""
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name in _CATALOG_TABLES:
                continue
            count = conn.execute(text(f'SELECT count(*) FROM "{table.name}"')).scalar_one()
            if count:
                counts[table.name] = count
    return counts


@dataclass(frozen=True)
class _FirstRun:
    engine: Engine
    database_url: str
    unconfirmed_before: list[str]
    completed: subprocess.CompletedProcess[str]


@pytest.fixture(scope="module")
def first_run() -> Iterator[_FirstRun]:
    """A database of this module's own, migrated to head, and the command run on it once."""
    admin = make_url(os.environ["DATABASE_URL"])
    name = f"{admin.database}_seed_catalog"
    database_url = admin.set(database=name).render_as_string(hide_password=False)
    maintenance = create_engine(admin.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engine = create_engine(database_url)
    try:
        with maintenance.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        migrated = _python(database_url, "alembic", "upgrade", "head")
        assert migrated.returncode == 0, migrated.stderr
        unconfirmed_before = _unconfirmed(engine)
        yield _FirstRun(engine, database_url, unconfirmed_before, _seed_catalog(database_url))
    finally:
        engine.dispose()
        with maintenance.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        maintenance.dispose()


def test_a_fresh_database_gets_a_catalog_that_confirms_the_six_names(first_run: _FirstRun) -> None:
    # Migrated and never seeded: the import would hold every one of its names for review.
    assert first_run.unconfirmed_before == sorted(automatic_names())

    assert first_run.completed.returncode == 0, first_run.completed.stderr
    assert _unconfirmed(first_run.engine) == []
    with Session(first_run.engine) as db:
        assert load_terminology(db) == seed_terminology()


def test_running_it_again_changes_nothing(first_run: _FirstRun) -> None:
    before = _rows_as_stored(first_run.engine)
    assert all(before[table] for table in _CATALOG_TABLES)

    again = _seed_catalog(first_run.database_url)

    assert again.returncode == 0, again.stderr
    assert _rows_as_stored(first_run.engine) == before
    assert "already present" in again.stdout
    assert again.stdout.count("(+0)") == len(_CATALOG_TABLES)


def test_it_writes_the_catalog_and_no_other_table(first_run: _FirstRun) -> None:
    """No clinic, no member of staff, no patient — which is what lets it run in production."""
    assert first_run.completed.returncode == 0, first_run.completed.stderr
    assert _rows_outside_the_catalog(first_run.engine) == {}


def test_the_synthetic_seeder_refuses_where_this_command_runs(first_run: _FirstRun) -> None:
    refused = _python(first_run.database_url, "hadp_api.scripts.seed")

    assert refused.returncode != 0
    assert "refusing to seed synthetic data" in refused.stderr
    assert _rows_outside_the_catalog(first_run.engine) == {}


def test_it_prints_row_counts_and_no_catalog_content(first_run: _FirstRun) -> None:
    out = first_run.completed.stdout
    with first_run.engine.connect() as conn:
        for table in _CATALOG_TABLES:
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            assert f"{count} rows (+{count})" in out, table

    printed = (out + first_run.completed.stderr).lower()
    content = {str(row["code"]).lower() for row in kpi_rows()}
    content |= {str(row["display_name"]).lower() for row in kpi_rows()}
    content |= {alias.lower() for alias, _ in EXTRA_ALIASES}
    assert not {value for value in content if value in printed}


def test_a_catalog_that_no_longer_confirms_a_name_fails_the_step(first_run: _FirstRun) -> None:
    """An existing release is never updated, so the command cannot repair it: it must say so
    instead of reporting a seeded catalog while the import holds the name's values back."""
    retire = "UPDATE kpi_catalog SET status = :status WHERE code = 'cardio.ldl_c'"
    with first_run.engine.begin() as conn:
        conn.execute(text(retire), {"status": "deprecated"})
    try:
        before = _rows_as_stored(first_run.engine)
        drifted = _seed_catalog(first_run.database_url)
        assert drifted.returncode == 1
        assert "ldl, ldl cholesterol" in drifted.stderr
        assert _rows_as_stored(first_run.engine) == before
    finally:
        with first_run.engine.begin() as conn:
            conn.execute(text(retire), {"status": "active"})
    assert _unconfirmed(first_run.engine) == []


_AUTOMATIC_KPIS = (
    "cardio.ldl_c",
    "cardio.total_cholesterol",
    "cardio.hdl_c",
    "metabolic.fasting_plasma_glucose",
    "metabolic.hba1c",
)


def test_a_changed_unit_of_an_automatic_kpi_fails_the_step(first_run: _FirstRun) -> None:
    change = "UPDATE kpi_catalog SET canonical_unit_ucum = :unit WHERE code = 'metabolic.hba1c'"
    with first_run.engine.begin() as conn:
        original = conn.execute(
            text("SELECT canonical_unit_ucum FROM kpi_catalog WHERE code = 'metabolic.hba1c'")
        ).scalar_one()
        conn.execute(text(change), {"unit": "mmol/mol"})
    try:
        drifted = _seed_catalog(first_run.database_url)
        assert drifted.returncode == 1
        assert "hba1c" in drifted.stderr
    finally:
        with first_run.engine.begin() as conn:
            conn.execute(text(change), {"unit": original})
    assert _unconfirmed(first_run.engine) == []


def test_a_catalog_changed_in_place_is_not_reported_as_seeded(first_run: _FirstRun) -> None:
    """The six automatic names still agree, the release is the build's own — and a KPI the
    import does not act on by itself has another unit than the build ships. "Already present"
    would be true and would hide it."""
    with first_run.engine.begin() as conn:
        code, original = conn.execute(
            text(
                """
                SELECT c.code, c.canonical_unit_ucum
                  FROM kpi_catalog c
                  JOIN kpi_alias a ON a.kpi_code = c.code AND a.source_system = ''
                 WHERE c.status = 'active' AND c.canonical_unit_ucum IS NOT NULL
                   AND c.code <> ALL(:automatic)
                 ORDER BY c.code
                 LIMIT 1
                """
            ),
            {"automatic": list(_AUTOMATIC_KPIS)},
        ).one()
    change = "UPDATE kpi_catalog SET canonical_unit_ucum = :unit WHERE code = :code"
    with first_run.engine.begin() as conn:
        conn.execute(text(change), {"unit": "changed-in-place", "code": code})
    try:
        assert _unconfirmed(first_run.engine) == []  # the import's own check sees nothing
        before = _rows_as_stored(first_run.engine)
        drifted = _seed_catalog(first_run.database_url)
        assert drifted.returncode == 1
        assert "does not resolve names as this build's catalog does" in drifted.stderr
        assert "already present" in drifted.stdout
        assert _rows_as_stored(first_run.engine) == before
        # Says that it differs, not what: no catalog content is printed.
        assert code not in drifted.stderr + drifted.stdout
    finally:
        with first_run.engine.begin() as conn:
            conn.execute(text(change), {"unit": original, "code": code})
    with Session(first_run.engine) as db:
        assert load_terminology(db) == seed_terminology()


def test_another_release_in_the_database_stops_the_step_before_it_writes(
    first_run: _FirstRun,
) -> None:
    """The command seeds an empty catalog; it does not replace a release. Seeding over one
    would collide with the rows that are there — it says which release it found and what it
    ships, with an exit code of its own."""
    with first_run.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO kpi_catalog_release (version, status)"
                " VALUES ('kpi-cat-0.0.1-test', 'retired')"
            )
        )
    try:
        before = _rows_as_stored(first_run.engine)
        refused = _seed_catalog(first_run.database_url)
        assert refused.returncode == 2
        assert "kpi-cat-0.0.1-test" in refused.stderr
        assert "Nothing was written" in refused.stderr
        assert refused.stdout == ""
        assert _rows_as_stored(first_run.engine) == before
    finally:
        with first_run.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM kpi_catalog_release WHERE version = 'kpi-cat-0.0.1-test'")
            )
    assert _seed_catalog(first_run.database_url).returncode == 0
