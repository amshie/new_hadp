"""Review-item resolution timestamp: resolved_at on review_items.

Review-queue resolution ships (Phase 1C): resolution gets the same first-class
attribution as approval/rejection — the actor column already existed
(resolved_by_user_id); this adds the timestamp.

Revision ID: 0011_review_item_resolved_at
Revises: 0010_report_rejection
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_review_item_resolved_at"
down_revision = "0010_report_rejection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_items",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_items", "resolved_at")
