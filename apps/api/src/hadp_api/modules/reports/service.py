"""Report lifecycle service.

DRAFT_GENERATED -> DRAFT_EDITED -> APPROVED -> RELEASED (or REJECTED). Invariants:
- A draft is built only from published observations; every statement is evidence-linked.
- Approval requires every statement's evidence to be viewable (else it cannot be approved).
- A report cannot be released before it is approved, nor while a statement rests on a value a
  published laboratory correction has replaced.
- Editing after approval creates a NEW version and invalidates the prior approval.
- Patients can only ever see RELEASED content, via a scoped, revocable access link.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hadp_api.auth.sessions import hash_token
from hadp_api.errors import Conflict, IntendedUseViolation, NotFound, ValidationFailed
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.enums import ConsentPurpose, ReportRejectionReason, ReportStatus
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.evidence import build_evidence_payload, validate_statements
from hadp_api.modules.reports.language import restricted_terms
from hadp_api.modules.reports.models import (
    PatientAccessLink,
    Report,
    ReportEvidence,
    ReportVersion,
)
from hadp_api.modules.reports.narrative import (
    DeterministicNarrativeProvider,
    DraftStatement,
    NarrativeProvider,
)

_DRAFT_STATES = {ReportStatus.DRAFT_GENERATED, ReportStatus.DRAFT_EDITED}
PATIENT_LINK_TTL = timedelta(days=14)


def _stmt_dict(statement: DraftStatement) -> dict[str, Any]:
    return {
        "id": statement.id,
        "text": statement.text,
        "evidence_observation_ids": [str(i) for i in statement.evidence_observation_ids],
    }


def latest_reports_by_patient(db: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, Report]:
    """Latest report per patient for the tenant (RLS-scoped). Public read for the worklist."""
    rows = (
        db.execute(
            select(Report)
            .where(Report.tenant_id == tenant_id)
            .order_by(Report.patient_id, Report.created_at.desc())
        )
        .scalars()
        .all()
    )
    latest: dict[uuid.UUID, Report] = {}
    for report in rows:
        latest.setdefault(report.patient_id, report)  # first seen = newest (desc order)
    return latest


def version_no_for(db: Session, report: Report) -> int | None:
    version = current_version_for(db, report)
    return version.version_no if version else None


def current_version_for(db: Session, report: Report) -> ReportVersion | None:
    if report.current_version_id is None:
        return None
    return db.get(ReportVersion, report.current_version_id)


def status_reached_at(version: ReportVersion) -> datetime:
    """When the version reached the status it holds: released, approved or rejected at that
    moment; a draft when it was written."""
    if version.status == ReportStatus.RELEASED and version.released_at is not None:
        return version.released_at
    if version.status == ReportStatus.APPROVED and version.approved_at is not None:
        return version.approved_at
    if version.status == ReportStatus.REJECTED and version.rejected_at is not None:
        return version.rejected_at
    return version.created_at


def version_stepped_by(version: ReportVersion, user_id: uuid.UUID) -> bool:
    """Whether this person took the step that brought the version to the status it holds —
    generated or edited the draft, approved it, rejected it. A release carries no account on
    the version (the trail holds it), so a release is never counted as the person's own."""
    if version.status == ReportStatus.APPROVED:
        return version.approved_by_user_id == user_id
    if version.status == ReportStatus.REJECTED:
        return version.rejected_by_user_id == user_id
    if version.status == ReportStatus.DRAFT_EDITED:
        return version.edited_by_user_id == user_id
    if version.status == ReportStatus.DRAFT_GENERATED:
        return version.generated_by_user_id == user_id
    return False


@dataclass
class ThroughputBucket:
    day: date
    created: int  # report versions created that day (a "draft" produced)
    signed: int  # report versions whose clinician approval (sign-off) landed that day
    released: int = 0  # report versions the medical director released that day


@dataclass
class ThroughputSummary:
    days: int
    buckets: list[ThroughputBucket]
    total_created: int
    total_signed: int
    total_released: int = 0


