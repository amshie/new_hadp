"""Patient-facing view: read a RELEASED report via a scoped access link.

No staff authentication. The access URL carries the (non-secret) tenant id and the
unguessable token; tenant context is bound from the URL so RLS scopes the lookup, and
only the unguessable token grants access. Returns RELEASED content only.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from hadp_api.db.engine import set_tenant_context
from hadp_api.db.session import get_db
from hadp_api.errors import NotFound
from hadp_api.modules.audit.service import record_audit, record_security_event
from hadp_api.modules.reports import service as reports_service

router = APIRouter(tags=["patient-view"])


@router.get("/patient-view")
def patient_view(
    tenant: uuid.UUID,
    token: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Bind tenant scope from the URL (non-secret); the token is the actual credential.
    set_tenant_context(db, tenant)
    try:
        view = reports_service.resolve_patient_view(db, token)
    except NotFound:
        # Audit denied/failed access (independent transaction; survives request rollback).
        record_security_event(
            action="report.patient_view_denied",
            tenant_id=tenant,
            detail={"reason": "not_found"},
        )
        raise
    record_audit(
        db,
        action="report.patient_view",
        tenant_id=tenant,
        target_type="report",
        target_id=uuid.UUID(view["report_id"]),
        detail={"status": view["status"]},
    )
    return view
