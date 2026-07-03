"""Attributable report rejection: rejected_by_user_id + rejected_at on report_versions.

REJECTED becomes reachable (Gate G2 slice): a clinician may withdraw a draft or their
approval, and a medical director may refuse a release. Rejection gets the same
first-class attribution as approval (actor column + timestamp), in addition to the
audit event.

Revision ID: 0010_report_rejection
Revises: 0009_medical_director_role
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_report_rejection"
down_revision = "0009_medical_director_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_versions",
        sa.Column(
            "rejected_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "report_versions",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("report_versions", "rejected_at")
    op.drop_column("report_versions", "rejected_by_user_id")
