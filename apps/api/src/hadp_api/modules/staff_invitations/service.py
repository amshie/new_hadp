"""Staff-invitation service: mint, list, revoke, and redeem the single-use credential.

Redemption is the colleague-side half of onboarding: on success — in ONE transaction — a
User is created for the colleague (is_synthetic=True per the synthetic Alpha; is_active=True
so the dev provider can resolve them) and a Membership is added for the tenant with the ROLE
the owner fixed at invite time. The redeemer never chooses the role. Every failure mode
(unknown, expired, revoked, already redeemed) resolves to the SAME NotFound — no oracle.

Tenant boundary: every query is filtered by tenant_id explicitly AND the staff_invitations
table is RLS-scoped; the created Membership uses the invitation's own tenant_id (established
under that scope), never a value chosen by the caller.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.auth.sessions import hash_token
from hadp_api.errors import Conflict, NotFound
from hadp_api.modules.enums import InvitationStatus, Role
from hadp_api.modules.identity.models import User
from hadp_api.modules.staff_invitations.models import StaffInvitation
from hadp_api.modules.tenancy.models import Membership

INVITATION_TTL = timedelta(days=7)


def create_staff_invitation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    role: Role,
    created_by_user_id: uuid.UUID,
    label: str | None = None,
) -> tuple[StaffInvitation, str]:
    """Mint a single-use staff invitation; the raw token exists only in the return value."""
    raw_token = secrets.token_urlsafe(32)
    invitation = StaffInvitation(
        tenant_id=tenant_id,
        role=role,
        created_by_user_id=created_by_user_id,
        label=(label or "").strip() or None,
        token_hash=hash_token(raw_token),
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC) + INVITATION_TTL,
        is_synthetic=True,
    )
    db.add(invitation)
    db.flush()
    return invitation, raw_token


def list_staff_invitations(db: Session, *, tenant_id: uuid.UUID) -> list[StaffInvitation]:
    """Pending staff invitations for the tenant (explicit tenant filter + RLS scope)."""
    return list(
        db.execute(
            select(StaffInvitation)
            .where(
                StaffInvitation.tenant_id == tenant_id,
                StaffInvitation.status == InvitationStatus.PENDING,
            )
            .order_by(StaffInvitation.created_at.desc())
        )
        .scalars()
        .all()
    )


def revoke_staff_invitation(
    db: Session, *, tenant_id: uuid.UUID, invitation_id: uuid.UUID
) -> StaffInvitation:
    invitation = db.execute(
        select(StaffInvitation).where(
            StaffInvitation.id == invitation_id,
            StaffInvitation.tenant_id == tenant_id,
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


def redeem_staff_invitation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    raw_token: str,
    display_name: str,
    email: str,
) -> tuple[StaffInvitation, User, Membership]:
    """Redeem (single-use): create the colleague's User + Membership in one transaction.

    Fail-closed: every non-redeemable state is the same NotFound. The Membership's tenant and
    role come from the invitation, never from the caller.

    Single-use is enforced atomically: the invitation row is locked FOR UPDATE before the
    status is checked, so two concurrent redeems of one token cannot both provision access —
    the second waits, re-reads the now-REDEEMED row, and 404s. Without the lock, a check-then-
    write race under READ COMMITTED could mint two Users + two Memberships from one token."""
    invitation = db.execute(
        select(StaffInvitation)
        .where(
            StaffInvitation.tenant_id == tenant_id,
            StaffInvitation.token_hash == hash_token(raw_token),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if (
        invitation is None
        or invitation.status != InvitationStatus.PENDING
        or invitation.expires_at <= datetime.now(UTC)
    ):
        raise NotFound("invitation not found")

    normalized_email = email.strip().lower()
    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing is not None:
        # A taken email is just another non-redeemable outcome: the SAME neutral NotFound as
        # every other failure, so a token holder cannot probe which emails are registered
        # (cross-tenant account reuse is out of scope for this slice). The users.email unique
        # constraint is the backstop against a concurrent same-email race.
        raise NotFound("invitation not found")

    user = User(
        email=normalized_email,
        display_name=display_name.strip(),
        is_active=True,
        is_synthetic=True,
    )
    db.add(user)
    db.flush()  # assign user.id

    membership = Membership(
        tenant_id=invitation.tenant_id,
        user_id=user.id,
        role=invitation.role,
    )
    db.add(membership)

    invitation.status = InvitationStatus.REDEEMED
    invitation.redeemed_at = datetime.now(UTC)
    invitation.redeemed_user_id = user.id
    db.flush()
    return invitation, user, membership