def throughput_daily(db: Session, tenant_id: uuid.UUID, days: int) -> ThroughputSummary:
    """Real per-day report-version throughput for the dashboard "Review-Durchsatz" chart.

    "Erstellt" = report versions by `created_at` day; "Signiert" = report versions by
    `approved_at` day (the clinician sign-off timestamp); "Freigegeben" = report versions by
    `released_at` day (the medical director's release). All three are REAL persisted timestamps —
    no fabricated rate. Tenant-scoped (explicit filter + RLS defense-in-depth). Days are bucketed
    by **UTC calendar day** — pinned via `timezone('UTC', ...)` so the grouping matches the UTC
    window below regardless of the DB session time zone. Zero-activity days are present so the
    series has no gaps.
    """
    days = max(1, min(days, 90))
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    start_dt = datetime(start.year, start.month, start.day, tzinfo=UTC)

    # `date(timestamptz)` truncates in the *session* time zone; pin to UTC so a near-midnight
    # version cannot land in a neighbouring local-day bucket and miss the UTC-keyed window.
    created_day = func.date(func.timezone("UTC", ReportVersion.created_at))
    signed_day = func.date(func.timezone("UTC", ReportVersion.approved_at))
    created_rows = db.execute(
        select(created_day, func.count())
        .where(
            ReportVersion.tenant_id == tenant_id,
            ReportVersion.created_at >= start_dt,
        )
        .group_by(created_day)
    ).all()
    signed_rows = db.execute(
        select(signed_day, func.count())
        .where(
            ReportVersion.tenant_id == tenant_id,
            ReportVersion.approved_at.is_not(None),
            ReportVersion.approved_at >= start_dt,
        )
        .group_by(signed_day)
    ).all()
    released_day = func.date(func.timezone("UTC", ReportVersion.released_at))
    released_rows = db.execute(
        select(released_day, func.count())
        .where(
            ReportVersion.tenant_id == tenant_id,
            ReportVersion.released_at.is_not(None),
            ReportVersion.released_at >= start_dt,
        )
        .group_by(released_day)
    ).all()
    created_by_day: dict[date, int] = {row[0]: row[1] for row in created_rows}
    signed_by_day: dict[date, int] = {row[0]: row[1] for row in signed_rows}
    released_by_day: dict[date, int] = {row[0]: row[1] for row in released_rows}

    buckets: list[ThroughputBucket] = []
    total_created = 0
    total_signed = 0
    total_released = 0
    for i in range(days):
        d = start + timedelta(days=i)
        created = int(created_by_day.get(d, 0))
        signed = int(signed_by_day.get(d, 0))
        released = int(released_by_day.get(d, 0))
        total_created += created
        total_signed += signed
        total_released += released
        buckets.append(ThroughputBucket(day=d, created=created, signed=signed, released=released))
    return ThroughputSummary(
        days=days,
        buckets=buckets,
        total_created=total_created,
        total_signed=total_signed,
        total_released=total_released,
    )


