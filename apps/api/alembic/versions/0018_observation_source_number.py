"""observations.numeric_value holds the source's value as a number, in the source's unit.

Until now the column was written with the NORMALIZED value: NULL for every value the
terminology did not know or whose unit had no approved conversion — such a value showed as
"—" although the source had written a number — and, for a converted value, the converted
number rather than the source's.

From normalization version norm-2 the import writes the source's number here, and the read
side shows it (with the source's unit) wherever no normalized value exists. This migration
brings the stored rows to the same meaning: `numeric_value` is the number in `original_value`
when that is a plain decimal number, else NULL. Nothing is inferred — `original_value` is the
immutable source representation, read with the grammar the import itself uses.

Not recoverable for stored rows: their reference bounds. An un-normalized row was stored
without `reference_low`/`reference_high` (only `reference_text` kept what the source wrote);
it shows its number without an interval until it is imported again.

Revision ID: 0018_observation_source_number
Revises: 0017_report_rejection_reason
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_observation_source_number"
down_revision = "0017_report_rejection_reason"
branch_labels = None
depends_on = None

# The import's number grammar (modules/imports/normalize.py `_NUMBER`): ASCII digits, an optional
# sign, "." or "," as the decimal separator, an optional exponent of at most two digits.
PLAIN_NUMBER = r"^[+-]?([0-9]+([.,][0-9]*)?|[.,][0-9]+)([eE][+-]?[0-9]{1,2})?$"
_TRIMMED = r"btrim(original_value, E' \t\n\r\f\v')"

BACKFILL = sa.text(
    f"""
    UPDATE observations
       SET numeric_value = CASE
               WHEN {_TRIMMED} ~ :plain_number
               THEN replace({_TRIMMED}, ',', '.')::numeric
           END
    """
).bindparams(plain_number=PLAIN_NUMBER)


def upgrade() -> None:
    op.execute(BACKFILL)


def downgrade() -> None:
    # The former meaning: the normalized value (NULL where none exists).
    op.execute("UPDATE observations SET numeric_value = normalized_value")
