"""Load the KPI catalog — and nothing else.

The laboratory import looks every name up in the catalog (ADR-0004 §18). This is the seeding
step of a deployment: it writes the catalog's reference tables and no other table, so — unlike
`hadp_api.scripts.seed`, which creates synthetic clinics, staff and patients and refuses to run
in production — it may run against any environment.

It connects with the admin DSN (`DATABASE_URL`), as Alembic does: the application role can
only read the catalog (migration 0004).

Idempotent. A release that is already in the database is left exactly as it is
(`seed_kpi_catalog` never updates one), and a second run adds no row.

It seeds; it does not upgrade. Where the database holds ANOTHER catalog release than the one
this build ships, nothing is written and the command stops with its own exit code: replacing
a release is a change of reference data with its own migration (ADR-0004), and seeding over
it would only collide with the rows that are there.

Afterwards the catalog in the database is held against this build's catalog and against the
import. Where it resolves a name differently from the build's catalog (an alias, a KPI's
status or its unit was changed in place), or does not confirm the names the import acts on
without a human, the command says so and fails — "already present" is not "as shipped".

Exit codes: 0 seeded or already present and as shipped; 1 present but not as shipped; 2 another
release is in the database.

Prints row counts and release identifiers only, never catalog content.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.modules.imports.normalize import automatic_names, unconfirmed_names
from hadp_api.modules.kpi.catalog_data import CATALOG_VERSION
from hadp_api.modules.kpi.models import (
    KpiAlias,
    KpiCatalog,
    KpiCatalogRelease,
    KpiExternalCode,
    KpiSecondaryDomain,
)
from hadp_api.modules.kpi.service import load_terminology, seed_kpi_catalog, seed_terminology

# Every table this command may write.
_CATALOG_TABLES = (KpiCatalogRelease, KpiCatalog, KpiExternalCode, KpiAlias, KpiSecondaryDomain)

EXIT_NOT_AS_SHIPPED = 1
EXIT_OTHER_RELEASE = 2


@dataclass(frozen=True)
class CatalogSeedResult:
    # Rows per catalog table after the run, and how many of them this run added.
    rows: dict[str, int]
    added: dict[str, int]
    # Releases in the database that are not this build's. Non-empty: nothing was written.
    other_releases: list[str]
    # Whether the database resolves every name as this build's catalog does.
    as_shipped: bool
    # The import's automatic names the catalog in the database does not confirm (empty = all).
    unconfirmed: list[str]


def _row_counts(db: Session) -> dict[str, int]:
    return {
        model.__tablename__: db.execute(select(func.count()).select_from(model)).scalar_one()
        for model in _CATALOG_TABLES
    }


def seed_catalog(engine: Engine) -> CatalogSeedResult:
    """Seed the catalog in one transaction and report what the database now holds."""
    with Session(engine) as db:
        before = _row_counts(db)
        releases = db.execute(select(KpiCatalogRelease.version)).scalars().all()
        other_releases = sorted(version for version in releases if version != CATALOG_VERSION)
        if other_releases:
            return CatalogSeedResult(
                rows=before,
                added=dict.fromkeys(before, 0),
                other_releases=other_releases,
                as_shipped=False,
                unconfirmed=[],
            )
        seed_kpi_catalog(db)
        db.commit()
        rows = _row_counts(db)
        held = load_terminology(db)
        as_shipped = held == seed_terminology()
        unconfirmed = unconfirmed_names(held)
    return CatalogSeedResult(
        rows=rows,
        added={table: rows[table] - before[table] for table in rows},
        other_releases=[],
        as_shipped=as_shipped,
        unconfirmed=unconfirmed,
    )


def main() -> int:
    engine = create_engine(get_settings().database_url, future=True)
    try:
        result = seed_catalog(engine)
    finally:
        engine.dispose()

    if result.other_releases:
        print(
            f"the database holds KPI catalog release {', '.join(result.other_releases)}; this "
            f"build ships {CATALOG_VERSION}. Nothing was written: this command seeds an empty "
            "catalog and does not replace a release — that is a migration of its own.",
            file=sys.stderr,
        )
        return EXIT_OTHER_RELEASE

    changed = any(result.added.values())
    print(f"KPI catalog {CATALOG_VERSION}: {'seeded' if changed else 'already present'}")
    for table, count in result.rows.items():
        print(f"  {table:<22}{count:>6} rows ({result.added[table]:+d})")

    if result.unconfirmed:
        print(
            f"the catalog in the database does not confirm {len(result.unconfirmed)} of the "
            f"import's {len(automatic_names())} automatic names ({', '.join(result.unconfirmed)}): "
            "their values would be held for review. An existing release is never updated by "
            "this command.",
            file=sys.stderr,
        )
        return EXIT_NOT_AS_SHIPPED
    if not result.as_shipped:
        print(
            f"the catalog in the database carries release {CATALOG_VERSION} but does not resolve "
            "names as this build's catalog does (an alias, a KPI's status or its unit differs). "
            "An existing release is never updated by this command.",
            file=sys.stderr,
        )
        return EXIT_NOT_AS_SHIPPED
    print(f"the catalog confirms the import's {len(automatic_names())} automatic names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
