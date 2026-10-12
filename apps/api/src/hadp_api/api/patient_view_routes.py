"""Patient-facing view: read a RELEASED report via a scoped access link.

No staff authentication. The (non-secret) tenant id and the unguessable token are sent in
the request BODY, not the URL — so the patient bearer token never lands in a query string,
browser history, referrer, or an intermediary access log. Tenant context is bound from the
body so RLS scopes the lookup; only the unguessable token grants access. Returns RELEASED
content only. Anonymous (no session cookie), so it is not subject to the CSRF guard.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hadp_api.db.engine import set_tenant_context
from hadp_api.db.session import RequestSession
from hadp_api.errors import NotFound
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.reports import service as reports_service
from hadp_api.security.rate_limit import check_rate_limit

router = APIRouter(tags=["patient-view"])


class PatientViewRequest(BaseModel):
    tenant: uuid.UUID
    token: str


@router.post("/patient-view")
def patient_view(
    body: PatientViewRequest,
    request: Request,
    db: Session = RequestSession,
) -> dict[str, Any]:
    # The token surface is public and brute-forceable — throttle per client IP
    # (P-pre-1) before touching the database.
    check_rate_limit(
        action="patient_view",
        key=request.client.host if request.client else "unknown",
        limit=30,
        window_seconds=60,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    # Bind tenant scope from the body (non-secret); the token is the actual credential.
    set_tenant_context(db, body.tenant)
    try:
        view = reports_service.resolve_patient_view(db, body.token)
    except NotFound:
        # Audit denied/failed access (independent transaction; survives request rollback).
        record_security_event(
            action="report.patient_view_denied",
            tenant_id=body.tenant,
            detail={"reason": "not_found"},
        )
        raise
    record_audit(
        db,
        action="report.patient_view",
        tenant_id=body.tenant,
        target_type="report",
        target_id=uuid.UUID(view["report_id"]),
        detail={"status": view["status"]},
    )
    return view
