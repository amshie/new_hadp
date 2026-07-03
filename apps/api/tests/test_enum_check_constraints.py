"""Every closed-vocabulary enum column is DB-enforced by a CHECK constraint.

docs/notes/0006 follow-up: SQLAlchemy's native_enum=False creates no CHECK, so migrations
0009 (memberships.role), 0013 (staff_invitations.role) and 0014 (the rest) add them
explicitly. This guards the invariant and would fail if a future enum column shipped without
one.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import hadp_api.modules  # noqa: F401  registers models
from hadp_api.db.base import Base
from tests.helpers import make_tenant

_CHECK_DEFS_SQL = text(
    """
    SELECT rel.relname AS tbl, pg_get_constraintdef(con.oid) AS def
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace n ON n.oid = rel.relnamespace
    WHERE con.contype = 'c' AND n.nspname = 'public'
    """
)


def _enum_columns() -> set[tuple[str, str]]:
    return {
        (t.name, c.name)
        for t in Base.metadata.sorted_tables
        for c in t.columns
        if isinstance(c.type, SAEnum) and getattr(c.type, "native_enum", True) is False
    }


def test_every_enum_column_is_db_enforced(admin_session) -> None:  # type: ignore[no-untyped-def]
    checks = admin_session.execute(_CHECK_DEFS_SQL).all()

    def covered(table: str, column: str) -> bool:
        # pg_get_constraintdef renders the column as e.g. "(status)::text = ANY (...)".
        return any(rel == table and f"({column})::text" in definition for rel, definition in checks)

    missing = sorted((t, c) for (t, c) in _enum_columns() if not covered(t, c))
    assert not missing, f"enum columns without a DB CHECK constraint: {missing}"


def test_enum_check_rejects_out_of_vocabulary_value(admin_session) -> None:  # type: ignore[no-untyped-def]
    tenant = make_tenant(admin_session, name="Enum Check", slug="enum-check")
    admin_session.flush()
    # role is valid; status is outside the closed vocabulary -> the DB CHECK must reject it.
    with pytest.raises(IntegrityError):
        admin_session.execute(
            text(
                "INSERT INTO staff_invitations "
                "(tenant_id, role, token_hash, status, expires_at) "
                "VALUES (:t, 'clinician', :tok, 'NOT_A_REAL_STATUS', :exp)"
            ),
            {"t": tenant.id, "tok": "e" * 64, "exp": datetime.now(UTC)},
        )
    admin_session.rollback()
