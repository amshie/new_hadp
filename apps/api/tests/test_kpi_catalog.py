"""KPI catalog (ADR-0004 Slice 1): seeded breadth, global read-only access, doctrine guardrails,
source-term resolution, and the table CHECK constraints."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from hadp_api.modules.enums import (
    DomainAxis,
    KpiCatalogTier,
    KpiMeasurementClass,
    KpiStatus,
)
from hadp_api.modules.kpi.catalog_data import CATALOG_VERSION, kpi_rows
from hadp_api.modules.kpi.models import KpiAlias, KpiCatalog
from hadp_api.modules.kpi.service import load_terminology, resolve_kpi_code, seed_terminology

_BLOCKED = {
    "unified_healthspan_score",
    "biological_age_score",
    "epigenetic_age_years_younger",
    "aging_reversal_score",
    "telomere_age",
    "nad_plus_score",
    "vendor_readiness_score",
}


def test_catalog_is_seeded_120_with_43_core(admin_session: Session) -> None:
    total = admin_session.execute(select(func.count()).select_from(KpiCatalog)).scalar()
    core = admin_session.execute(
        select(func.count()).select_from(KpiCatalog).where(KpiCatalog.default_enabled.is_(True))
    ).scalar()
    assert total == 120
    assert core == 43


def test_catalog_readable_without_a_tenant_under_app_role() -> None:
    # Global reference data: the hadp_app role reads it with NO app.current_tenant bound (no RLS).
    engine = create_engine(os.environ["APP_DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM kpi_catalog")).scalar()
        assert count == 120
    finally:
        engine.dispose()


def test_app_role_cannot_write_the_catalog() -> None:
    engine = create_engine(os.environ["APP_DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn, pytest.raises(ProgrammingError):
            conn.execute(
                text(
                    "INSERT INTO kpi_catalog (code, display_name, primary_domain_axis, "
                    "measurement_class, tier, default_enabled, is_derived, clinician_visible, "
                    "patient_visible, status) VALUES ('hack.x','X','metabolic','laboratory',"
                    "'extended',false,false,true,false,'active')"
                )
            )
    finally:
        engine.dispose()


def test_catalog_has_no_range_or_score_columns() -> None:
    cols = {c.name for c in KpiCatalog.__table__.columns}
    forbidden = {"reference_low", "reference_high", "optimal", "target", "goal", "score"}
    assert cols.isdisjoint(forbidden)


def test_no_blocked_concepts_are_catalog_codes() -> None:
    codes = {str(r["code"]) for r in kpi_rows()}
    leaf_names = {c.rsplit(".", 1)[-1] for c in codes}
    assert _BLOCKED.isdisjoint(codes)
    assert _BLOCKED.isdisjoint(leaf_names)


def test_resolve_kpi_code_maps_the_seed_markers(admin_session: Session) -> None:
    assert resolve_kpi_code(admin_session, "HbA1c", "4548-4") == "metabolic.hba1c"
    assert resolve_kpi_code(admin_session, "ApoB") == "cardio.apob"
    assert resolve_kpi_code(admin_session, "Griffstärke") == "msk.grip_strength"
    assert resolve_kpi_code(admin_session, "VO2max") == "regen.vo2peak_direct"
    # A verified LOINC resolves even without a name alias; an unknown term does not guess.
    assert resolve_kpi_code(admin_session, "unknown marker", "30522-7") == "immune.hs_crp"
    assert resolve_kpi_code(admin_session, "totally unknown marker") is None


def test_the_import_terminology_is_the_seeded_catalog(admin_session: Session) -> None:
    """What an import resolves against (loaded from the tables) is exactly what the seed data
    says — the normalizer's unit tests run against the latter."""
    loaded = load_terminology(admin_session)
    assert loaded == seed_terminology()
    term = loaded.resolve("  LDL Cholesterol ")
    assert term is not None
    assert (term.kpi_code, term.canonical_unit) == ("cardio.ldl_c", "mmol/L")
    grip = loaded.resolve("Griffstärke")
    assert grip is not None and grip.kpi_code == "msk.grip_strength"
    assert loaded.resolve("totally unknown marker") is None


def test_a_kpi_that_is_not_active_resolves_to_nothing(admin_session: Session) -> None:
    """A deprecated or blocked KPI must not be mapped by an import: its values wait for a human."""
    try:
        admin_session.execute(
            text("UPDATE kpi_catalog SET status = 'deprecated' WHERE code = 'cardio.ldl_c'")
        )
        loaded = load_terminology(admin_session)
        assert loaded.resolve("LDL Cholesterol") is None
        assert loaded.resolve("HDL cholesterol") is not None
    finally:
        admin_session.rollback()


def test_an_alias_of_one_source_system_is_not_part_of_the_global_terminology(
    admin_session: Session,
) -> None:
    """A name one laboratory uses for a KPI says nothing about what another source means by
    it. Only global aliases resolve."""
    try:
        admin_session.add(
            KpiAlias(kpi_code="immune.ferritin", alias_normalized="fer-x", source_system="lab-x")
        )
        admin_session.flush()
        loaded = load_terminology(admin_session)
        assert loaded.resolve("FER-X") is None
        assert loaded.resolve("Ferritin") is not None
    finally:
        admin_session.rollback()


def _catalog_row(**overrides: object) -> KpiCatalog:
    row = KpiCatalog(
        code="test.x",
        display_name="Test KPI",
        primary_domain_axis=DomainAxis.METABOLIC,
        measurement_class=KpiMeasurementClass.LABORATORY,
        tier=KpiCatalogTier.EXTENDED,
        default_enabled=False,
        is_derived=False,
        formula_id=None,
        clinician_visible=True,
        patient_visible=False,
        status=KpiStatus.ACTIVE,
        introduced_in=CATALOG_VERSION,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_derived_requires_formula_id_check(admin_session: Session) -> None:
    admin_session.add(_catalog_row(code="test.derived", is_derived=True, formula_id=None))
    with pytest.raises(IntegrityError):
        admin_session.flush()


def test_specialist_research_cannot_be_patient_visible_check(admin_session: Session) -> None:
    admin_session.add(
        _catalog_row(code="test.research", tier=KpiCatalogTier.RESEARCH, patient_visible=True)
    )
    with pytest.raises(IntegrityError):
        admin_session.flush()
