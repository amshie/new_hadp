"""Pin the search_path of the erasure function (SECURITY DEFINER).

`hadp_execute_patient_erasure` (0016) runs with the rights of its owner — the migrating
superuser — because the application role may not UPDATE or DELETE the append-only tables it
has to touch. It names those tables without a schema and had no search_path of its own, so
the CALLER's path decided what the names mean. A temporary schema is searched first by
default, and any role may create temporary objects: a session of the application role (a
stolen DSN, an injection) could put a table of its own in front of a real one — with a
trigger on it — and have its code run as the owner. That is the one place where the
application role could reach superuser rights.

The function now resolves its names in `pg_catalog`, then `public`, and a temporary schema
last. Its body is unchanged.

Revision ID: 0020_erasure_function_search_path
Revises: 0019_preparation_time_statements
"""

from __future__ import annotations

from alembic import op

revision = "0020_erasure_function_search_path"
down_revision = "0019_preparation_time_statements"
branch_labels = None
depends_on = None

_FUNCTION = "hadp_execute_patient_erasure(uuid, uuid)"


def upgrade() -> None:
    # `pg_temp` is named so that it comes LAST: left out, it is searched first.
    op.execute(f"ALTER FUNCTION {_FUNCTION} SET search_path = pg_catalog, public, pg_temp")


def downgrade() -> None:
    op.execute(f"ALTER FUNCTION {_FUNCTION} RESET search_path")
