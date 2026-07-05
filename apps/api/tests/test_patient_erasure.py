"""Gated patient erasure (docs/notes/0012, PR B): the execute path.

An APPROVED request is executed by an owner or medical director. The engine anonymizes the
patient (tombstone) and hard-deletes PII-bearing artifacts, while PRESERVING the append-only
ledgers: consent gets an appended WITHDRAWN event (never deleted), audit is untouched, and
interpretation runs/cells are kept with their free text redacted. Object storage is purged.
Crucially, the append-only immutability of consent_events is NOT weakened by the erasure change.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, InternalError, ProgrammingError

from hadp_api.config import get_settings
from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.modules.audit.service import _FORBIDDEN_DETAIL_KEYS
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.consents.models import ConsentEvent
from hadp_api.modules.derivations.models import ObservationDerivation
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import (
    CELL_STATES,
    ActionabilityClass,
    AdequacyStatus,
    CisStatus,
    ConsentPurpose,
    DomainAxis,
    InvitationStatus,
    ReportStatus,
    Role,
    TriStateAxis,
    ValueType,
)
from hadp_api.modules.interpretation.models import (
    DomainAxisInterpretation,
    InterpretationRun,
    TriStateCell,
)
from hadp_api.modules.invitations.models import PatientInvitation
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy.models import DeletionRequest
from hadp_api.modules.privacy.service import TOMBSTONE_NAME
from hadp_api.modules.reports.models import Report, ReportVersion
from tests.helpers import login_as, switch_role

_SENSITIVE = "SENSITIVE FREE TEXT"


def _obs(tenant_id, patient_id, name: str) -> Observation:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    return Observation(
        tenant_id=tenant_id,
        patient_id=patient_id,
        original_name=name,
        original_value="1.0",
        value_type=ValueType.NUMERIC,
        normalization_version="synthetic-seed-1",
        observed_at=now,
        received_at=now,
        review_status="published",
    )


def _populate(admin_session, tenant_id, patient_id):  # type: ignore[no-untyped-def]
    """Insert a rich set of patient-owned artifacts, returning key ids + the storage key.

    Uses the admin (superuser) session: INSERT is permitted on append-only tables (the trigger
    only blocks UPDATE/DELETE), and RLS is bypassed for setup.
    """
    o1, o2, o3 = (
        _obs(tenant_id, patient_id, "LDL"),
        _obs(tenant_id, patient_id, "ApoB"),
        _obs(tenant_id, patient_id, "Ratio"),
    )
    admin_session.add_all([o1, o2, o3])
    admin_session.flush()
    # Append-only derivation lineage (o3 derived from o1 + o2). Deleting o3's observations must
    # first remove these — the gated path handles it.
    admin_session.add_all(
        [
            ObservationDerivation(
                tenant_id=tenant_id,
                derived_observation_id=o3.id,
                input_observation_id=o1.id,
                role="input",
            ),
            ObservationDerivation(
                tenant_id=tenant_id,
                derived_observation_id=o3.id,
                input_observation_id=o2.id,
                role="input",
            ),
        ]
    )

    # Append-only interpretation with sensitive free text (reason / rationale x2).
    run = InterpretationRun(
        tenant_id=tenant_id, patient_id=patient_id, run_number=1, reason=_SENSITIVE
    )
    admin_session.add(run)
    admin_session.flush()
    dai = DomainAxisInterpretation(
        tenant_id=tenant_id,
        interpretation_run_id=run.id,
        domain_axis=DomainAxis.METABOLIC,
        cis_status=CisStatus.CIS_0_INSUFFICIENT_EVIDENCE,
        actionability_class=ActionabilityClass.A_DISCOVERY,
        followup_adequacy=AdequacyStatus.NOT_ASSESSED,
        rationale=_SENSITIVE,
    )
    admin_session.add(dai)
    admin_session.flush()
    cell = TriStateCell(
        tenant_id=tenant_id,
        domain_axis_interpretation_id=dai.id,
        tri_state_axis=TriStateAxis.BIOLOGICAL,
        state=CELL_STATES[0],
        endpoint_adequacy=AdequacyStatus.NOT_ASSESSED,
        rationale=_SENSITIVE,
    )
    admin_session.add(cell)

    # Source document + object-storage blob.
    storage_key = f"{tenant_id}/{patient_id}/deadbeefcafe"
    admin_session.add(
        SourceDocument(
            tenant_id=tenant_id,
            patient_id=patient_id,
            filename="labs.csv",
            content_type="text/csv",
            byte_size=6,
            checksum_sha256="deadbeefcafe",
            storage_key=storage_key,
        )
    )
    get_blob_store(get_settings()).put(storage_key, b"secret", "text/csv")

    # A report + version.
    report = Report(tenant_id=tenant_id, patient_id=patient_id, status=ReportStatus.DRAFT_GENERATED)
    admin_session.add(report)
    admin_session.flush()
    admin_session.add(
        ReportVersion(
            tenant_id=tenant_id,
            report_id=report.id,
            version_no=1,
            status=ReportStatus.DRAFT_GENERATED,
            body={"statements": []},
            narrative_provider="deterministic",
            narrative_version="v1",
        )
    )
    admin_session.commit()
    return {"run_id": run.id, "dai_id": dai.id, "cell_id": cell.id, "storage_key": storage_key}


def _count(admin_session, model, patient_id) -> int:  # type: ignore[no-untyped-def]
    return int(
        admin_session.execute(
            select(func.count()).select_from(model).where(model.patient_id == patient_id)
        ).scalar_one()
    )


def _approved_request(client, admin_session, *, slug: str, role_exec: Role):  # type: ignore[no-untyped-def]
    """Create patient + populate + request(owner) + approve(MD), then log in as the executor."""
    owner, tenant = login_as(
        client,
        admin_session,
        email=f"{slug}-owner@synthetic.example",
        tenant_name=f"Erasure Exec {slug}",
        tenant_slug=f"erasure-exec-{slug}",
        role=Role.OWNER,
    )
    pid = client.post(
        "/api/v1/patients",
        json={
            "display_name": "Erase Me",
            "external_ref": "SYN-ERASE",
            "date_of_birth": "1970-01-01",
        },
    ).json()["id"]
    puid = uuid.UUID(pid)
    for purpose in ("report_release", "data_source_connect"):
        client.post(
            f"/api/v1/patients/{pid}/consents", json={"purpose": purpose, "channel": "in_person"}
        )
    client.post(f"/api/v1/patients/{pid}/invitations")
    ids = _populate(admin_session, tenant.id, puid)

    rid = client.post(
        f"/api/v1/patients/{pid}/deletion-requests", json={"reason_category": "patient_request"}
    ).json()["id"]
    switch_role(
        client,
        admin_session,
        email=f"{slug}-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/approve").status_code == 200
    if role_exec != Role.MEDICAL_DIRECTOR:
        switch_role(
            client,
            admin_session,
            email=f"{slug}-exec@synthetic.example",
            tenant=tenant,
            role=role_exec,
        )
    return owner, tenant, pid, puid, rid, ids


def test_execute_erases_pii_preserves_ledgers_tombstones(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant, pid, puid, rid, ids = _approved_request(
        client, admin_session, slug="full", role_exec=Role.MEDICAL_DIRECTOR
    )
    blob = get_blob_store(get_settings())
    assert blob.exists(ids["storage_key"]) is True

    resp = client.post(f"/api/v1/deletion-requests/{rid}/execute")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "executed"
    assert body["patient_erased"] is True
    assert body["patient_display_name"] == TOMBSTONE_NAME
    assert body["executed_at"] is not None

    # PII-bearing artifacts are gone.
    assert _count(admin_session, Observation, puid) == 0
    assert _count(admin_session, SourceDocument, puid) == 0
    assert _count(admin_session, Report, puid) == 0
    assert (
        admin_session.execute(
            select(func.count())
            .select_from(ObservationDerivation)
            .where(ObservationDerivation.tenant_id == tenant.id)
        ).scalar_one()
        == 0
    )
    # Object storage purged.
    assert blob.exists(ids["storage_key"]) is False

    # Interpretation KEPT (append-only) but free text redacted.
    run = admin_session.get(InterpretationRun, ids["run_id"])
    assert run is not None and run.reason == "[erased]"
    dai = admin_session.get(DomainAxisInterpretation, ids["dai_id"])
    assert dai is not None and dai.rationale is None
    cell = admin_session.get(TriStateCell, ids["cell_id"])
    assert cell is not None and cell.rationale is None
    # The verdict enums themselves are untouched (only free text was redacted).
    assert dai.cis_status == CisStatus.CIS_0_INSUFFICIENT_EVIDENCE

    # Consent ledger preserved: the two GRANTED rows remain AND a WITHDRAWN was appended per
    # purpose; both purposes are now inactive.
    events = (
        admin_session.execute(select(ConsentEvent).where(ConsentEvent.patient_id == puid))
        .scalars()
        .all()
    )
    granted = [e for e in events if e.event_type.value == "granted"]
    withdrawn = [e for e in events if e.event_type.value == "withdrawn"]
    assert len(granted) == 2 and len(withdrawn) == 2
    for purpose in (ConsentPurpose.REPORT_RELEASE, ConsentPurpose.DATA_SOURCE_CONNECT):
        assert (
            consents_service.has_active_consent(
                admin_session, tenant_id=tenant.id, patient_id=puid, purpose=purpose
            )
            is False
        )

    # Invitation revoked.
    inv = (
        admin_session.execute(select(PatientInvitation).where(PatientInvitation.patient_id == puid))
        .scalars()
        .one()
    )
    assert inv.status == InvitationStatus.REVOKED

    # Patient tombstoned: identity blanked, row kept, erased_at set.
    patient = admin_session.get(Patient, puid)
    assert patient is not None
    assert patient.display_name == TOMBSTONE_NAME
    assert patient.date_of_birth is None
    assert patient.external_ref is None
    assert patient.erased_at is not None

    # Request closed out with a count-only manifest.
    dr = admin_session.get(DeletionRequest, uuid.UUID(rid))
    assert dr is not None and dr.status.value == "executed"
    assert dr.executed_by_user_id is not None and dr.executed_at is not None
    assert dr.erasure_manifest["observations"] == 3
    assert dr.erasure_manifest["documents"] == 1
    assert dr.erasure_manifest["reports"] == 1
    assert dr.erasure_manifest["consents_withdrawn"] == 2
    assert dr.erasure_manifest["invitations_revoked"] == 1
    # Manifest carries no forbidden (PII) keys.
    assert not _FORBIDDEN_DETAIL_KEYS.intersection(dr.erasure_manifest)


def test_consent_events_still_append_only_after_erasure(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant, _pid, puid, rid, _ids = _approved_request(
        client, admin_session, slug="immut", role_exec=Role.MEDICAL_DIRECTOR
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 200

    event_id = (
        admin_session.execute(select(ConsentEvent.id).where(ConsentEvent.patient_id == puid))
        .scalars()
        .first()
    )
    # Under the real app role, UPDATE/DELETE on consent_events are STILL denied (the erasure
    # change never touched this trigger/REVOKE). The erasure GUC does not unlock consent mutation.
    for stmt in (
        "UPDATE consent_events SET channel = 'x' WHERE id = :i",
        "DELETE FROM consent_events WHERE id = :i",
    ):
        sess = get_sessionmaker()()
        set_tenant_context(sess, tenant.id)
        try:
            with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
                sess.execute(text(stmt), {"i": event_id})
        finally:
            sess.rollback()
            sess.close()


def test_interpretation_update_still_blocked_outside_erasure(admin_session) -> None:  # type: ignore[no-untyped-def]
    """A normal (non-erasure) UPDATE of an append-only interpretation row still RAISEs."""
    from tests.helpers import make_tenant

    tenant = make_tenant(admin_session, name="Immut Interp", slug="immut-interp")
    patient = Patient(tenant_id=tenant.id, display_name="P", is_synthetic=True)
    admin_session.add(patient)
    admin_session.flush()
    run = InterpretationRun(
        tenant_id=tenant.id, patient_id=patient.id, run_number=1, reason="original"
    )
    admin_session.add(run)
    admin_session.commit()

    # No erasure GUC set → the trigger blocks the UPDATE even for the superuser.
    with pytest.raises((DBAPIError, InternalError, ProgrammingError)):
        admin_session.execute(
            text("UPDATE interpretation_runs SET reason = 'x' WHERE id = :i"), {"i": run.id}
        )
    admin_session.rollback()
    assert admin_session.get(InterpretationRun, run.id).reason == "original"


def test_erased_patient_hidden_from_directory_and_duplicate_probe(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, _tenant, pid, _puid, rid, _ids = _approved_request(
        client, admin_session, slug="hide", role_exec=Role.MEDICAL_DIRECTOR
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 200

    # Directory listing excludes the tombstone.
    listed = client.get("/api/v1/patients").json()
    assert pid not in [p["id"] for p in listed]
    # get by id still resolves (tombstone), flagged erased.
    got = client.get(f"/api/v1/patients/{pid}").json()
    assert got["erased"] is True and got["display_name"] == TOMBSTONE_NAME
    # Duplicate probe does NOT match the erased identity.
    probe = client.post(
        "/api/v1/patients/duplicate-check",
        json={
            "display_name": "Erase Me",
            "external_ref": "SYN-ERASE",
            "date_of_birth": "1970-01-01",
        },
    ).json()
    assert probe == {"candidates": [], "has_strong_match": False}


def test_execute_authz_and_state_guards(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner, tenant, _pid, _puid, rid, _ids = _approved_request(
        client, admin_session, slug="guard", role_exec=Role.MEDICAL_DIRECTOR
    )
    # Care staff may not execute.
    switch_role(
        client,
        admin_session,
        email="guard-clin@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 403

    # The owner CAN execute (owner or medical director are permitted).
    switch_role(
        client,
        admin_session,
        email="guard-owner2@synthetic.example",
        tenant=tenant,
        role=Role.OWNER,
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 200
    # A second execute on an already-executed request is a 409 (idempotency guard).
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 409


def test_cannot_execute_unapproved_or_cross_tenant(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    # A pending (un-approved) request cannot be executed.
    _owner, tenant = login_as(
        client,
        admin_session,
        email="pend-owner@synthetic.example",
        tenant_name="Erasure Pending",
        tenant_slug="erasure-pending",
        role=Role.OWNER,
    )
    pid = client.post("/api/v1/patients", json={"display_name": "Pending P"}).json()["id"]
    rid = client.post(
        f"/api/v1/patients/{pid}/deletion-requests", json={"reason_category": "patient_request"}
    ).json()["id"]
    switch_role(
        client,
        admin_session,
        email="pend-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/deletion-requests/{rid}/execute").status_code == 409

    # Tenant B (a medical director) cannot execute tenant A's approved request.
    _owner_a, tenant_a, _pa, _pua, rid_a, _ids = _approved_request(
        client, admin_session, slug="xtenant", role_exec=Role.MEDICAL_DIRECTOR
    )
    login_as(
        client,
        admin_session,
        email="xtenant-b-md@synthetic.example",
        tenant_name="Erasure X B",
        tenant_slug="erasure-x-b",
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/deletion-requests/{rid_a}/execute").status_code == 404
    # And tenant A's patient is NOT erased by the failed cross-tenant attempt.
    a_patient = admin_session.get(DeletionRequest, uuid.UUID(rid_a))
    assert a_patient.status.value == "approved"
