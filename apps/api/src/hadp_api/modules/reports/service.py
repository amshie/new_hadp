"""Report lifecycle service.

DRAFT_GENERATED -> DRAFT_EDITED -> APPROVED -> RELEASED (or REJECTED). Invariants:
- A draft is built only from published observations; every statement is evidence-linked.
- Approval requires every statement's evidence to be viewable (else it cannot be approved).
- A report cannot be released before it is approved.
- Editing after approval creates a NEW version and invalidates the prior approval.
- Patients can only ever see RELEASED content, via a scoped, revocable access link.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.auth.sessions import hash_token
from hadp_api.errors import Conflict, IntendedUseViolation, NotFound, ValidationFailed
from hadp_api.modules.enums import ReportStatus
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.reports.evidence import build_evidence_payload, validate_statements
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
    if report.current_version_id is None:
        return None
    version = db.get(ReportVersion, report.current_version_id)
    return version.version_no if version else None


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

    current = _current_version(db, report)
    if current.status in {ReportStatus.APPROVED, ReportStatus.RELEASED}:
        # Editing after approval creates a NEW version; the prior approval no longer applies.
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


def _evidence_for_statement(db: Session, statement: dict[str, Any]) -> list[dict[str, Any]]:
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
                "value": str(obs.normalized_value) if obs.normalized_value is not None else None,
                "unit": obs.normalized_unit,
                "observed_at": obs.observed_at.date().isoformat()
                if obs.observed_at_is_date_only
                else obs.observed_at.isoformat(),
                "review_status": obs.review_status.value,
            }
        )
    return out


def assemble_report_view(db: Session, report: Report) -> dict[str, Any]:
    """Full view for the clinician approval UI: statements with inline evidence."""
    version = _current_version(db, report)
    statements = version.body.get("statements", [])
    return {
        "report_id": str(report.id),
        "patient_id": str(report.patient_id),
        "status": report.status.value,
        "version_no": version.version_no,
        "narrative_provider": version.narrative_provider,
        "narrative_version": version.narrative_version,
        "statements": [
            {
                "id": s["id"],
                "text": s["text"],
                "evidence": _evidence_for_statement(db, s),
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
    return {
        "report_id": str(report.id),
        "status": report.status.value,
        "released_at": version.released_at.isoformat() if version.released_at else None,
        "synthetic": True,
        "statements": [
            {"id": s["id"], "text": s["text"]} for s in version.body.get("statements", [])
        ],
    }
