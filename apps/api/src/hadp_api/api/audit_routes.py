"""The clinic's audit trail, read by the clinic (go-live plan A9).

The clinic is the controller: it answers for who accessed which record, and it has to be able
to see that without asking the platform operator. OWNER only — the trail shows every
colleague's recorded access to every record.

What a clinic sees is exactly the events recorded FOR it. Events without a tenant — a sign-in,
a failed sign-in, a sign-out, a throttled request, a denial before a clinic was selected —
belong to no clinic and are never returned here, although row-level security would let them
through (see `list_tenant_events`).

An event is meant to carry identifiers, codes, counts and timings only. That is the rule for
the code that writes one (see `modules/audit/service.py` for how far it is enforced); this
route returns `detail` as it was written. It leaves out the request's correlation id, which
is the operator's handle and not part of what a clinic reads. And it adds one thing an event
does not store: who the acting account is — its current display name and e-mail address, a
colleague of the reader in the reader's own clinic, including one who has since left it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.errors import ValidationFailed
from hadp_api.modules.audit import service as audit_service
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import AuditCategory
from hadp_api.modules.identity.models import User
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(tags=["audit"])


class AuditActorOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    email: str


class AuditEventOut(BaseModel):
    id: uuid.UUID
    # In UTC.
    occurred_at: datetime
    action: str
    # None: nobody signed in acted (the holder of a patient link, an invitation being redeemed).
    actor: AuditActorOut | None
    target_type: str | None
    target_id: uuid.UUID | None
    # As written: meant to be identifiers, codes, counts and timings only.
    detail: dict[str, Any]


class AuditPageOut(BaseModel):
    items: list[AuditEventOut]
    # Pass as `cursor` to read the next (older) page; null when nothing older is left.
    next_cursor: str | None


@router.get("/audit-events", response_model=AuditPageOut)
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=audit_service.MAX_PAGE),
    cursor: str | None = Query(default=None, max_length=200),
    category: AuditCategory | None = None,
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
    # Every read writes an event (below) into this clinic's trail, and nothing is ever removed
    # from it: this bounds what one account's reading adds to one clinic. A window in which
    # reads were refused leaves one `rate_limited` event, without tenant or actor.
    check_rate_limit(
        action="audit.read",
        key=f"{ctx.tenant_id}:{ctx.user.id}",
        limit=120,
        window_seconds=60,
        correlation_id=ctx.correlation_id,
    )
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
    # Reading the trail is itself on the trail: which filters were set. Of their values only
    # the category, which is one of a closed set — never an id or a time.
    record_audit(
        ctx.db,
        action="audit.read",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        correlation_id=ctx.correlation_id,
        detail={
            "count": len(page.events),
            "category": category.value if category else None,
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
                occurred_at=e.created_at.astimezone(UTC),
                action=e.action,
                actor=actors.get(e.actor_user_id) if e.actor_user_id is not None else None,
                target_type=e.target_type,
                target_id=e.target_id,
                detail=e.detail,
            )
            for e in page.events
        ],
        next_cursor=page.next_cursor,
    )
