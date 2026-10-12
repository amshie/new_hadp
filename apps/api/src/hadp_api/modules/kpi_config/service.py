"""Per-tenant KPI configuration service.

Reads the global catalog and overlays this tenant's overrides to produce the EFFECTIVE
per-clinic KPI configuration. Writes only the tenant-scoped override rows; the global catalog
is never mutated. Every read/write is tenant-scoped (explicit filter + RLS).

Doctrine guard preserved from the catalog: a specialist/research-tier KPI can never be made
patient-visible — the same rule the catalog CHECK enforces (kpi_config may not bend it).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from hadp_api.errors import IntendedUseViolation, NotFound, ValidationFailed
from hadp_api.modules.enums import DomainAxis, KpiCatalogTier, KpiMeasurementClass, KpiStatus
from hadp_api.modules.kpi.models import KpiCatalog
from hadp_api.modules.kpi_config.models import TenantKpiSetting

# Tiers that must never be patient-visible (mirrors the kpi_catalog CHECK constraint).
_NEVER_PATIENT_VISIBLE = frozenset({KpiCatalogTier.SPECIALIST, KpiCatalogTier.RESEARCH})


@dataclass(frozen=True)
class ClinicReference:
    """A tenant's clinic-defined reference interval for one KPI (in `unit`)."""

    low: Decimal
    high: Decimal
    unit: str


@dataclass(frozen=True)
class KpiConfigRow:
    kpi_code: str
    display_name: str
    primary_domain_axis: DomainAxis
    tier: KpiCatalogTier
    measurement_class: KpiMeasurementClass
    # Catalog (global) defaults, shown so the owner sees what they are overriding.
    catalog_default_enabled: bool
    catalog_patient_visible: bool
    catalog_clinician_visible: bool
    # Effective per-clinic values (override if present, else catalog).
    effective_enabled: bool
    effective_patient_visible: bool
    effective_clinician_visible: bool
    is_overridden: bool
    # Clinic-defined reference interval (fallback-only, position-only) in the KPI's canonical unit.
    reference_low: Decimal | None
    reference_high: Decimal | None
    reference_unit: str | None
    # The KPI's canonical unit — the unit a clinic reference must be entered in (None => no numeric
    # reference is possible for this KPI, e.g. a panel).
    canonical_unit: str | None


def _row(catalog: KpiCatalog, setting: TenantKpiSetting | None) -> KpiConfigRow:
    pv_override = setting.patient_visible_override if setting is not None else None
    cv_override = setting.clinician_visible_override if setting is not None else None
    return KpiConfigRow(
        kpi_code=catalog.code,
        display_name=catalog.display_name,
        primary_domain_axis=catalog.primary_domain_axis,
        tier=catalog.tier,
        measurement_class=catalog.measurement_class,
        catalog_default_enabled=catalog.default_enabled,
        catalog_patient_visible=catalog.patient_visible,
        catalog_clinician_visible=catalog.clinician_visible,
        effective_enabled=setting.enabled if setting is not None else catalog.default_enabled,
        effective_patient_visible=(
            pv_override if pv_override is not None else catalog.patient_visible
        ),
        effective_clinician_visible=(
            cv_override if cv_override is not None else catalog.clinician_visible
        ),
        # "Overridden" means a REAL deviation from the catalog defaults — not merely that a settings
        # row exists (a row can survive holding only defaults, e.g. after a reference is cleared).
        is_overridden=setting is not None
        and (
            setting.enabled != catalog.default_enabled
            or setting.patient_visible_override is not None
            or setting.clinician_visible_override is not None
            or setting.reference_low is not None
        ),
        reference_low=setting.reference_low if setting is not None else None,
        reference_high=setting.reference_high if setting is not None else None,
        reference_unit=setting.reference_unit if setting is not None else None,
        canonical_unit=catalog.canonical_unit_ucum,
    )


