"""What the clinic's data has come in through: one line per laboratory file reader, and one for
everything else (values entered by hand or sent through the API).

Counts and times of import jobs only — no value, no patient. The readers are the ones this
code ships (`parsers/`); a reader the clinic has not used yet is still listed, with nothing
read.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.modules.imports.models import ImportJob, ImportRow
from hadp_api.modules.imports.parsers import csv_reader, ldt2_reader, ldt3_reader

# The file readers, in the order a clinic page lists them.
READERS: tuple[str, ...] = (
    csv_reader.PARSER_NAME,
    ldt2_reader.PARSER_NAME,
    ldt3_reader.PARSER_NAME,
)


@dataclass
class SourceLine:
    # A reader's name, or None for everything that did not come through a file reader.
    parser_name: str | None
    jobs: int
    rows: int
    last_import_at: datetime | None


def source_summary(db: Session, tenant_id: uuid.UUID) -> list[SourceLine]:
    """One line per reader in READERS, then one for every other way in."""
    job_rows = db.execute(
        select(ImportJob.parser_name, func.count(), func.max(ImportJob.created_at))
        .where(ImportJob.tenant_id == tenant_id)
        .group_by(ImportJob.parser_name)
    ).all()
    row_counts = db.execute(
        select(ImportJob.parser_name, func.count(ImportRow.id))
        .join(ImportRow, ImportRow.import_job_id == ImportJob.id)
        .where(ImportJob.tenant_id == tenant_id)
        .group_by(ImportJob.parser_name)
    ).all()
    rows_by_name: dict[str, int] = {name: int(n) for name, n in row_counts}

    lines = {name: SourceLine(name, 0, 0, None) for name in READERS}
    other = SourceLine(None, 0, 0, None)
    for name, jobs, last in job_rows:
        line = lines.get(name, other)
        line.jobs += int(jobs)
        line.rows += rows_by_name.get(name, 0)
        if last is not None and (line.last_import_at is None or last > line.last_import_at):
            line.last_import_at = last
    return [*lines.values(), other]
