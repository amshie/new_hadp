"""Per-tenant KPI configuration routes: an owner views and adjusts which global-catalog KPIs
are active and visible for THEIR clinic.

OWNER-only via the deny-by-default matrix (KPI_CONFIG_READ / KPI_CONFIG_WRITE), tenant-scoped
(explicit filter + RLS). The global KPI catalog is never mutated here — only the tenant's own
override rows. Writes are audited with KPI codes, booleans, and clinic reference bounds only —
the bounds are clinic CONFIGURATION (tenant thresholds), never patient data; no PII, no free text.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.enums import DomainAxis, KpiCatalogTier, KpiMeasurementClass
from hadp_api.modules.kpi_config import service as kpi_config_service

router = APIRouter(tags=["kpi-config"])


class KpiConfigOut(BaseModel):
    kpi_code: str
    display_name: str
    primary_domain_axis: DomainAxis
    tier: KpiCatalogTier
    measurement_class: KpiMeasurementClass
    catalog_default_enabled: bool
    catalog_patient_visible: bool
    catalog_clinician_visible: bool
    effective_enabled: bool
    effective_patient_visible: bool
    effective_clinician_visible: bool
    is_overridden: bool
    # Clinic-defined reference interval (fallback-only, position-only), in `canonical_unit`.
    # Exact decimals as strings (no false precision). null => no clinic reference set.
    reference_low: str | None
    reference_high: str | None
    reference_unit: str | None
    # The KPI's canonical unit — the unit a clinic reference must be entered in (null => no numeric
    # reference is possible for this KPI, e.g. a panel).
    canonical_unit: str | None


class KpiConfigUpdateIn(BaseModel):
    # Replace semantics: `enabled` is always set; each visibility field is an override value
    # or null (null = inherit the catalog). Owners cannot invent catalog entries here.
    enabled: bool
    patient_visible: bool | None = None
    clinician_visible: bool | None = None


class KpiReferenceIn(BaseModel):
    # Send exact decimals as strings to avoid float rounding. A two-sided ordered interval is
    # required; the unit is fixed to the KPI's canonical unit server-side (not client-chosen).
    reference_low: Decimal
    reference_high: Decimal


def _out(row: kpi_config_service.KpiConfigRow) -> KpiConfigOut:
    return KpiConfigOut(
        kpi_code=row.kpi_code,
        display_name=row.display_name,
        primary_domain_axis=row.primary_domain_axis,
        tier=row.tier,
        measurement_class=row.measurement_class,
        catalog_default_enabled=row.catalog_default_enabled,
        catalog_patient_visible=row.catalog_patient_visible,
        catalog_clinician_visible=row.catalog_clinician_visible,
        effective_enabled=row.effective_enabled,
        effective_patient_visible=row.effective_patient_visible,
        effective_clinician_visible=row.effective_clinician_visible,
        is_overridden=row.is_overridden,
        reference_low=None if row.reference_low is None else str(row.reference_low),
        reference_high=None if row.reference_high is None else str(row.reference_high),
        reference_unit=row.reference_unit,
        canonical_unit=row.canonical_unit,
    )


def _previous_reference_detail(
    previous: kpi_config_service.ClinicReference | None,
) -> dict[str, str | None]:
    # The replaced/removed clinic reference as exact-decimal strings (all None = none was set).
    # Settings rows are mutated/deleted in place, so the audit trail is the only place a
    # superseded interval survives — without it, past timeline markers lose their inputs.
    return {
        "previous_low": None if previous is None else str(previous.low),
        "previous_high": None if previous is None else str(previous.high),
        "previous_unit": None if previous is None else previous.unit,
    }


@router.get("/kpi-config", response_model=list[KpiConfigOut])
def list_kpi_config(
    ctx: TenantContext = Depends(require(Action.KPI_CONFIG_READ)),
) -> list[KpiConfigOut]:
    rows = kpi_config_service.list_kpi_config(ctx.db, tenant_id=ctx.tenant_id)
    return [_out(r) for r in rows]


@router.patch("/kpi-config/{kpi_code}", response_model=KpiConfigOut)
def update_kpi_config(
    kpi_code: str,
    body: KpiConfigUpdateIn,
    ctx: TenantContext = Depends(require(Action.KPI_CONFIG_WRITE)),
) -> KpiConfigOut:
    row = kpi_config_service.set_kpi_config(
        ctx.db,
        tenant_id=ctx.tenant_id,
        kpi_code=kpi_code,
        enabled=body.enabled,
        patient_visible=body.patient_visible,
        clinician_visible=body.clinician_visible,
        updated_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="kpi_config.updated",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="kpi_config",
        correlation_id=ctx.correlation_id,
        # Catalog code + booleans only — never a name, value, or free text.
        detail={
            "kpi_code": kpi_code,
            "enabled": body.enabled,
            "patient_visible": body.patient_visible,
            "clinician_visible": body.clinician_visible,
        },
    )
    return _out(row)


@router.delete("/kpi-config/{kpi_code}", response_model=KpiConfigOut)
def reset_kpi_config(
    kpi_code: str,
    ctx: TenantContext = Depends(require(Action.KPI_CONFIG_WRITE)),
) -> KpiConfigOut:
    row, previous_reference = kpi_config_service.reset_kpi_config(
        ctx.db, tenant_id=ctx.tenant_id, kpi_code=kpi_code
    )
    record_audit(
        ctx.db,
        action="kpi_config.reset",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="kpi_config",
        correlation_id=ctx.correlation_id,
        # Reset deletes the override row — record the clinic reference it carried, if any.
        detail={"kpi_code": kpi_code, **_previous_reference_detail(previous_reference)},
    )
    return _out(row)


@router.put("/kpi-config/{kpi_code}/reference", response_model=KpiConfigOut)
def set_kpi_reference(
    kpi_code: str,
    body: KpiReferenceIn,
    ctx: TenantContext = Depends(require(Action.KPI_CONFIG_WRITE)),
) -> KpiConfigOut:
    row, previous_reference = kpi_config_service.set_kpi_reference(
        ctx.db,
        tenant_id=ctx.tenant_id,
        kpi_code=kpi_code,
        reference_low=body.reference_low,
        reference_high=body.reference_high,
        updated_by_user_id=ctx.user.id,
    )
    record_audit(
        ctx.db,
        action="kpi_config.reference_set",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="kpi_config",
        correlation_id=ctx.correlation_id,
        # New AND replaced bounds, so every past fallback marker stays reconstructable.
        detail={
            "kpi_code": kpi_code,
            "unit": row.reference_unit,
            "low": str(body.reference_low),
            "high": str(body.reference_high),
            **_previous_reference_detail(previous_reference),
        },
    )
    return _out(row)


@router.delete("/kpi-config/{kpi_code}/reference", response_model=KpiConfigOut)
def clear_kpi_reference(
    kpi_code: str,
    ctx: TenantContext = Depends(require(Action.KPI_CONFIG_WRITE)),
) -> KpiConfigOut:
    row, previous_reference = kpi_config_service.clear_kpi_reference(
        ctx.db, tenant_id=ctx.tenant_id, kpi_code=kpi_code, updated_by_user_id=ctx.user.id
    )
    record_audit(
        ctx.db,
        action="kpi_config.reference_cleared",
        actor_user_id=ctx.user.id,
        tenant_id=ctx.tenant_id,
        target_type="kpi_config",
        correlation_id=ctx.correlation_id,
        detail={"kpi_code": kpi_code, **_previous_reference_detail(previous_reference)},
    )
    return _out(row)
