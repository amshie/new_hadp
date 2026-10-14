"""A label for a team invitation, as the owner wrote it.

An owner inviting a colleague may note whom the link is for — usually an e-mail address — so
the open invitations can be told apart. The label is shown to the clinic's owners only; the
link is never sent to it, and the invited person still chooses their own name and address
when they redeem the link. It is optional and never part of an audit event.

Revision ID: 0021_staff_invitation_label
Revises: 0020_erasure_fn_search_path
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_staff_invitation_label"
down_revision = "0020_erasure_fn_search_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff_invitations", sa.Column("label", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("staff_invitations", "label")
