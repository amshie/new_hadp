"""Synthetic data generator.

Creates a small, deterministic, fully SYNTHETIC data set (clinics, staff, patients,
consent, and a few observations) for local development and demos. Idempotent: re-running
updates in place by natural key. Refuses to run with APP_ENV=production.

All records are flagged `is_synthetic=True`. No real patient data is ever used.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.modules.consents.models import ConsentEvent, ConsentRecord
from hadp_api.modules.derivations.service import compute_derived
from hadp_api.modules.enums import (
    ConsentEventType,
    ConsentPurpose,
    ConsentStatus,
    KpiMeasurementClass,
    ReviewStatus,
    Role,
    ValueType,
)
from hadp_api.modules.identity.models import User
from hadp_api.modules.kpi.service import resolve_kpi_code, seed_kpi_catalog
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.tenancy.models import Membership, Tenant

NORMALIZATION_VERSION = "synthetic-seed-1"

# (email, display_name, role)
_STAFF = [
    ("owner@demo.synthetic", "Synthetic Owner", Role.OWNER),
    ("clinician@demo.synthetic", "Synthetic Clinician", Role.CLINICIAN),
    ("assistant@demo.synthetic", "Synthetic Assistant", Role.ASSISTANT),
    # The clinician persona shown in the UI prototype, so its sign-in email works for real.
    ("s.johnson@meridian-health.eu", "Dr. Sarah Johnson", Role.CLINICIAN),
]


# Synthetic biomarkers per domain axis: (metric_code, name, value, unit, ref_low, ref_high).
# These back the per-cell evidence of the seeded interpretation run; LDL is seeded separately
# (two dates for the timeline demo) and cited under cardiovascular.
_MARKERS_BY_AXIS: dict[str, list[tuple[str, str, str, str | None, str | None, str | None]]] = {
    "metabolic": [
        ("4548-4", "HbA1c", "5.4", "%", "0", "5.6"),
        ("2345-7", "Nüchternglukose", "5.3", "mmol/L", "3.9", "5.6"),
    ],
    "immune_inflammation": [("1988-5", "hs-CRP", "1.8", "mg/L", "0", "3.0")],
    "cardiovascular": [("1884-6", "ApoB", "1.02", "g/L", "0", "1.0")],
    "neurocognitive": [("SYN-PROC", "Verarbeitungsgeschwindigkeit", "105", None, None, None)],
    "musculoskeletal": [("SYN-GRIP", "Griffstärke", "38", "kg", None, None)],
    "regenerative_capacity": [
        ("SYN-VO2", "VO2max", "34", "ml/kg/min", None, None),
        ("SYN-HRV", "HRV", "42", "ms", None, None),
    ],
}


def _get_or_create_user(db: Session, email: str, name: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=name, is_synthetic=True)
        db.add(user)
        db.flush()
    return user


def _get_or_create_tenant(db: Session, name: str, slug: str) -> Tenant:
    tenant = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=name, slug=slug, is_synthetic=True)
        db.add(tenant)
        db.flush()
    return tenant


def _ensure_membership(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID, role: Role) -> None:
    existing = db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(Membership(user_id=user_id, tenant_id=tenant_id, role=role))
        db.flush()


def _get_or_create_patient(
    db: Session, tenant_id: uuid.UUID, external_ref: str, name: str, dob: date
) -> Patient:
    patient = db.execute(
        select(Patient).where(Patient.tenant_id == tenant_id, Patient.external_ref == external_ref)
    ).scalar_one_or_none()
    if patient is None:
        patient = Patient(
            tenant_id=tenant_id,
            external_ref=external_ref,
            display_name=name,
            date_of_birth=dob,
            is_synthetic=True,
        )
        db.add(patient)
        db.flush()
    return patient


def _ensure_consent(db: Session, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    existing = db.execute(
        select(ConsentRecord).where(ConsentRecord.patient_id == patient_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            ConsentRecord(
                tenant_id=tenant_id,
                patient_id=patient_id,
                consent_text_version="v1",
                purposes=["analytics", "report"],
                channel="in_person",
                status=ConsentStatus.ACTIVE,
                recorded_at=datetime.now(UTC),
            )
        )
        db.flush()

    # Authoritative append-only consent: a GRANTED report_release event so the demo report can be
    # released (the consent gate reads consent_events, not the legacy ConsentRecord). Idempotent.
    has_release = db.execute(
        select(ConsentEvent).where(
            ConsentEvent.patient_id == patient_id,
            ConsentEvent.purpose == ConsentPurpose.REPORT_RELEASE,
        )
    ).first()
    if has_release is None:
        db.add(
            ConsentEvent(
                tenant_id=tenant_id,
                patient_id=patient_id,
                purpose=ConsentPurpose.REPORT_RELEASE,
                event_type=ConsentEventType.GRANTED,
                consent_text_version="synthetic-v1",
                channel="in_person",
                recorded_at=datetime.now(UTC),
            )
        )
        db.flush()


def _ensure_observation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    metric_code: str,
    name: str,
    value: Decimal,
    unit: str | None,
    ref_low: Decimal | None,
    ref_high: Decimal | None,
    observed_at: datetime,
    source_category: KpiMeasurementClass | None = None,
    device_model: str | None = None,
    firmware_or_algorithm_version: str | None = None,
    instrument_version: str | None = None,
) -> None:
    existing = db.execute(
        select(Observation).where(
            Observation.patient_id == patient_id,
            Observation.metric_code == metric_code,
            Observation.observed_at == observed_at,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    has_ref = ref_low is not None or ref_high is not None
    db.add(
        Observation(
            tenant_id=tenant_id,
            patient_id=patient_id,
            original_name=name,
            original_value=str(value),
            original_unit=unit,
            reference_text=f"{ref_low}-{ref_high} {unit or ''}".strip() if has_ref else None,
            metric_code=metric_code,
            code_system="LOINC",
            kpi_code=resolve_kpi_code(db, name, metric_code),
            mapping_confidence=1.0,
            source_category=source_category,
            device_model=device_model,
            firmware_or_algorithm_version=firmware_or_algorithm_version,
            instrument_version=instrument_version,
            value_type=ValueType.NUMERIC,
            numeric_value=value,
            normalized_value=value,
            normalized_unit=unit,
            reference_low=ref_low,
            reference_high=ref_high,
            normalization_version=NORMALIZATION_VERSION,
            observed_at=observed_at,
            observed_at_is_date_only=True,
            received_at=datetime.now(UTC),
            review_status=ReviewStatus.PUBLISHED,
        )
    )
    db.flush()


def _backfill_observation_kpi_codes(db: Session, patient_id: uuid.UUID) -> None:
    """Set kpi_code on observations that predate the column (idempotent; touches NULL rows only).

    Resolves via the same global alias + verified-LOINC rules as the normalizer; an unresolved term
    stays NULL (never guessed). Lets the Slice-2b domain view surface secondary-linked biomarkers.
    """
    rows = (
        db.execute(
            select(Observation).where(
                Observation.patient_id == patient_id, Observation.kpi_code.is_(None)
            )
        )
        .scalars()
        .all()
    )
    for obs in rows:
        code = resolve_kpi_code(db, obs.original_name, obs.metric_code)
        if code is not None:
            obs.kpi_code = code
    db.flush()


def _ensure_draft_report(db: Session, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    from hadp_api.modules.reports import service as reports_service
    from hadp_api.modules.reports.models import Report

    existing = db.execute(select(Report.id).where(Report.patient_id == patient_id).limit(1)).first()
    if existing is not None:
        return
    clinician = db.execute(
        select(User).where(User.email == "s.johnson@meridian-health.eu")
    ).scalar_one_or_none()
    if clinician is None:
        return
    reports_service.generate_draft(
        db,
        tenant_id=tenant_id,
        patient_id=patient_id,
        generated_by_user_id=clinician.id,
    )


def _ensure_interpretation_run(db: Session, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    """Seed one synthetic interpretation run (6 verdicts + 18 cells) for the demo patient."""
    from hadp_api.modules.enums import (
        ActionabilityClass,
        AdequacyStatus,
        CisStatus,
        DomainAxis,
        TriStateAxis,
    )
    from hadp_api.modules.interpretation import service as interp_service
    from hadp_api.modules.interpretation.models import InterpretationRun
    from hadp_api.modules.interpretation.run_shape import (
        CellInput,
        DomainInput,
        EvidenceRef,
        RunInput,
    )
    from hadp_api.modules.observations.models import Observation

    existing = db.execute(
        select(InterpretationRun.id).where(InterpretationRun.patient_id == patient_id).limit(1)
    ).first()
    if existing is not None:
        return
    if not interp_service.list_published_observation_ids(db, patient_id):
        return
    clinician = db.execute(
        select(User).where(User.email == "s.johnson@meridian-health.eu")
    ).scalar_one_or_none()

    def refs_for(*codes: str) -> list[EvidenceRef]:
        ids = (
            db.execute(
                select(Observation.id).where(
                    Observation.patient_id == patient_id,
                    Observation.metric_code.in_(codes),
                )
            )
            .scalars()
            .all()
        )
        return [EvidenceRef(kind="observation", id=str(i)) for i in ids]

    axis_refs: dict[str, list[EvidenceRef]] = {
        axis: refs_for(*[m[0] for m in markers]) for axis, markers in _MARKERS_BY_AXIS.items()
    }
    # Cardiovascular also cites the separately-seeded LDL observations (two dates).
    axis_refs["cardiovascular"] = refs_for("13457-7") + axis_refs["cardiovascular"]

    note = "Synthetic clinician note."

    def cell(axis: TriStateAxis, state: str, refs: list[EvidenceRef]) -> CellInput:
        # A determinate (non-INDETERMINATE) cell must cite evidence; INDETERMINATE may not.
        return CellInput(
            tri_state_axis=axis,
            state=state,
            endpoint_adequacy=AdequacyStatus.ADEQUATE,
            evidence_refs=[] if state == "INDETERMINATE" else refs,
        )

    def domain(
        axis: DomainAxis,
        cis: CisStatus,
        act: ActionabilityClass,
        adq: AdequacyStatus,
        bio: str,
        risk: str,
        func: str,
    ) -> DomainInput:
        refs = axis_refs[axis.value]
        return DomainInput(
            axis,
            cis,
            act,
            adq,
            [
                cell(TriStateAxis.BIOLOGICAL, bio, refs),
                cell(TriStateAxis.RISK, risk, refs),
                cell(TriStateAxis.FUNCTIONAL, func, refs),
            ],
            note,
        )

    domains = [
        domain(
            DomainAxis.METABOLIC,
            CisStatus.CIS_4_CREDIBLE_IMPROVEMENT,
            ActionabilityClass.C_CLINICALLY_INTERPRETABLE,
            AdequacyStatus.ADEQUATE,
            "IMPROVED",
            "REDUCED",
            "IMPROVED",
        ),
        domain(
            DomainAxis.IMMUNE_INFLAMMATION,
            CisStatus.CIS_2_NOT_YET_CREDIBLE,
            ActionabilityClass.A_DISCOVERY,
            AdequacyStatus.INADEQUATE,
            "IMPROVED",
            "UNRESOLVED",
            "INDETERMINATE",
        ),
        domain(
            DomainAxis.CARDIOVASCULAR,
            CisStatus.CIS_3_RISK_DOMINANT_OR_CONFLICTING,
            ActionabilityClass.D_ACTIONABLE_UNDER_GOVERNANCE,
            AdequacyStatus.ADEQUATE,
            "IMPROVED",
            "DOMINANT",
            "STABLE",
        ),
        domain(
            DomainAxis.NEUROCOGNITIVE,
            CisStatus.CIS_5_STABLE_NO_MATERIAL_CHANGE,
            ActionabilityClass.C_CLINICALLY_INTERPRETABLE,
            AdequacyStatus.ADEQUATE,
            "STABLE",
            "REDUCED",
            "STABLE",
        ),
        domain(
            DomainAxis.MUSCULOSKELETAL,
            CisStatus.CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY,
            ActionabilityClass.B_SUPPORTIVE,
            AdequacyStatus.INADEQUATE,
            "IMPROVED",
            "UNRESOLVED",
            "WORSENED",
        ),
        domain(
            DomainAxis.REGENERATIVE_CAPACITY,
            CisStatus.CIS_0_INSUFFICIENT_EVIDENCE,
            ActionabilityClass.E_DO_NOT_ACT,
            AdequacyStatus.NOT_ASSESSED,
            "INDETERMINATE",
            "UNRESOLVED",
            "INDETERMINATE",
        ),
    ]
    interp_service.create_run(
        db,
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=clinician.id if clinician else None,
        run=RunInput(domains=domains),
        reason="Synthetic baseline interpretation.",
    )


def seed_all(engine: Engine) -> dict[str, object]:
    """Seed the synthetic data set. Uses an admin connection (bypasses RLS for setup)."""
    with Session(engine, expire_on_commit=False) as db:
        # Global KPI reference catalog (idempotent) — must exist before observations set kpi_code.
        seed_kpi_catalog(db)

        clinic = _get_or_create_tenant(db, "Synthetic Longevity Clinic", "demo-clinic")
        clinic2 = _get_or_create_tenant(db, "Synthetic Preventive Care", "demo-clinic-2")

        for email, name, role in _STAFF:
            user = _get_or_create_user(db, email, name)
            _ensure_membership(db, user.id, clinic.id, role)
        # A clinician in the second clinic (used to demonstrate tenant isolation).
        other = _get_or_create_user(db, "clinician2@demo.synthetic", "Synthetic Clinician 2")
        _ensure_membership(db, other.id, clinic2.id, Role.CLINICIAN)

        patient = _get_or_create_patient(
            db, clinic.id, "SYN-0001", "Synthetic Patient One", date(1980, 5, 17)
        )
        _ensure_consent(db, clinic.id, patient.id)

        # Two LDL cholesterol observations on different dates (timeline demo).
        _ensure_observation(
            db,
            tenant_id=clinic.id,
            patient_id=patient.id,
            metric_code="13457-7",
            name="LDL Cholesterol",
            value=Decimal("3.6"),
            unit="mmol/L",
            ref_low=Decimal("0"),
            ref_high=Decimal("3.0"),
            observed_at=datetime(2025, 1, 15, tzinfo=UTC),
        )
        _ensure_observation(
            db,
            tenant_id=clinic.id,
            patient_id=patient.id,
            metric_code="13457-7",
            name="LDL Cholesterol",
            value=Decimal("2.8"),
            unit="mmol/L",
            ref_low=Decimal("0"),
            ref_high=Decimal("3.0"),
            observed_at=datetime(2025, 6, 10, tzinfo=UTC),
        )

        # Two appendicular-lean-mass observations across a DXA DEVICE/SOFTWARE CHANGE (ADR-0004 §9,
        # Slice 3). Same KPI + unit, but body_composition requires a matching device+algorithm, so
        # these must NOT merge into a delta — a device swap can shift lean mass and a rendered
        # change would be a fabricated trend. The two points show individually; no delta.
        for date_, val, device, sw in [
            (datetime(2025, 1, 20, tzinfo=UTC), "21.0", "DXA-Model-A", "sw-3.1"),
            (datetime(2025, 6, 12, tzinfo=UTC), "21.6", "DXA-Model-B", "sw-4.0"),
        ]:
            _ensure_observation(
                db,
                tenant_id=clinic.id,
                patient_id=patient.id,
                metric_code="SYN-ALM",
                name="Appendicular lean mass",
                value=Decimal(val),
                unit="kg",
                ref_low=None,
                ref_high=None,
                observed_at=date_,
                source_category=KpiMeasurementClass.BODY_COMPOSITION,
                device_model=device,
                firmware_or_algorithm_version=sw,
            )

        # Inputs for the Slice-4 derived demo (BP, lipids, CBC at one visit) — exact catalog units.
        for in_code, in_name, in_value, in_unit in [
            ("8480-6", "Systolic blood pressure", "122", "mm[Hg]"),
            ("8462-4", "Diastolic blood pressure", "78", "mm[Hg]"),
            ("2093-3", "Total cholesterol", "4.8", "mmol/L"),
            ("2085-9", "HDL cholesterol", "1.3", "mmol/L"),
            ("751-8", "Absolute neutrophil count", "3.8", "10*9/L"),
            ("731-0", "Absolute lymphocyte count", "1.9", "10*9/L"),
        ]:
            _ensure_observation(
                db,
                tenant_id=clinic.id,
                patient_id=patient.id,
                metric_code=in_code,
                name=in_name,
                value=Decimal(in_value),
                unit=in_unit,
                ref_low=None,
                ref_high=None,
                observed_at=datetime(2025, 6, 10, tzinfo=UTC),
            )

        # Domain-specific synthetic biomarkers (back the interpretation run's per-cell evidence).
        for markers in _MARKERS_BY_AXIS.values():
            for code, name, value, unit, lo, hi in markers:
                _ensure_observation(
                    db,
                    tenant_id=clinic.id,
                    patient_id=patient.id,
                    metric_code=code,
                    name=name,
                    value=Decimal(value),
                    unit=unit,
                    ref_low=Decimal(lo) if lo is not None else None,
                    ref_high=Decimal(hi) if hi is not None else None,
                    observed_at=datetime(2025, 6, 10, tzinfo=UTC),
                )

        # Backfill kpi_code on any observation seeded before the column existed (ADR-0004 Slice 2b).
        _backfill_observation_kpi_codes(db, patient.id)

        # Slice-4 first-tranche derived values — an EXPLICIT controlled call (never on import, §10).
        # Idempotent; fails closed if an input is missing. Each result is a labelled
        # source_category='derived' Observation with frozen provenance + append-only input lineage.
        for formula_id in ("non_hdl_c.v1", "pulse_pressure.v1", "map.v1", "nlr.v1"):
            compute_derived(db, tenant_id=clinic.id, patient_id=patient.id, formula_id=formula_id)

        # A source-grounded draft for the demo patient (idempotent) so the worklist and
        # review screens have real data to read.
        _ensure_draft_report(db, clinic.id, patient.id)

        # One synthetic interpretation run (the six-axis matrix) for the demo patient.
        _ensure_interpretation_run(db, clinic.id, patient.id)

        db.commit()
        return {
            "tenants": [clinic.slug, clinic2.slug],
            "staff_logins": [email for email, _, _ in _STAFF] + ["clinician2@demo.synthetic"],
            "patient_external_ref": patient.external_ref,
        }


def main() -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("refusing to seed synthetic data with APP_ENV=production")
    # Admin DSN bypasses RLS, which is required to insert tenant-scoped rows during setup.
    engine = create_engine(settings.database_url, future=True)
    try:
        result = seed_all(engine)
    finally:
        engine.dispose()
    print("=== SYNTHETIC DATA seeded (no real patient data) ===")
    print(f"tenants:        {result['tenants']}")
    print(f"staff logins:   {result['staff_logins']}")
    print(f"demo patient:   {result['patient_external_ref']}")
    print("Use any staff login with POST /api/v1/auth/dev-login (development only).")


if __name__ == "__main__":
    main()
