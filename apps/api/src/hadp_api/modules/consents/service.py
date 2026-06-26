"""Consent application service — the public boundary other modules call.

Consent is an append-only event stream (`ConsentEvent`): a grant and a withdrawal are each a NEW
row; current state for a (patient, purpose) is the latest event by `recorded_at`.
`has_active_consent` is the gate other modules (e.g. report release) consult; it is fail-closed
(no event => not active).
Withdrawal additionally revokes any live patient access links for that patient in the same
transaction, so existing access stops the moment consent is withdrawn.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.enums import ConsentEventType, ConsentPurpose

# Synthetic-Alpha consent text version. The real, counsel-authored consent text + versioning is a
# DPO/counsel deliverable (PENDING) — this is a placeholder for the synthetic demo only.
SYNTHETIC_CONSENT_TEXT_VERSION = "synthetic-v1"


def _latest_event(
    db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID, purpose: ConsentPurpose
) -> ConsentEvent | None:
    return db.execute(
        select(ConsentEvent)
        .where(
            ConsentEvent.tenant_id == tenant_id,
            ConsentEvent.patient_id == patient_id,
            ConsentEvent.purpose == purpose,
        )
        .order_by(ConsentEvent.recorded_at.desc(), ConsentEvent.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def has_active_consent(
    db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID, purpose: ConsentPurpose
) -> bool:
    """True iff the latest consent event for (patient, purpose) is a grant. Fail-closed."""
    latest = _latest_event(db, tenant_id=tenant_id, patient_id=patient_id, purpose=purpose)
    return latest is not None and latest.event_type == ConsentEventType.GRANTED


def record_consent(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    purpose: ConsentPurpose,
    channel: str,
    recorded_by_user_id: uuid.UUID | None,
    consent_text_version: str = SYNTHETIC_CONSENT_TEXT_VERSION,
) -> ConsentEvent:
    """Append a GRANTED consent event."""
    event = ConsentEvent(
        tenant_id=tenant_id,
        patient_id=patient_id,
        purpose=purpose,
        event_type=ConsentEventType.GRANTED,
        consent_text_version=consent_text_version,
        channel=channel,
        recorded_at=datetime.now(UTC),
        recorded_by_user_id=recorded_by_user_id,
    )
    db.add(event)
    db.flush()
    return event


def withdraw_consent(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    purpose: ConsentPurpose,
    channel: str,
    recorded_by_user_id: uuid.UUID | None,
    consent_text_version: str = SYNTHETIC_CONSENT_TEXT_VERSION,
) -> ConsentEvent:
    """Append a WITHDRAWN event AND revoke live patient access links in the SAME transaction.

    Withdrawal never mutates the prior grant (append-only). When `report_release` consent is
    withdrawn, existing patient access links are revoked so any released report immediately becomes
    inaccessible; a new release is blocked by the release gate (`has_active_consent`).
    """
    event = ConsentEvent(
        tenant_id=tenant_id,
        patient_id=patient_id,
        purpose=purpose,
        event_type=ConsentEventType.WITHDRAWN,
        consent_text_version=consent_text_version,
        channel=channel,
        recorded_at=datetime.now(UTC),
        recorded_by_user_id=recorded_by_user_id,
    )
    db.add(event)
    db.flush()

    if purpose == ConsentPurpose.REPORT_RELEASE:
        # Local import avoids a circular import (reports.service imports this module for the gate).
        from hadp_api.modules.reports import service as reports_service

        reports_service.revoke_all_patient_links(db, tenant_id=tenant_id, patient_id=patient_id)
    return event
