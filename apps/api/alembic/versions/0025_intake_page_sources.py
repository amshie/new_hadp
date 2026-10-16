"""Lab intake agent: where each page's text came from.

docs/product/INTAKE_AGENT.md, slice 4. OCR is an explicit step; a batch records per page whether
its text came from the text layer, from OCR, or from nowhere, so a reviewer and the evaluation
know which readings rest on OCR. Nullable: batches written before this column have no record.

Revision ID: 0025_intake_page_sources
Revises: 0024_intake_decisions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0025_intake_page_sources"
down_revision = "0024_intake_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intake_batches", sa.Column("page_sources", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("intake_batches", "page_sources")