def _get_report(db: Session, report_id: uuid.UUID, tenant_id: uuid.UUID) -> Report:
    report = db.execute(
        select(Report).where(Report.id == report_id, Report.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if report is None:
        raise NotFound("report not found")
    return report


def _current_version(db: Session, report: Report) -> ReportVersion:
    if report.current_version_id is None:
        raise NotFound("report has no current version")
    version = db.get(ReportVersion, report.current_version_id)
    if version is None:
        raise NotFound("report version not found")
    return version


def _revoke_patient_links(db: Session, report_id: uuid.UUID) -> None:
    """Revoke any outstanding patient access links for a report (idempotent)."""
    db.query(PatientAccessLink).filter(
        PatientAccessLink.report_id == report_id,
        PatientAccessLink.revoked_at.is_(None),
    ).update({PatientAccessLink.revoked_at: datetime.now(UTC)})
    db.flush()


def revoke_all_patient_links(db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    """Revoke ALL live patient access links for a patient (idempotent).

    Public seam called on consent withdrawal (consents.service.withdraw_consent): the moment
    report_release consent is withdrawn, every live link is revoked so resolve_patient_view 404s.
    Filters on tenant_id as well as patient_id (defense-in-depth on top of RLS).
    """
    db.query(PatientAccessLink).filter(
        PatientAccessLink.tenant_id == tenant_id,
        PatientAccessLink.patient_id == patient_id,
        PatientAccessLink.revoked_at.is_(None),
    ).update({PatientAccessLink.revoked_at: datetime.now(UTC)})
    db.flush()


def _create_evidence_rows(
    db: Session,
    tenant_id: uuid.UUID,
    report_version_id: uuid.UUID,
    statements: list[dict[str, Any]],
) -> None:
    for stmt in statements:
        for obs_id in stmt.get("evidence_observation_ids") or []:
            db.add(
                ReportEvidence(
                    tenant_id=tenant_id,
                    report_version_id=report_version_id,
                    statement_id=stmt["id"],
                    observation_id=uuid.UUID(str(obs_id)),
                )
            )
    db.flush()


def generate_draft(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    generated_by_user_id: uuid.UUID,
    provider: NarrativeProvider | None = None,
) -> Report:
    provider = provider or DeterministicNarrativeProvider()
    payload = build_evidence_payload(db, patient_id)
    if not payload:
        raise ValidationFailed("no published observations to report")
    statements = [_stmt_dict(s) for s in provider.generate(payload)]
    try:
        validate_statements(db, patient_id, statements)
    except ValueError as exc:
        raise IntendedUseViolation(str(exc)) from exc

    report = Report(
        tenant_id=tenant_id,
        patient_id=patient_id,
        status=ReportStatus.DRAFT_GENERATED,
        created_by_user_id=generated_by_user_id,
    )
    db.add(report)
    db.flush()
    version = ReportVersion(
        tenant_id=tenant_id,
        report_id=report.id,
        version_no=1,
        status=ReportStatus.DRAFT_GENERATED,
        body={"statements": statements},
        narrative_provider=provider.name,
        narrative_version=provider.version,
        generated_by_user_id=generated_by_user_id,
    )
    db.add(version)
    db.flush()
    report.current_version_id = version.id
    _create_evidence_rows(db, tenant_id, version.id, statements)
    db.flush()
    return report


def edit_report(
    db: Session,
    *,
    report_id: uuid.UUID,
    tenant_id: uuid.UUID,
    statements: list[dict[str, Any]],
    edited_by_user_id: uuid.UUID,
) -> ReportVersion:
    report = _get_report(db, report_id, tenant_id)
    try:
        validate_statements(db, report.patient_id, statements)
    except ValueError as exc:
        raise IntendedUseViolation(str(exc)) from exc
    # An edit is free text bound for a patient-facing report: the restricted intended-use
    # terms are refused at write time. The detail names the matched terms, never the text.
    restricted = restricted_terms(str(s.get("text", "")) for s in statements)
    if restricted:
        raise IntendedUseViolation(
            f"restricted language in statement text: {', '.join(restricted)}"
        )

    current = _current_version(db, report)
    if current.status in {ReportStatus.APPROVED, ReportStatus.RELEASED, ReportStatus.REJECTED}:
        # Editing after approval creates a NEW version; the prior approval no longer applies.
        # A REJECTED version is likewise a preserved record — never mutated back into a draft.
        # If the report was released, retract patient access until re-approval + re-release.
        if current.status == ReportStatus.RELEASED:
            _revoke_patient_links(db, report.id)
        new_version = ReportVersion(
            tenant_id=tenant_id,
            report_id=report.id,
            version_no=current.version_no + 1,
            status=ReportStatus.DRAFT_EDITED,
            body={"statements": statements},
            narrative_provider=current.narrative_provider,
            narrative_version=current.narrative_version,
            edited_by_user_id=edited_by_user_id,
        )
        db.add(new_version)
        db.flush()
        report.current_version_id = new_version.id
        report.status = ReportStatus.DRAFT_EDITED
        _create_evidence_rows(db, tenant_id, new_version.id, statements)
        db.flush()
        return new_version

    # Still a draft: update in place.
    current.status = ReportStatus.DRAFT_EDITED
    current.body = {"statements": statements}
    current.edited_by_user_id = edited_by_user_id
    db.query(ReportEvidence).filter(ReportEvidence.report_version_id == current.id).delete()
    _create_evidence_rows(db, tenant_id, current.id, statements)
    report.status = ReportStatus.DRAFT_EDITED
    db.flush()
    return current


def cites_replaced_evidence(db: Session, report: Report, version: ReportVersion) -> bool:
    """The version cites a value that no longer stands (a laboratory correction replaced it)."""
    cited = {
        uuid.UUID(str(i))
        for stmt in version.body.get("statements", [])
        for i in stmt.get("evidence_observation_ids") or []
    }
    return bool(cited & obs_service.not_standing(db, report.patient_id))


def redraft_report(
    db: Session,
    *,
    report_id: uuid.UUID,
    tenant_id: uuid.UUID,
    generated_by_user_id: uuid.UUID,
    provider: NarrativeProvider | None = None,
) -> tuple[ReportVersion, bool]:
    """Open a NEW version built from the values that stand. Returns (version, retracted).

    The way on once a laboratory correction has replaced a cited value: an edit can only
    remove the affected statement, it cannot bring the corrected value in. Offered for that
    case only — a report whose evidence still stands is revised by editing. The prior version
    stays a preserved record. If it was released, patient access is withdrawn until the new
    version is approved and released again, exactly as with an edit after release.
    """
    report = _get_report(db, report_id, tenant_id)
    current = _current_version(db, report)
    if not cites_replaced_evidence(db, report, current):
        raise Conflict("redraft_not_needed: every cited value still stands")
    provider = provider or DeterministicNarrativeProvider()
    payload = build_evidence_payload(db, report.patient_id)
    if not payload:
        raise ValidationFailed("no published observations to report")
    statements = [_stmt_dict(s) for s in provider.generate(payload)]
    try:
        validate_statements(db, report.patient_id, statements)
    except ValueError as exc:
        raise IntendedUseViolation(str(exc)) from exc

    retracted = current.status == ReportStatus.RELEASED
    if retracted:
        _revoke_patient_links(db, report.id)
    version = ReportVersion(
        tenant_id=tenant_id,
        report_id=report.id,
        version_no=current.version_no + 1,
        status=ReportStatus.DRAFT_GENERATED,
        body={"statements": statements},
        narrative_provider=provider.name,
        narrative_version=provider.version,
        generated_by_user_id=generated_by_user_id,
    )
    db.add(version)
    db.flush()
    report.current_version_id = version.id
    report.status = ReportStatus.DRAFT_GENERATED
    _create_evidence_rows(db, tenant_id, version.id, statements)
    db.flush()
    return version, retracted


def approve_report(
    db: Session, *, report_id: uuid.UUID, tenant_id: uuid.UUID, approved_by_user_id: uuid.UUID
) -> ReportVersion:
    report = _get_report(db, report_id, tenant_id)
    version = _current_version(db, report)
    if version.status not in _DRAFT_STATES:
        raise Conflict("report is not in a draft state")
    statements = version.body.get("statements", [])
    # Meaningful approval: every statement's evidence must be viewable, or approval fails.
    try:
        validate_statements(db, report.patient_id, statements)
    except ValueError as exc:
        raise IntendedUseViolation(f"cannot approve: {exc}") from exc

    version.status = ReportStatus.APPROVED
    version.approved_by_user_id = approved_by_user_id
    version.approved_at = datetime.now(UTC)
    report.status = ReportStatus.APPROVED
    db.flush()
    return version


def release_report(
    db: Session, *, report_id: uuid.UUID, tenant_id: uuid.UUID, released_by_user_id: uuid.UUID
) -> tuple[Report, str]:
    report = _get_report(db, report_id, tenant_id)
    version = _current_version(db, report)
    if version.status != ReportStatus.APPROVED:
        raise Conflict("report must be approved before release")
    # The laboratory may have corrected a cited value since approval: a statement that rests
    # on a replaced value is not released. The way on is a rejection and a rework.
    try:
        validate_statements(db, report.patient_id, version.body.get("statements", []))
    except ValueError as exc:
        raise IntendedUseViolation(f"cannot release: {exc}") from exc
    # Consent gate (fail-closed): a patient-facing release requires an ACTIVE consent for the
    # report_release purpose. Checked AFTER the approval invariant so an unapproved report still
    # reports the approval error first.
    if not consents_service.has_active_consent(
        db,
        tenant_id=tenant_id,
        patient_id=report.patient_id,
        purpose=ConsentPurpose.REPORT_RELEASE,
    ):
        raise Conflict("active patient consent (report_release) is required before release")

    version.status = ReportStatus.RELEASED
    version.released_at = datetime.now(UTC)
    report.status = ReportStatus.RELEASED

    # Re-release supersedes any earlier link for this report.
    _revoke_patient_links(db, report.id)
    raw_token = secrets.token_urlsafe(32)
    link = PatientAccessLink(
        tenant_id=tenant_id,
        patient_id=report.patient_id,
        report_id=report.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + PATIENT_LINK_TTL,
    )
    db.add(link)
    db.flush()
    return report, raw_token


def reject_report(
    db: Session,
    *,
    report_id: uuid.UUID,
    tenant_id: uuid.UUID,
    rejected_by_user_id: uuid.UUID,
    reason: ReportRejectionReason,
) -> ReportVersion:
    """Attributable refusal of the current version (draft or approved -> REJECTED).

    A RELEASED version cannot be rejected — released content is retracted by editing
    (which revokes patient links and opens a new draft version), never re-labeled.
    Rejection is a preserved record: further work happens on a new version via edit. The
    reason (closed vocabulary) tells whoever does that work what to change.
    """
    report = _get_report(db, report_id, tenant_id)
    version = _current_version(db, report)
    if version.status == ReportStatus.RELEASED:
        raise Conflict("a released report cannot be rejected; edit it to retract and revise")
    if version.status == ReportStatus.REJECTED:
        raise Conflict("report is already rejected")
    version.status = ReportStatus.REJECTED
    version.rejected_by_user_id = rejected_by_user_id
    version.rejected_at = datetime.now(UTC)
    version.rejection_reason = reason
    report.status = ReportStatus.REJECTED
    db.flush()
    return version


def released_versions(
    db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
) -> list[tuple[Report, ReportVersion]]:
    """Every report version of the patient that WAS released (current or since revised).

    A version keeps its RELEASED status when a later version replaces it, so this is exactly
    the content that passed the release gate — never a draft or an approved-only version.
    """
    rows = db.execute(
        select(Report, ReportVersion)
        .join(ReportVersion, ReportVersion.report_id == Report.id)
        .where(
            Report.tenant_id == tenant_id,
            Report.patient_id == patient_id,
            ReportVersion.status == ReportStatus.RELEASED,
        )
        .order_by(ReportVersion.released_at, ReportVersion.version_no)
    ).tuples()
    return list(rows)


def count_reports_citing(db: Session, tenant_id: uuid.UUID, observation_id: uuid.UUID) -> int:
    """How many reports cite this observation in their CURRENT version (any status)."""
    return db.execute(
        select(func.count(func.distinct(Report.id)))
        .join(ReportEvidence, ReportEvidence.report_version_id == Report.current_version_id)
        .where(Report.tenant_id == tenant_id, ReportEvidence.observation_id == observation_id)
    ).scalar_one()


def _evidence_for_statement(
    db: Session, statement: dict[str, Any], replaced: set[uuid.UUID]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for obs_id in statement.get("evidence_observation_ids") or []:
        obs = db.get(Observation, uuid.UUID(str(obs_id)))
        if obs is None:
            # Surface the gap rather than hiding it: the approval UI must show that a
            # cited observation no longer resolves (it cannot be approved as-is).
            out.append({"observation_id": str(obs_id), "missing": True})
            continue
        out.append(
            {
                "observation_id": str(obs.id),
                "original_name": obs.original_name,
                # Source representation (verbatim) and, where one exists, the normalized one.
                "original_value": obs.original_value,
                "original_unit": obs.original_unit,
                "value": obs_service.plain(obs.normalized_value),
                "unit": obs.normalized_unit,
                "observed_at": obs.observed_at.astimezone(UTC).date().isoformat()
                if obs.observed_at_is_date_only
                else obs.observed_at.isoformat(),
                "review_status": obs.review_status.value,
                # A published laboratory correction has replaced this value since it was cited.
                "superseded": obs.id in replaced,
            }
        )
    return out


def _reworked_rejection_reason(db: Session, report: Report, version: ReportVersion) -> str | None:
    """The reason of the version directly before this one, if that version was rejected."""
    previous = db.execute(
        select(ReportVersion).where(
            ReportVersion.report_id == report.id,
            ReportVersion.version_no == version.version_no - 1,
        )
    ).scalar_one_or_none()
    if previous is None or previous.status != ReportStatus.REJECTED:
        return None
    return previous.rejection_reason.value if previous.rejection_reason is not None else None


def assemble_report_view(db: Session, report: Report) -> dict[str, Any]:
    """Full view for the clinician approval UI: statements with inline evidence."""
    version = _current_version(db, report)
    statements = version.body.get("statements", [])
    replaced = obs_service.not_standing(db, report.patient_id)
    return {
        "report_id": str(report.id),
        "patient_id": str(report.patient_id),
        "status": report.status.value,
        "version_no": version.version_no,
        "narrative_provider": version.narrative_provider,
        "narrative_version": version.narrative_version,
        # Provenance of the text: a human edit means it is no longer the provider's output.
        "edited": version.edited_by_user_id is not None,
        # Why this version was rejected (closed vocabulary; null on a version that is not
        # rejected, and on one rejected before reasons were recorded).
        "rejection_reason": version.rejection_reason.value
        if version.rejection_reason is not None
        else None,
        # On a version that reworks a rejected one: why that earlier version was rejected, so
        # whoever approves or releases can check that the rework answers it.
        "reworks_rejection_reason": _reworked_rejection_reason(db, report, version),
        # A cited value no longer stands: this version cannot be approved or released, and a
        # new draft from the standing values is the way on (redraft).
        "cites_replaced_evidence": cites_replaced_evidence(db, report, version),
        "statements": [
            {
                "id": s["id"],
                "text": s["text"],
                "evidence": _evidence_for_statement(db, s, replaced),
            }
            for s in statements
        ],
    }


def resolve_patient_view(db: Session, raw_token: str) -> dict[str, Any]:
    """Patient-facing view. Returns RELEASED content only; otherwise 404 (no info leak).

    Tenant context must already be bound (from the access URL) so RLS scopes the lookup.
    """
    link = db.execute(
        select(PatientAccessLink).where(PatientAccessLink.token_hash == hash_token(raw_token))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if link is None or link.revoked_at is not None or link.expires_at <= now:
        raise NotFound("not found")
    report = db.get(Report, link.report_id)
    if report is None or report.status != ReportStatus.RELEASED:
        raise NotFound("not found")
    version = _current_version(db, report)
    if version.status != ReportStatus.RELEASED:
        raise NotFound("not found")
    statements = version.body.get("statements", [])
    return {
        "report_id": str(report.id),
        "status": report.status.value,
        "released_at": version.released_at.isoformat() if version.released_at else None,
        "synthetic": True,
        "statements": [{"id": s["id"], "text": s["text"]} for s in statements],
        "values": _patient_view_values(db, statements),
    }


def _patient_view_values(db: Session, statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The measurements the released statements cite, as the source wrote them.

    One row per cited observation, in the order the statements cite them: the source's name,
    value, unit and reference text, verbatim, and the day of sampling. Nothing is derived; a
    statement's own text already quotes these, the table only lines them up for the reader.
    An observation that no longer resolves is left out (the statement still stands as text).
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for statement in statements:
        for obs_id in statement.get("evidence_observation_ids") or []:
            key = str(obs_id)
            if key in seen:
                continue
            seen.add(key)
            obs = db.get(Observation, uuid.UUID(key))
            if obs is None:
                continue
            rows.append(
                {
                    "observation_id": key,
                    "name": obs.original_name,
                    "value": obs.original_value,
                    "unit": obs.original_unit,
                    "reference": obs.reference_text,
                    "observed_on": obs.observed_at.astimezone(UTC).date().isoformat(),
                }
            )
    return rows
