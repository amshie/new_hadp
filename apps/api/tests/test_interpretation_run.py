"""DB-backed tests for the interpretation service: create_run records a whole run; latest_matrix
returns 6 verdicts x 3 cells; reads are tenant-filtered; an invalid run shape is refused."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from hadp_api.errors import IntendedUseViolation
from hadp_api.modules.enums import (
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    DomainAxis,
    TriStateAxis,
)
from hadp_api.modules.interpretation import service
from hadp_api.modules.interpretation.run_shape import (
    CellInput,
    DomainInput,
    EvidenceRef,
    RunInput,
)
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.tenancy.models import Tenant

_REF = EvidenceRef(kind="observation", id=str(uuid.uuid4()))


def _domain(axis: DomainAxis) -> DomainInput:
    return DomainInput(
        domain_axis=axis,
        cis_status=CisStatus.CIS_4_CREDIBLE_IMPROVEMENT,
        actionability_class=ActionabilityClass.C_CLINICALLY_INTERPRETABLE,
        followup_adequacy=AdequacyStatus.ADEQUATE,
        rationale="note",
        cells=[
            CellInput(TriStateAxis.BIOLOGICAL, "STABLE", AdequacyStatus.ADEQUATE, [_REF]),
            CellInput(TriStateAxis.RISK, "REDUCED", AdequacyStatus.ADEQUATE, [_REF]),
            CellInput(TriStateAxis.FUNCTIONAL, "IMPROVED", AdequacyStatus.ADEQUATE, [_REF]),
        ],
    )


def _full_run() -> RunInput:
    return RunInput(domains=[_domain(a) for a in DomainAxis])


def _patient(db: Session, slug: str) -> tuple[uuid.UUID, uuid.UUID]:
    tenant = Tenant(name="T", slug=slug, is_synthetic=True)
    db.add(tenant)
    db.flush()
    patient = Patient(
        tenant_id=tenant.id,
        external_ref=f"SYN-{slug}",
        display_name="Synthetic Patient",
        date_of_birth=date(1980, 1, 1),
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()
    return tenant.id, patient.id


def test_create_run_records_six_verdicts_and_eighteen_cells(admin_session: Session) -> None:
    tenant_id, patient_id = _patient(admin_session, "run-a")
    service.create_run(
        admin_session,
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=None,
        run=_full_run(),
        reason="baseline",
    )
    matrix = service.latest_matrix(admin_session, tenant_id, patient_id)
    assert matrix is not None
    assert len(matrix["domains"]) == 6
    assert all(len(d["cells"]) == 3 for d in matrix["domains"])
    # CIS and Actionability are present as TWO separate fields (never merged).
    first = matrix["domains"][0]
    assert first["cis_status"].startswith("CIS_")
    assert first["actionability_class"][0] in "ABCDE"


def test_latest_matrix_is_tenant_filtered(admin_session: Session) -> None:
    tenant_id, patient_id = _patient(admin_session, "run-b")
    service.create_run(
        admin_session,
        tenant_id=tenant_id,
        patient_id=patient_id,
        created_by_user_id=None,
        run=_full_run(),
        reason="baseline",
    )
    # A different tenant id must not see this patient's run.
    assert service.latest_matrix(admin_session, uuid.uuid4(), patient_id) is None


def test_create_run_rejects_an_incomplete_run(admin_session: Session) -> None:
    tenant_id, patient_id = _patient(admin_session, "run-c")
    bad = _full_run()
    bad.domains.pop()  # five domains, not six
    with pytest.raises(IntendedUseViolation):
        service.create_run(
            admin_session,
            tenant_id=tenant_id,
            patient_id=patient_id,
            created_by_user_id=None,
            run=bad,
            reason="bad",
        )
