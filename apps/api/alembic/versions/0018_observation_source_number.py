"""observations.numeric_value holds the source's value as a number, in the source's unit.

Until now the column was written with the NORMALIZED value: NULL for every value the import
did not normalize — such a value showed as "—" although the source had written a number —
and, for a converted value, the converted number rather than the source's.

From normalization version norm-2 the import writes the source's number here, and the read
side shows it (with the source's unit) wherever no normalized value exists. This migration
brings the stored rows to the same meaning: `numeric_value` is the number in `original_value`
when that is one number, else NULL. Nothing is inferred — `original_value` is the immutable
source representation, read with the grammar the import itself uses (a plain decimal number
that reads one way only; "4.000" and "1,250" read two ways and stay NULL).

White space around the value is removed as the import removes it, for ASCII white space.
A value padded with a non-ASCII space (a no-break space) stays NULL here although the import
would read it: the row then shows the source's wording instead of a number.

Only `numeric_value` is touched. A row normalized under norm-1 keeps the normalized value and
the bounds norm-1 gave it, also where norm-2 would not read the source that way ("4.000").

Not recoverable for stored rows: their reference bounds. An un-normalized row was stored
without `reference_low`/`reference_high` (only `reference_text` kept what the source wrote);
it shows its number without an interval until it is imported again.

`observations` is under row-level security. Run by a role that is subject to it, an UPDATE
without a tenant bound would match no row and report success. Row security is therefore
switched off for the statement: a role that may not do that fails here, loudly, instead of
leaving every row as it was — also on an empty table. Migrations are run by a superuser or a
role with BYPASSRLS (docs/adr/0001-stack.md).

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

# The import's number grammar (modules/imports/normalize.py): `_NUMBER` — ASCII digits, an
# optional sign, "." or "," as the decimal separator, an optional exponent of at most two
# digits — less `_GROUPED`, a number that reads two ways (one to three digits that are not all
# zeros, a mark, exactly three digits).
PLAIN_NUMBER = r"^[+-]?([0-9]+([.,][0-9]*)?|[.,][0-9]+)([eE][+-]?[0-9]{1,2})?$"
GROUPED_NUMBER = r"^[+-]?(?!0+[.,])[0-9]{1,3}[.,][0-9]{3}$"
# The ASCII white space Python's str.strip() removes: space, tab, line feed, vertical tab, form
# feed, carriage return and the four separators 28-31. Written with chr(): PostgreSQL's E''
# strings have no escape for the vertical tab ("\v" is the letter v).
_WHITE_SPACE = " || ".join(
    ["' '", *(f"chr({code})" for code in (9, 10, 11, 12, 13, 28, 29, 30, 31))]
)

ROW_SECURITY_OFF = "SET LOCAL row_security = off"

BACKFILL = sa.text(
    f"""
    UPDATE observations
       SET numeric_value = source.number
      FROM (
            SELECT id,
                   CASE
                       WHEN trimmed ~ :plain_number AND trimmed !~ :grouped_number
                       THEN replace(trimmed, ',', '.')::numeric
                   END AS number
              FROM (
                    SELECT id, btrim(original_value, {_WHITE_SPACE}) AS trimmed
                      FROM observations
                   ) AS read
           ) AS source
     WHERE observations.id = source.id
       AND observations.numeric_value::text IS DISTINCT FROM source.number::text
    """
).bindparams(plain_number=PLAIN_NUMBER, grouped_number=GROUPED_NUMBER)

# The former meaning: the normalized value (NULL where none exists). Reference bounds an
# un-normalized row has gained since are left in place.
RESTORE = sa.text(
    """
    UPDATE observations
       SET numeric_value = normalized_value
     WHERE numeric_value::text IS DISTINCT FROM normalized_value::text
    """
)


def upgrade() -> None:
    op.execute(ROW_SECURITY_OFF)
    op.execute(BACKFILL)


def downgrade() -> None:
    op.execute(ROW_SECURITY_OFF)
    op.execute(RESTORE)
