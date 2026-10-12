"""The clinic's audit trail, read by the clinic (go-live plan A9).

The clinic is the controller: it answers for who accessed which record, and it has to be able
to see that without asking the platform operator. OWNER only — the trail shows every
colleague's access to every record.

What a clinic sees is exactly the events recorded FOR it. Events without a tenant — a sign-in,
a failed sign-in, a denial before a clinic was selected — belong to no clinic and are never
returned here, although row-level security would let them through (see `list_tenant_events`).

An event carries identifiers, codes and timings only; that is enforced where events are
written (`record_audit` refuses a detail key such as `value`, `name` or `email`). This route
adds one thing an event does not store: who the acting user is, by name — a colleague of the
reader, in the reader's own clinic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.errors import ValidationFailed
from hadp_api.modules.audit import service as audit_service
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.identity.models import User

router = APIRouter(tags=["audit"])


class AuditActorOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    email: str


class AuditEventOut(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    action: str
    # None: nobody signed in acted (a patient opening a link, a job), or the account is gone.
    actor: AuditActorOut | None
    target_type: str | None
    target_id: uuid.UUID | None
    correlation_id: str | None
    # Identifiers, codes, counts and timings only.
    detail: dict[str, Any]


class AuditPageOut(BaseModel):
    items: list[AuditEventOut]
    # Pass as `cursor` to read the next (older) page; null when nothing older is left.
    next_cursor: str | None


@router.get("/audit-events", response_model=AuditPageOut)
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=audit_service.MAX_PAGE),
    cursor: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, pattern=r"^[a-z_]{1,40}$"),
    actor_user_id: uuid.UUID | None = None,
    target_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    exclude_reads: bool = False,
    ctx: TenantContext = Depends(require(Action.AUDIT_READ)),
) -> AuditPageOut:
    for bound in (since, until):
        if bound is not None and bound.tzinfo is None:
            raise ValidationFailed("since / until must carry a UTC offset")
    page = audit_service.list_tenant_events(
        ctx.db,
        tenant_id=ctx.tenant_id,
        limit=limit,
        cursor=cursor,
        category=category,
        actor_user_id=actor_user_id,
        target_id=target_id,
        since=since,
        until=until,
        exclude_reads=exclude_reads,
    )
    actor_ids = {e.actor_user_id for e in page.events if e.actor_user_id is not None}
    actors = (
        {
            user.id: AuditActorOut(
                user_id=user.id, display_name=user.display_name, email=user.email
            )
            for user in ctx.db.execute(select(User).where(User.id.in_(actor_ids))).scalars()
        }
        if actor_ids
        else {}
    )
    # Reading the trail is itself on the trail. Which filters were set, never their values.
    record_audit(
        ctx.db,
        action="audit.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={
            "count": len(page.events),
            "category": category,
            "by_actor": actor_user_id is not None,
            "by_target": target_id is not None,
            "by_time": since is not None or until is not None,
            "exclude_reads": exclude_reads,
            "continued": cursor is not None,
        },
    )
    return AuditPageOut(
        items=[
            AuditEventOut(
                id=e.id,
                occurred_at=e.created_at,
                action=e.action,
                actor=actors.get(e.actor_user_id) if e.actor_user_id is not None else None,
                target_type=e.target_type,
                target_id=e.target_id,
                correlation_id=e.correlation_id,
                detail=e.detail,
            )
            for e in page.events
        ],
        next_cursor=page.next_cursor,
    )