def list_kpi_config(db: Session, *, tenant_id: uuid.UUID) -> list[KpiConfigRow]:
    """Every active catalog KPI with this tenant's effective configuration (tenant-scoped).

    LEFT JOINs the global catalog to the tenant's override rows. The override side is scoped by
    tenant_id explicitly AND by RLS; the catalog side is global read-only reference data.
    """
    rows = db.execute(
        select(KpiCatalog, TenantKpiSetting)
        .outerjoin(
            TenantKpiSetting,
            and_(
                TenantKpiSetting.kpi_code == KpiCatalog.code,
                TenantKpiSetting.tenant_id == tenant_id,
            ),
        )
        .where(KpiCatalog.status == KpiStatus.ACTIVE)
        .order_by(KpiCatalog.primary_domain_axis, KpiCatalog.display_name)
    ).all()
    return [_row(catalog, setting) for catalog, setting in rows]


def _get_catalog(db: Session, kpi_code: str) -> KpiCatalog:
    catalog = db.get(KpiCatalog, kpi_code)
    if catalog is None:
        raise NotFound("kpi not found")
    return catalog


def set_kpi_config(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    kpi_code: str,
    enabled: bool,
    patient_visible: bool | None,
    clinician_visible: bool | None,
    updated_by_user_id: uuid.UUID,
) -> KpiConfigRow:
    """Upsert this tenant's override for one KPI (replace semantics).

    `enabled` is always set; the two visibility overrides are set to the given value or NULL
    (NULL = inherit the catalog). Refuses to make a specialist/research KPI patient-visible.
    A cross-tenant/unknown kpi_code is a 404 (no info leak).
    """
    catalog = _get_catalog(db, kpi_code)

    effective_patient_visible = (
        patient_visible if patient_visible is not None else catalog.patient_visible
    )
    if catalog.tier in _NEVER_PATIENT_VISIBLE and effective_patient_visible:
        raise IntendedUseViolation("specialist/research KPIs can never be made patient-visible")

    setting = db.execute(
        select(TenantKpiSetting).where(
            TenantKpiSetting.tenant_id == tenant_id,
            TenantKpiSetting.kpi_code == kpi_code,
        )
    ).scalar_one_or_none()
    if setting is None:
        setting = TenantKpiSetting(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            enabled=enabled,
            patient_visible_override=patient_visible,
            clinician_visible_override=clinician_visible,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(setting)
    else:
        setting.enabled = enabled
        setting.patient_visible_override = patient_visible
        setting.clinician_visible_override = clinician_visible
        setting.updated_by_user_id = updated_by_user_id
        setting.updated_at = datetime.now(UTC)
    db.flush()
    return _row(catalog, setting)


def reset_kpi_config(
    db: Session, *, tenant_id: uuid.UUID, kpi_code: str
) -> tuple[KpiConfigRow, ClinicReference | None]:
    """Remove this tenant's override for one KPI (idempotent) → back to the catalog default.

    Also returns the clinic reference the deleted row carried (None if it carried none): the row
    is gone afterwards, so the caller must put those bounds into the audit trail or they are lost.
    """
    catalog = _get_catalog(db, kpi_code)
    setting = db.execute(
        select(TenantKpiSetting).where(
            TenantKpiSetting.tenant_id == tenant_id,
            TenantKpiSetting.kpi_code == kpi_code,
        )
    ).scalar_one_or_none()
    previous = _previous_reference(setting)
    if setting is not None:
        db.delete(setting)
    db.flush()
    return _row(catalog, None), previous


def _get_or_create_setting(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    kpi_code: str,
    default_enabled: bool,
    updated_by_user_id: uuid.UUID,
) -> TenantKpiSetting:
    setting = db.execute(
        select(TenantKpiSetting).where(
            TenantKpiSetting.tenant_id == tenant_id,
            TenantKpiSetting.kpi_code == kpi_code,
        )
    ).scalar_one_or_none()
    if setting is None:
        # A reference-only row inherits the catalog's default enablement (setting a reference must
        # not silently enable/disable the KPI).
        setting = TenantKpiSetting(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            enabled=default_enabled,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(setting)
    return setting


def _previous_reference(setting: TenantKpiSetting | None) -> ClinicReference | None:
    """The complete clinic reference a write is about to replace/remove (None = none was set).

    Captured BEFORE mutation so the caller can audit it — the settings row is updated in place,
    so the audit trail is the only place the replaced interval survives.
    """
    if (
        setting is None
        or setting.reference_low is None
        or setting.reference_high is None
        or setting.reference_unit is None
    ):
        return None
    return ClinicReference(
        low=setting.reference_low, high=setting.reference_high, unit=setting.reference_unit
    )


def set_kpi_reference(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    kpi_code: str,
    reference_low: Decimal,
    reference_high: Decimal,
    updated_by_user_id: uuid.UUID,
) -> tuple[KpiConfigRow, ClinicReference | None]:
    """Set this tenant's clinic-defined reference interval for one KPI (in its canonical unit).

    A neutral, fallback-only reference: it is applied to the within/above/below marker ONLY when a
    lab result carries no reference of its own and the units match. It is never an "optimal" target
    and never a verdict. Requires a two-sided ordered interval on a KPI that has a canonical unit.
    Also returns the interval this write replaced (None on first set), for the audit trail.
    """
    catalog = _get_catalog(db, kpi_code)
    unit = catalog.canonical_unit_ucum
    if unit is None:
        raise ValidationFailed(
            "this KPI has no canonical unit; a numeric reference interval cannot be defined"
        )
    if reference_low >= reference_high:
        raise ValidationFailed("reference_low must be strictly less than reference_high")

    setting = _get_or_create_setting(
        db,
        tenant_id=tenant_id,
        kpi_code=kpi_code,
        default_enabled=catalog.default_enabled,
        updated_by_user_id=updated_by_user_id,
    )
    previous = _previous_reference(setting)
    setting.reference_low = reference_low
    setting.reference_high = reference_high
    setting.reference_unit = unit
    setting.updated_by_user_id = updated_by_user_id
    setting.updated_at = datetime.now(UTC)
    db.flush()
    return _row(catalog, setting), previous


def clear_kpi_reference(
    db: Session, *, tenant_id: uuid.UUID, kpi_code: str, updated_by_user_id: uuid.UUID
) -> tuple[KpiConfigRow, ClinicReference | None]:
    """Remove this tenant's clinic reference for one KPI (idempotent). Other overrides are kept.

    Also returns the removed interval (None if none was set), for the audit trail.
    """
    catalog = _get_catalog(db, kpi_code)
    setting = db.execute(
        select(TenantKpiSetting).where(
            TenantKpiSetting.tenant_id == tenant_id,
            TenantKpiSetting.kpi_code == kpi_code,
        )
    ).scalar_one_or_none()
    previous = _previous_reference(setting)
    if setting is not None:
        setting.reference_low = None
        setting.reference_high = None
        setting.reference_unit = None
        setting.updated_by_user_id = updated_by_user_id
        setting.updated_at = datetime.now(UTC)
        db.flush()
    return _row(catalog, setting), previous


def clinic_references(db: Session, *, tenant_id: uuid.UUID) -> dict[str, ClinicReference]:
    """This tenant's complete clinic reference intervals, keyed by kpi_code (tenant-scoped).

    Consumed by the clinician timeline as the fallback reference. The DB CHECK guarantees a row with
    a non-null `reference_low` also has `reference_high` and `reference_unit`.
    """
    rows = (
        db.execute(
            select(TenantKpiSetting).where(
                TenantKpiSetting.tenant_id == tenant_id,
                TenantKpiSetting.reference_low.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    out: dict[str, ClinicReference] = {}
    for r in rows:
        if (
            r.reference_low is not None
            and r.reference_high is not None
            and r.reference_unit is not None
        ):
            out[r.kpi_code] = ClinicReference(
                low=r.reference_low, high=r.reference_high, unit=r.reference_unit
            )
    return out


def effective_enabled_codes(db: Session, *, tenant_id: uuid.UUID) -> set[str]:
    """The set of KPI codes effectively enabled for this tenant (catalog default ± overrides).

    A small public seam other modules can consume to honour the clinic's KPI selection.
    """
    return {r.kpi_code for r in list_kpi_config(db, tenant_id=tenant_id) if r.effective_enabled}
