"""How long reports take from their first draft to an approval that stood.

A public service of the reports module (the metrics module reads report timing through it and
never queries these tables itself). Durations and counts only — nothing of a report's content.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from hadp_api.modules.reports.models import Report, ReportVersion


@dataclass(frozen=True)
class IntervalStats:
    reports: int
    # None when no report falls in the window.
    q1_seconds: float | None
    median_seconds: float | None
    q3_seconds: float | None


def draft_to_approval(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    until: datetime,
    windows: Sequence[datetime | None],
) -> list[IntervalStats]:
    """Per window `[since, until)` (`since` None: no lower bound): the reports whose first
    STANDING approval falls in it, and the quartiles of their draft-to-approval time.

    One value per report: from the creation of the report (its first draft) to the earliest
    approval that was not refused afterwards. An approval the medical director refused at the
    release gate, or the clinician withdrew, did not end the work on the report — the version
    carries both `approved_at` and `rejected_at`, and is left out. A report approved again
    later (after an edit or a laboratory correction) counts once, at the first such approval;
    a report without one does not count.

    All windows are read in ONE statement, so they describe the same moment: a report cannot
    be in the narrower window and missing from the wider one. A negative interval (the two
    timestamps come from two clocks: the database's for the draft, the application's for the
    approval) counts as zero.
    """
    standing = (
        select(
            Report.created_at.label("drafted_at"),
            func.min(ReportVersion.approved_at).label("approved_at"),
        )
        .join(ReportVersion, ReportVersion.report_id == Report.id)
        .where(
            Report.tenant_id == tenant_id,
            ReportVersion.tenant_id == tenant_id,
            ReportVersion.approved_at.is_not(None),
            ReportVersion.rejected_at.is_(None),
        )
        .group_by(Report.id, Report.created_at)
        .subquery()
    )
    seconds = func.greatest(
        func.extract("epoch", standing.c.approved_at - standing.c.drafted_at), 0
    )
    columns = []
    for since in windows:
        inside = standing.c.approved_at < until
        if since is not None:
            inside = and_(standing.c.approved_at >= since, inside)
        # NULL outside the window: count() and percentile_cont() both ignore NULLs.
        value = case((inside, seconds))
        columns += [
            func.count(value),
            func.percentile_cont(0.25).within_group(value),
            func.percentile_cont(0.5).within_group(value),
            func.percentile_cont(0.75).within_group(value),
        ]
    row = db.execute(select(*columns)).one()
    return [
        IntervalStats(
            reports=row[i],
            q1_seconds=None if row[i + 1] is None else float(row[i + 1]),
            median_seconds=None if row[i + 2] is None else float(row[i + 2]),
            q3_seconds=None if row[i + 3] is None else float(row[i + 3]),
        )
        for i in range(0, len(columns), 4)
    ]
