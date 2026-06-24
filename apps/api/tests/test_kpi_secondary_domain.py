"""KPI secondary-domain links (ADR-0004 Slice 2): seeded breadth, the secondary != primary
invariant, global read-only access, the (kpi_code, domain_axis) uniqueness, idempotent seeding,
and the navigational membership read helpers."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from hadp_api.modules.enums import DomainAxis
from hadp_api.modules.kpi.catalog_data import kpi_rows, kpi_secondary_domain_rows
from hadp_api.modules.kpi.models import KpiSecondaryDomain
from hadp_api.modules.kpi.service import (
    domain_membership,
    kpi_codes_for_domain,
    secondary_domains_for,
    seed_secondary_domains,
)


def test_rows_are_34_kpis_44_links_and_never_equal_primary() -> None:
    # Pure-data check (no DB): the transcription from ADR-0004 §7 is exact and internally valid.
    rows = kpi_secondary_domain_rows()
    primary = {str(r["code"]): str(r["primary_domain_axis"]) for r in kpi_rows()}
    valid = {r["primary_domain_axis"] for r in kpi_rows()}
    assert len(rows) == 44
    assert len({code for code, _ in rows}) == 34
    for code, axis in rows:
        assert code in primary, f"secondary link for unknown KPI: {code}"
        assert axis != primary[code], f"secondary equals primary: {code}"
        assert axis in valid, f"unknown domain axis: {axis}"
    # No duplicate (kpi_code, domain_axis) pairs.
    assert len(rows) == len(set(rows))


def test_secondary_domains_seeded(admin_session: Session) -> None:
    total = admin_session.execute(
        select(func.count()).select_from(KpiSecondaryDomain)
    ).scalar()
    distinct_kpis = admin_session.execute(
        select(func.count(func.distinct(KpiSecondaryDomain.kpi_code)))
    ).scalar()
    assert total == 44
    assert distinct_kpis == 34


def test_secondary_domain_readable_without_a_tenant_under_app_role() -> None:
    engine = create_engine(os.environ["APP_DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM kpi_secondary_domain")).scalar()
        assert count == 44
    finally:
        engine.dispose()


def test_app_role_cannot_write_the_secondary_domain() -> None:
    engine = create_engine(os.environ["APP_DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn, pytest.raises(ProgrammingError):
            conn.execute(
                text(
                    "INSERT INTO kpi_secondary_domain (kpi_code, domain_axis) "
                    "VALUES ('cardio.apob', 'neurocognitive')"
                )
            )
    finally:
        engine.dispose()


def test_duplicate_link_is_blocked_by_the_composite_pk(admin_session: Session) -> None:
    # metabolic.hba1c -> cardiovascular is a seeded link; re-inserting it violates the PK.
    admin_session.add(
        KpiSecondaryDomain(kpi_code="metabolic.hba1c", domain_axis=DomainAxis.CARDIOVASCULAR)
    )
    with pytest.raises(IntegrityError):
        admin_session.flush()


def test_seed_secondary_domains_is_idempotent(admin_session: Session) -> None:
    # Already seeded once at session scope; a re-run is a no-op and leaves the count unchanged.
    seeded = seed_secondary_domains(admin_session)
    total = admin_session.execute(
        select(func.count()).select_from(KpiSecondaryDomain)
    ).scalar()
    assert seeded is False
    assert total == 44


def test_secondary_domains_for_returns_the_links(admin_session: Session) -> None:
    assert set(secondary_domains_for(admin_session, "metabolic.hba1c")) == {
        DomainAxis.CARDIOVASCULAR,
        DomainAxis.NEUROCOGNITIVE,
    }
    # A KPI with no secondary links returns an empty list (never None, never a guess).
    assert secondary_domains_for(admin_session, "cardio.apob") == []


def test_kpi_codes_for_domain_unions_primary_and_secondary(admin_session: Session) -> None:
    codes = kpi_codes_for_domain(admin_session, DomainAxis.CARDIOVASCULAR)
    # Primary cardiovascular membership.
    assert "cardio.apob" in codes
    # Secondary-linked biomarkers surface in the cardiovascular view (navigational only).
    assert "metabolic.hba1c" in codes
    assert "immune.hs_crp" in codes
    # A purely neurocognitive-only KPI does not leak into cardiovascular.
    assert "neuro.episodic_memory_score" not in codes


def test_domain_membership_resolves_primary_and_secondary(admin_session: Session) -> None:
    # The batched resolver behind the Slice-2b timeline enrichment.
    m = domain_membership(admin_session, {"metabolic.hba1c", "cardio.apob", "nonsense.x"})
    primary, secondary = m["metabolic.hba1c"]
    assert primary is DomainAxis.METABOLIC
    assert set(secondary) == {DomainAxis.CARDIOVASCULAR, DomainAxis.NEUROCOGNITIVE}
    assert m["cardio.apob"] == (DomainAxis.CARDIOVASCULAR, [])  # primary only, no secondary
    assert "nonsense.x" not in m  # unknown codes are not invented
    assert domain_membership(admin_session, set()) == {}
