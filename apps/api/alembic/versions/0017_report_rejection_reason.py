"""Why a report version was rejected: a closed-vocabulary reason on report_versions.

Whoever reworks a rejected report must know what to change. The reason is a closed vocabulary
(never free text, so neither the row nor its audit event can carry patient data), DB-enforced
like every other enum column, and only a rejected version may carry one.

Existing rejected versions keep NULL (no reason was recorded for them) — nothing is invented.

Revision ID: 0017_report_rejection_reason
Revises: 0016_erasure_redaction
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_report_rejection_reason"
down_revision = "0016_erasure_redaction"
branch_labels = None
depends_on = None

_REASONS = ["evidence_insufficient", "wording", "data_incomplete", "data_changed", "other"]


def upgrade() -> None:
    op.add_column(
        "report_versions", sa.Column("rejection_reason", sa.String(length=40), nullable=True)
    )
    allowed = ", ".join(f"'{v}'" for v in _REASONS)
    # Bare names: the metadata naming convention expands them to ck_report_versions_<name>.
    # `col IN (...)` passes on NULL, so versions without a reason stay valid.
    op.create_check_constraint(
        "rejection_reason", "report_versions", f"rejection_reason IN ({allowed})"
    )
    op.create_check_constraint(
        "rejection_reason_only_when_rejected",
        "report_versions",
        "rejection_reason IS NULL OR status = 'rejected'",
    )


def downgrade() -> None:
    op.drop_constraint("rejection_reason_only_when_rejected", "report_versions", type_="check")
    op.drop_constraint("rejection_reason", "report_versions", type_="check")
    op.drop_column("report_versions", "rejection_reason")
