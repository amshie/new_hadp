"""Invitation service: mint, revoke, and redeem the single-use consent credential.

Redemption is the patient-side half of the P0 consent gate: on success — in ONE
transaction — a GRANTED report_release consent event is appended (channel
`synthetic_invite_redeem`, `recorded_by_user_id` NULL: there is no patient principal;
attribution rests on the single-use token identity + timestamp, which counsel must
confirm before any real-patient use) and the invitation is marked redeemed.
Every failure mode (unknown, expired, revoked, already redeemed) resolves to the SAME
NotFound — no oracle distinguishes them.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.auth.sessions import hash_token
from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.enums import ConsentPurpose, InvitationStatus
from hadp_api.modules.invitations.models import PatientInvitation

INVITATION_TTL = timedelta(days=7)
REDEEM_CHANNEL = "synthetic_invite_redeem"


def create_invitation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
) -> tuple[PatientInvitation, str]:
    """Mint a single-use invitation; the raw token exists only in the return value."""
    raw_token = secrets.token_urlsafe(32)
    invitation = PatientInvitation(
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=created_by_user_id,
        token_hash=hash_token(raw_token),
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + INVITATION_TTL,
        is_synthetic=True,
    )
    db.add(invitation)
    db.flush()
    return invitation, raw_token


def revoke_invitation(
    db: Session, *, tenant_id: uuid.UUID, invitation_id: uuid.UUID
) -> PatientInvitation:
    invitation = db.execute(
        select(PatientInvitation).where(
            PatientInvitation.id == invitation_id,
            PatientInvitation.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise NotFound("invitation not found")
    if invitation.status != InvitationStatus.PENDING:
        raise Conflict("invitation is no longer pending")
    invitation.status = InvitationStatus.REVOKED
    invitation.revoked_at = datetime.now(UTC)
    db.flush()
    return invitation


def redeem_invitation(db: Session, *, tenant_id: uuid.UUID, raw_token: str) -> PatientInvitation:
    """Redeem (single-use) and append the GRANTED consent event in the same transaction.

    Fail-closed: every non-redeemable state is the same NotFound."""
    invitation = db.execute(
        select(PatientInvitation).where(
            PatientInvitation.tenant_id == tenant_id,
            PatientInvitation.token_hash == hash_token(raw_token),
        )
    ).scalar_one_or_none()
    if (
        invitation is None
        or invitation.status != InvitationStatus.PENDING
        or invitation.expires_at <= datetime.now(UTC)
    ):
        raise NotFound("invitation not found")

    consents_service.record_consent(
        db,
        tenant_id=tenant_id,
        patient_id=invitation.patient_id,
        purpose=ConsentPurpose.REPORT_RELEASE,
        channel=REDEEM_CHANNEL,
        recorded_by_user_id=None,
    )
    invitation.status = InvitationStatus.REDEEMED
    invitation.redeemed_at = datetime.now(UTC)
    db.flush()
    return invitation
