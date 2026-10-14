"""The clinic's address, as its owner writes it.

Shown to the clinic's staff under Einstellungen › Praxisprofil and to a patient beneath the
report they were given access to, so they know which practice released it. Free text of at
most 300 characters; optional. The clinic is the controller of this record — it is not patient
data.

Revision ID: 0022_tenant_address
Revises: 0021_staff_invitation_label
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022_tenant_address"
down_revision = "0021_staff_invitation_label"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("address", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "address")
