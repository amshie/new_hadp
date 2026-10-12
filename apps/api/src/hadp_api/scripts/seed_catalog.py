"""Load the KPI catalog — and nothing else.

The laboratory import looks every name up in the catalog (ADR-0004 §18). This is the seeding
step of a deployment: it writes the catalog's reference tables and no other table, so — unlike
`hadp_api.scripts.seed`, which creates synthetic clinics, staff and patients and refuses to run
in production — it may run against any environment.

It connects with the admin DSN (`DATABASE_URL`), as Alembic does: the application role can
only read the catalog (migration 0004).

Idempotent. A release that is already in the database is left exactly as it is
(`seed_kpi_catalog` never updates one), and a second run adds no row.

Afterwards the catalog in the database is held against the import. Where it does not confirm
the names the import acts on without a human, their values would wait for review and nothing
but one log line per import would say why — so the command says it and fails.

Prints row counts only, never catalog content.
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
from hadp_api.modules.kpi.service import load_terminology, seed_kpi_catalog

# Every table this command may write.
_CATALOG_TABLES = (KpiCatalogRelease, KpiCatalog, KpiExternalCode, KpiAlias, KpiSecondaryDomain)


@dataclass(frozen=True)
class CatalogSeedResult:
    # Rows per catalog table after the run, and how many of them this run added.
    rows: dict[str, int]
    added: dict[str, int]
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
        seed_kpi_catalog(db)
        db.commit()
        rows = _row_counts(db)
        unconfirmed = unconfirmed_names(load_terminology(db))
    return CatalogSeedResult(
        rows=rows,
        added={table: rows[table] - before[table] for table in rows},
        unconfirmed=unconfirmed,
    )


def main() -> int:
    engine = create_engine(get_settings().database_url, future=True)
    try:
        result = seed_catalog(engine)
    finally:
        engine.dispose()

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
        return 1
    print(f"the catalog confirms the import's {len(automatic_names())} automatic names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
