"""Add the medical_director role and DB-enforce the memberships role vocabulary.

Two-tier Physician Gate (INTENDED_USE/ADR-0003): the clinician authors and approves;
a medical director locks/releases patient-facing content.

Note: SQLAlchemy 2.x creates NO CHECK constraint for `native_enum=False` enum columns
by default (`create_constraint=False`), so until this revision the role vocabulary was
enforced at the Python layer only. This migration adds the CHECK explicitly — role is
the first enum column with the closed set enforced by the database itself; extending
the same treatment to the remaining enum columns is a tracked follow-up
(docs/notes/0006-review-followups.md).

Revision ID: 0009_medical_director_role
Revises: 0008_consent_events
"""

from __future__ import annotations

from alembic import op

revision = "0009_medical_director_role"
down_revision = "0008_consent_events"
branch_labels = None
depends_on = None

_ROLES = "'owner', 'clinician', 'assistant', 'medical_director'"


def upgrade() -> None:
    # No prior CHECK exists (see docstring); existing rows all carry legacy-valid roles,
    # so creating the constraint is safe and validates them in the same statement.
    op.create_check_constraint("role", "memberships", f"role IN ({_ROLES})")


def downgrade() -> None:
    # Restores the pre-0009 state: no DB-level CHECK (Python-layer validation only).
    op.drop_constraint("role", "memberships", type_="check")
