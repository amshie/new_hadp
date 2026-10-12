"""Patient data export (GDPR Art. 15 / Art. 20) — the clinic's tool for a subject-access answer.

Properties: the package holds the patient's own data and RELEASED content only (nothing
unreleased leaves through this path); it never holds another patient's or another clinic's
data, nor staff identities — a stored file is shipped only if a reader imported it into this
record, and only while its bytes still match the recorded checksum; a storage failure fails
the export instead of thinning it; computed values, replaced values and withdrawn report
versions are marked; only the owner may generate it; an erased record has nothing to export;
every export — and every export refused for a record that exists — leaves a trace without
content; the package says what it does not contain.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from sqlalchemy import select, update

from hadp_api.config import get_settings
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.derivations.service import compute_derived
from hadp_api.modules.documents.blob import BlobUnavailable, S3BlobStore, get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import ReviewStatus, Role, ValueType
from hadp_api.modules.identity.models import User
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.privacy import export as export_module
from hadp_api.modules.privacy.export import NOT_INCLUDED, _safe_filename
from hadp_api.modules.reports.language import restricted_terms
from hadp_api.modules.tenancy.models import Tenant
from tests.helpers import login, login_as, select_tenant, switch_role
from tests.ldt_fixtures import TRAILER, header, lab_test, ldt_file, report

_CSV = (
    b"Analyt;Wert;Einheit;Referenz_von;Referenz_bis;Abnahmedatum\n"
    b"LDL Cholesterol;2,8;mmol/L;0;3,0;10.06.2025\n"
    b"Ferritin;85;ng/mL;30;400;10.06.2025\n"
)


def _owner(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}-owner@synthetic.example",
        tenant_name=f"{slug} clinic",
        tenant_slug=slug,
        role=Role.OWNER,
    )


def _back_to(client, tenant, email: str) -> None:  # type: ignore[no-untyped-def]
    login(client, email)
    select_tenant(client, tenant.id)


def _patient(client, name: str, **extra: Any) -> str:  # type: ignore[no-untyped-def]
    resp = client.post("/api/v1/patients", json={"display_name": name, **extra})
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _upload_and_import(client, patient_id: str, data: bytes, name: str) -> str:  # type: ignore[no-untyped-def]
    uploaded = client.post(
        f"/api/v1/patients/{patient_id}/documents", files={"file": (name, data, "text/csv")}
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = str(uploaded.json()["id"])
    imported = client.post(f"/api/v1/patients/{patient_id}/documents/{document_id}/import")
    assert imported.status_code == 201, imported.text
    return document_id


def _export(client, patient_id: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/patients/{patient_id}/data-export")


def _open(resp) -> tuple[zipfile.ZipFile, dict[str, Any]]:  # type: ignore[no-untyped-def]
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    return archive, json.loads(archive.read("export.json"))


def _everything(archive: zipfile.ZipFile) -> bytes:
    """Every byte a reader of the package can see: entry names and uncompressed contents."""
    return b"\n".join(name.encode() + b"\n" + archive.read(name) for name in archive.namelist())


def _events(admin_session, action: str) -> list[AuditEvent]:  # type: ignore[no-untyped-def]
    return list(
        admin_session.execute(select(AuditEvent).where(AuditEvent.action == action)).scalars()
    )


def test_the_package_holds_the_patients_own_data_and_released_content_only(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export")
    pid = _patient(
        client,
        "Erika Mustermann (synthetic)",
        external_ref="SYN-0001",
        date_of_birth="1980-01-15",
        consents=[{"purpose": "report_release", "channel": "in_person"}],
    )
    document_id = _upload_and_import(client, pid, _CSV, "befund-juni.csv")
    # Another patient of the same clinic, with data of their own.
    other = _patient(client, "Zweite Person (synthetic)")
    _upload_and_import(client, other, _CSV + b"HbA1c;5,4;%;;;10.06.2025\n", "other.csv")

    # One report goes through the whole gate; a second one stays a draft.
    switch_role(
        client,
        admin_session,
        email="export-clinician@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    released_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{released_id}/approve").status_code == 200
    draft_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    switch_role(
        client,
        admin_session,
        email="export-director@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{released_id}/release").status_code == 200
    _back_to(client, tenant, "export-owner@synthetic.example")

    resp = _export(client, pid)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="datenauskunft-')
    assert "Mustermann" not in disposition  # the file name carries no identity
    assert resp.headers["x-checksum-sha256"] == hashlib.sha256(resp.content).hexdigest()

    archive, data = _open(resp)
    stored_path = f"documents/{document_id}/befund-juni.csv"
    assert sorted(archive.namelist()) == ["LIESMICH.txt", stored_path, "export.json"]
    assert archive.read(stored_path) == _CSV  # the original file, byte for byte

    assert (data["format"], data["format_version"]) == ("hadp-patient-export", "1")
    assert data["patient"] == {
        "id": pid,
        "display_name": "Erika Mustermann (synthetic)",
        "external_ref": "SYN-0001",
        "date_of_birth": "1980-01-15",
        "record_created_at": data["patient"]["record_created_at"],
    }
    assert [(e["purpose"], e["event_type"], e["channel"]) for e in data["consent_events"]] == [
        ("report_release", "granted", "in_person")
    ]

    values = {o["original_name"]: o for o in data["observations"]}
    assert set(values) == {"LDL Cholesterol", "Ferritin"}  # not the other patient's HbA1c
    ldl = values["LDL Cholesterol"]
    # As the source wrote it, next to the normalized form and where it came from.
    assert (ldl["original_value"], ldl["original_unit"], ldl["normalized_value"]) == (
        "2,8",
        "mmol/L",
        "2.8",
    )
    assert (ldl["observed_at"], ldl["observed_at_is_date_only"]) == ("2025-06-10", True)
    assert (ldl["review_status"], ldl["source_document_id"]) == ("published", document_id)
    assert ldl["source_record_locator"].startswith("line ")
    # A value still waiting for review is the patient's data too — with its state said.
    assert values["Ferritin"]["review_status"] == "pending"

    assert [(d["id"], d["file"]) for d in data["source_documents"]] == [(document_id, stored_path)]

    # Only what passed the release gate: the draft report is not in the package.
    assert [(r["report_id"], r["withdrawn"]) for r in data["released_reports"]] == [
        (released_id, False)
    ]
    assert data["released_reports"][0]["statements"]
    # Where the wording comes from travels with it.
    assert data["released_reports"][0]["narrative_provider"]
    assert data["released_reports"][0]["edited_by_clinician"] is False
    visible = _everything(archive).decode("utf-8")
    assert draft_id not in visible
    # No other patient, no staff identity (address, name or id).
    assert "Zweite Person" not in visible and other not in visible
    staff = admin_session.execute(select(User)).scalars().all()
    assert len(staff) == 3
    for member in staff:
        assert member.email not in visible
        assert member.display_name not in visible
        assert str(member.id) not in visible
    assert all(o["computed"] is False and o["derivation"] is None for o in data["observations"])
    assert data["source_documents_not_imported"] == 0

    # The package says what it does not contain.
    assert [n["what"] for n in data["not_included"]] == [key for key, _e, _g in NOT_INCLUDED]
    readme = archive.read("LIESMICH.txt").decode("utf-8")
    assert all(german in readme for _key, _english, german in NOT_INCLUDED)
    assert "export clinic" in readme
    assert restricted_terms([readme]) == []

    # Audited with counts, size and checksum — the record of an export that is never stored.
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "privacy.export")
    ).scalar_one()
    assert audit.target_id == uuid.UUID(pid)
    assert audit.detail == {
        "consent_events": 1,
        "observations": 2,
        "computed_values": 0,
        "source_documents": 1,
        "source_files": 1,
        "source_files_missing": 0,
        "source_files_changed": 0,
        "source_documents_not_imported": 0,
        "released_report_versions": 1,
        "withdrawn_report_versions": 0,
        "byte_size": len(resp.content),
        "checksum_sha256": resp.headers["x-checksum-sha256"],
        "format_version": "1",
    }

    listed = client.get(f"/api/v1/patients/{pid}/data-exports")
    assert listed.status_code == 200, listed.text
    (entry,) = listed.json()
    assert (entry["checksum_sha256"], entry["observations"], entry["byte_size"]) == (
        resp.headers["x-checksum-sha256"],
        2,
        len(resp.content),
    )
    assert client.get(f"/api/v1/patients/{other}/data-exports").json() == []


def test_only_the_owner_may_export_and_only_in_their_clinic(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-roles")
    pid = _patient(client, "Rollen Test (synthetic)")
    for role in (Role.CLINICIAN, Role.ASSISTANT, Role.MEDICAL_DIRECTOR):
        switch_role(
            client,
            admin_session,
            email=f"export-roles-{role.value}@synthetic.example",
            tenant=tenant,
            role=role,
        )
        assert _export(client, pid).status_code == 403, role
        assert client.get(f"/api/v1/patients/{pid}/data-exports").status_code == 403, role

    # The owner of another clinic cannot even learn that the patient exists.
    _owner(client, admin_session, "export-elsewhere")
    assert _export(client, pid).status_code == 404
    assert client.get(f"/api/v1/patients/{pid}/data-exports").status_code == 404
    exports = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "privacy.export")
    ).scalars()
    assert exports.all() == []


def test_an_erased_record_has_nothing_to_export(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-erased")
    pid = _patient(client, "Erase Me (synthetic)", date_of_birth="1970-01-01")
    request_id = client.post(
        f"/api/v1/patients/{pid}/deletion-requests", json={"reason_category": "patient_request"}
    ).json()["id"]
    switch_role(
        client,
        admin_session,
        email="export-erased-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/deletion-requests/{request_id}/approve").status_code == 200
    assert client.post(f"/api/v1/deletion-requests/{request_id}/execute").status_code == 200
    _back_to(client, tenant, "export-erased-owner@synthetic.example")

    resp = _export(client, pid)
    assert resp.status_code == 409
    assert resp.json()["error"]["detail"].startswith("patient_erased")
    # A refused export of a whole record leaves a trace: who, which record, why.
    (refused,) = _events(admin_session, "privacy.export_refused")
    assert refused.detail == {"code": "patient_erased", "patient_id": pid}
    assert refused.actor_user_id is not None and refused.tenant_id == tenant.id
    assert _events(admin_session, "privacy.export") == []


def test_a_hostile_file_name_cannot_leave_its_folder(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-names")
    pid = _patient(client, "Datei Test (synthetic)")
    document_id = _upload_and_import(client, pid, _CSV, "../../etc/passwd\\..\\evil name?.csv")

    archive, data = _open(_export(client, pid))
    path = f"documents/{document_id}/evil name_.csv"
    assert path in archive.namelist()
    assert all(".." not in name and not name.startswith("/") for name in archive.namelist())
    # The name as it was uploaded is still reported, as data.
    assert data["source_documents"][0]["filename"].endswith("evil name?.csv")
    assert data["source_documents"][0]["file"] == path


def test_a_document_whose_file_is_gone_is_listed_without_a_file(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-gone")
    pid = _patient(client, "Blob Test (synthetic)")
    document_id = _upload_and_import(client, pid, _CSV, "befund.csv")
    key = admin_session.execute(select(SourceDocument.storage_key)).scalar_one()
    get_blob_store(get_settings()).delete(key)

    resp = _export(client, pid)
    assert resp.status_code == 200, resp.text
    archive, data = _open(resp)
    # Said, not hidden: the record is listed, the missing file is not invented.
    assert [(d["id"], d["file"]) for d in data["source_documents"]] == [(document_id, None)]
    assert sorted(archive.namelist()) == ["LIESMICH.txt", "export.json"]
    assert len(data["observations"]) == 2  # the values read from it are still there
    # The cover note and the owner's list count what is IN the package, and name the gap.
    readme = archive.read("LIESMICH.txt").decode("utf-8")
    assert "documents/     0 eingelesene Originaldatei(en)" in readme
    assert (
        "HINWEIS: 1 eingelesene Originaldatei(en) sind im Speicher nicht mehr vorhanden" in readme
    )
    (entry,) = client.get(f"/api/v1/patients/{pid}/data-exports").json()
    assert (entry["source_documents"], entry["source_files"], entry["source_files_missing"]) == (
        1,
        0,
        1,
    )


def test_the_export_is_rate_limited_per_user(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-limit")
    pid = _patient(client, "Limit Test (synthetic)")
    other = _patient(client, "Limit Test Zwei (synthetic)")
    # The limit is the user's, across patients.
    codes = [_export(client, pid).status_code for _ in range(5)]
    codes.append(_export(client, other).status_code)
    assert codes == [200, 200, 200, 200, 200, 429]
    # Another owner of the same clinic has a budget of their own.
    switch_role(
        client,
        admin_session,
        email="export-limit-second@synthetic.example",
        tenant=tenant,
        role=Role.OWNER,
    )
    assert _export(client, pid).status_code == 200


def test_an_unauthenticated_request_gets_nothing(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-anon")
    pid = _patient(client, "Anon Test (synthetic)")
    client.cookies.clear()
    assert _export(client, pid).status_code == 401
    assert client.get(f"/api/v1/patients/{pid}/data-exports").status_code == 401


# --- other people stay out: only a file read into this record is this person's ---


def _upload(client, patient_id: str, data: bytes, name: str, content_type: str) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"/api/v1/patients/{patient_id}/documents", files={"file": (name, data, content_type)}
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def test_a_file_refused_as_another_persons_report_is_not_exported(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-foreign")
    pid = _patient(client, "Anna Anders (synthetic)", date_of_birth="1975-03-02")
    # Misfiled: the report names Erika Mustermann, born 1980-01-15.
    foreign = ldt_file(
        header(), report(lab_test("LDL", "LDL Cholesterol", value="7.7", unit="mmol/L")), TRAILER
    )
    document_id = _upload(client, pid, foreign, "Mustermann_Z01.ldt", "application/octet-stream")
    refused = client.post(f"/api/v1/patients/{pid}/documents/{document_id}/import")
    assert refused.status_code == 409
    assert refused.json()["error"]["detail"].startswith("patient_mismatch")

    resp = _export(client, pid)
    assert resp.status_code == 200, resp.text
    archive, data = _open(resp)
    # Neither the file, nor its name, nor anything from it.
    assert sorted(archive.namelist()) == ["LIESMICH.txt", "export.json"]
    assert data["source_documents"] == [] and data["observations"] == []
    assert data["source_documents_not_imported"] == 1
    visible = _everything(archive)
    for trace in (b"Mustermann", b"19800115", b"7.7", document_id.encode()):
        assert trace not in visible, trace
    assert "HINWEIS: 1 gespeicherte Datei(en) wurden nicht maschinell in diese Akte" in (
        archive.read("LIESMICH.txt").decode("utf-8")
    )
    (entry,) = client.get(f"/api/v1/patients/{pid}/data-exports").json()
    assert (entry["source_files"], entry["source_documents_not_imported"]) == (0, 1)


def test_a_file_for_several_patients_or_without_a_reader_is_not_exported(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-batch")
    pid = _patient(client, "Erika Mustermann (synthetic)", date_of_birth="1980-01-15")
    batch = ldt_file(
        header(),
        report(lab_test("LDL", "LDL Cholesterol", value="2.8", unit="mmol/L")),
        report(
            lab_test("LDL", "LDL Cholesterol", value="9.9", unit="mmol/L"),
            last_name="Fremd",
            first_name="Frieda",
            born="19790101",
        ),
        TRAILER,
    )
    batch_id = _upload(client, pid, batch, "sammel.ldt", "application/octet-stream")
    assert client.post(f"/api/v1/patients/{pid}/documents/{batch_id}/import").status_code == 422
    # Stored, but no reader ever looked at it: nobody checked whose it is.
    _upload(
        client, pid, b"%PDF-1.4 synthetic scan of Frieda Fremd", "scan-fremd.pdf", "application/pdf"
    )

    archive, data = _open(_export(client, pid))
    assert sorted(archive.namelist()) == ["LIESMICH.txt", "export.json"]
    assert data["source_documents_not_imported"] == 2
    visible = _everything(archive)
    for trace in (b"Fremd", b"19790101", b"9.9", b"sammel", b"scan-fremd"):
        assert trace not in visible, trace


# --- truthful about what a value or a report version is ---


def test_a_withdrawn_released_version_is_marked_and_unreleased_ones_stay_out(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-withdrawn")
    pid = _patient(
        client,
        "Rückzug Test (synthetic)",
        consents=[{"purpose": "report_release", "channel": "in_person"}],
    )
    _upload_and_import(client, pid, _CSV, "befund.csv")
    switch_role(
        client,
        admin_session,
        email="export-withdrawn-clin@synthetic.example",
        tenant=tenant,
        role=Role.CLINICIAN,
    )
    released_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{released_id}/approve").status_code == 200
    approved_only = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{approved_only}/approve").status_code == 200
    rejected = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{rejected}/reject").status_code == 200
    switch_role(
        client,
        admin_session,
        email="export-withdrawn-md@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert client.post(f"/api/v1/reports/{released_id}/release").status_code == 200

    # The clinician revises the released report: v1 is withdrawn from the patient, v2 is a draft.
    _back_to(client, tenant, "export-withdrawn-clin@synthetic.example")
    view = client.get(f"/api/v1/reports/{released_id}").json()
    edited = client.post(
        f"/api/v1/reports/{released_id}/edit",
        json={
            "statements": [
                {
                    "id": st["id"],
                    "text": "UNRELEASED REVISION",
                    "evidence_observation_ids": [e["observation_id"] for e in st["evidence"]],
                }
                for st in view["statements"]
            ]
        },
    )
    assert edited.status_code == 200, edited.text

    _back_to(client, tenant, "export-withdrawn-owner@synthetic.example")
    archive, data = _open(_export(client, pid))
    assert [
        (r["report_id"], r["version_no"], r["withdrawn"]) for r in data["released_reports"]
    ] == [(released_id, 1, True)]
    visible = _everything(archive).decode("utf-8")
    assert "UNRELEASED REVISION" not in visible
    assert approved_only not in visible and rejected not in visible
    assert "(davon später zurückgezogen: 1)" in archive.read("LIESMICH.txt").decode("utf-8")


def test_a_computed_value_is_said_to_be_computed_and_marked_when_its_basis_was_replaced(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-derived")
    pid = _patient(client, "Berechnet Test (synthetic)")
    patient_id = uuid.UUID(pid)

    def reading(code: str, value: str, **extra: Any) -> Observation:
        observation = Observation(
            tenant_id=tenant.id,
            patient_id=patient_id,
            original_name=code,
            original_value=value,
            kpi_code=code,
            value_type=ValueType.NUMERIC,
            numeric_value=Decimal(value),
            normalized_value=Decimal(value),
            normalized_unit="mm[Hg]",
            normalization_version="test",
            observed_at=datetime(2025, 6, 10, tzinfo=UTC),
            received_at=datetime.now(UTC),
            review_status=ReviewStatus.PUBLISHED,
            **extra,
        )
        admin_session.add(observation)
        admin_session.flush()
        return observation

    systolic = reading("cardio.systolic_bp", "122")
    diastolic = reading("cardio.diastolic_bp", "78")
    derived = compute_derived(
        admin_session, tenant_id=tenant.id, patient_id=patient_id, formula_id="pulse_pressure.v1"
    )
    assert derived is not None
    reading("cardio.systolic_bp", "132", supersedes_observation_id=systolic.id)
    admin_session.commit()

    archive, data = _open(_export(client, pid))
    rows = {o["id"]: o for o in data["observations"]}
    computed = rows[str(derived.id)]
    assert (computed["computed"], computed["measurement_class"]) == (True, "derived")
    assert computed["derivation"]["formula_id"] == "pulse_pressure.v1"
    assert sorted(i["observation_id"] for i in computed["derivation"]["inputs"]) == sorted(
        [str(systolic.id), str(diastolic.id)]
    )
    # Its basis was corrected since: the package says so, as the staff timeline does.
    assert computed["derivation"]["input_replaced"] is True
    assert rows[str(systolic.id)]["superseded_by_observation_id"] is not None
    assert rows[str(diastolic.id)]["computed"] is False
    readme = archive.read("LIESMICH.txt").decode("utf-8")
    assert "Werte aus Quellen (z. B. Labor): 3 · von der Plattform berechnete Werte: 1" in readme
    assert "computed = true" in readme and "input_replaced = true" in readme


# --- a failure is a failure, not a thinner package ---


class _Outage:
    def get_or_none(self, key: str) -> bytes | None:
        raise BlobUnavailable("object store unreachable")


def test_a_storage_outage_fails_the_export_instead_of_thinning_it(
    client, admin_session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-outage")
    pid = _patient(client, "Ausfall Test (synthetic)")
    _upload_and_import(client, pid, _CSV, "befund.csv")
    monkeypatch.setattr(export_module, "get_blob_store", lambda _settings: _Outage())

    resp = _export(client, pid)
    assert resp.status_code == 503
    assert resp.json()["error"]["detail"].startswith("storage_unavailable")
    # No package, no record of one — only the refusal.
    assert _events(admin_session, "privacy.export") == []
    (refused,) = _events(admin_session, "privacy.export_refused")
    assert refused.detail == {"code": "storage_unavailable", "patient_id": pid}
    assert client.get(f"/api/v1/patients/{pid}/data-exports").json() == []


def test_a_record_too_large_for_one_package_is_refused(client, admin_session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-large")
    pid = _patient(client, "Gross Test (synthetic)")
    _upload_and_import(client, pid, _CSV, "befund.csv")
    monkeypatch.setattr(export_module, "MAX_DOCUMENT_BYTES", len(_CSV) - 1)

    resp = _export(client, pid)
    assert resp.status_code == 409
    assert resp.json()["error"]["detail"].startswith("export_too_large")
    assert [e.detail["code"] for e in _events(admin_session, "privacy.export_refused")] == [
        "export_too_large"
    ]


class _BrokenBody:
    def read(self) -> bytes:
        raise ConnectionResetError("connection reset while reading")


class _S3:
    def __init__(self, failure: str | None) -> None:
        self._failure = failure

    def get_object(self, **_kwargs: Any) -> dict[str, Any]:
        if self._failure is None:
            return {"Body": io.BytesIO(b"bytes")}
        if self._failure == "unreachable":
            raise EndpointConnectionError(endpoint_url="http://synthetic.invalid")
        if self._failure == "broken-read":
            return {"Body": _BrokenBody()}
        raise ClientError({"Error": {"Code": self._failure, "Message": "x"}}, "GetObject")


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (None, b"bytes"),
        ("NoSuchKey", None),
        ("SlowDown", BlobUnavailable),
        ("AccessDenied", BlobUnavailable),
        ("unreachable", BlobUnavailable),
        ("broken-read", BlobUnavailable),
    ],
)
def test_the_object_store_tells_missing_from_unavailable(
    failure: str | None, expected: Any
) -> None:
    store = S3BlobStore.__new__(S3BlobStore)
    store._bucket = "synthetic"
    store._client = _S3(failure)
    if expected is BlobUnavailable:
        with pytest.raises(BlobUnavailable):
            store.get_or_none("k")
    else:
        assert store.get_or_none("k") == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("befund.csv", "befund.csv"),
        ("../../etc/passwd", "passwd"),
        ("..", "original"),
        ("", "original"),
        ("a/b\\..\\c d?.csv", "c d_.csv"),
        ("NUL.txt", "_NUL.txt"),
        ("com1", "_com1"),
        ("x" * 119 + ". evil.csv", "x" * 119),
        ("x" * 118 + " .csv", "x" * 118),
    ],
)
def test_an_archive_entry_name_is_one_safe_path_component(name: str, expected: str) -> None:
    cleaned = _safe_filename(name)
    assert cleaned == expected
    assert "/" not in cleaned and "\\" not in cleaned and len(cleaned) <= 121
    assert not cleaned.endswith((" ", "."))


def test_a_value_typed_from_a_stored_file_is_exported_without_that_file(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-manual")
    pid = _patient(client, "Hand Test (synthetic)")
    # A PDF has no reader: staff type its values in and cite the stored file.
    pdf = _upload(
        client, pid, b"%PDF-1.4 synthetic own report", "eigener-befund.pdf", "application/pdf"
    )
    entered = client.post(
        f"/api/v1/patients/{pid}/imports",
        json={
            "source_document_id": pdf,
            "values": [
                {
                    "original_name": "LDL Cholesterol",
                    "original_value": "2.8",
                    "original_unit": "mmol/L",
                    "observed_at": "2025-06-10T00:00:00Z",
                    "observed_at_is_date_only": True,
                }
            ],
        },
    )
    assert entered.status_code == 201, entered.text

    archive, data = _open(_export(client, pid))
    (value,) = data["observations"]
    # The value is the record's; the file no reader checked is not in the package — and the
    # value says so instead of pointing at something that is not there.
    assert (
        value["original_value"],
        value["source_document_id"],
        value["source_document_withheld"],
    ) == (
        "2.8",
        None,
        True,
    )
    assert data["source_documents"] == [] and data["source_documents_not_imported"] == 1
    visible = _everything(archive)
    assert pdf.encode() not in visible and b"eigener-befund" not in visible


def test_a_manual_entry_can_only_cite_a_file_of_this_patient(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-cite-a")
    first = _patient(client, "Erste Person (synthetic)")
    second = _patient(client, "Zweite Person (synthetic)")
    foreign_document = _upload(client, second, _CSV, "zweite.csv", "text/csv")
    value = {
        "original_name": "LDL Cholesterol",
        "original_value": "2.8",
        "original_unit": "mmol/L",
        "observed_at": "2025-06-10T00:00:00Z",
        "observed_at_is_date_only": True,
    }

    def cite(patient_id: str, document_id: str) -> int:
        resp = client.post(
            f"/api/v1/patients/{patient_id}/imports",
            json={"source_document_id": document_id, "values": [value]},
        )
        return int(resp.status_code)

    # Another patient's file is not a source of this record.
    assert cite(first, foreign_document) == 404
    _owner(client, admin_session, "export-cite-b")
    elsewhere = _patient(client, "Andere Klinik (synthetic)")
    # Nor is another clinic's — and it is invisible.
    assert cite(elsewhere, foreign_document) == 404
    assert admin_session.execute(select(Observation)).scalars().all() == []


def test_a_stored_file_that_no_longer_matches_its_checksum_is_not_shipped(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _owner(client, admin_session, "export-changed")
    pid = _patient(client, "Prüfsumme Test (synthetic)")
    document_id = _upload_and_import(client, pid, _CSV, "befund.csv")
    key = admin_session.execute(select(SourceDocument.storage_key)).scalar_one()
    get_blob_store(get_settings()).put(key, b"something else entirely", "text/csv")

    resp = _export(client, pid)
    assert resp.status_code == 200, resp.text
    archive, data = _open(resp)
    # "Unchanged" is checked: other bytes under this record's key are not handed over.
    assert [(d["id"], d["file"], d["file_problem"]) for d in data["source_documents"]] == [
        (document_id, None, "checksum_mismatch")
    ]
    assert sorted(archive.namelist()) == ["LIESMICH.txt", "export.json"]
    assert b"something else entirely" not in _everything(archive)
    readme = archive.read("LIESMICH.txt").decode("utf-8")
    assert "HINWEIS: 1 eingelesene Originaldatei(en) stimmen nicht mehr mit der beim" in readme
    (entry,) = client.get(f"/api/v1/patients/{pid}/data-exports").json()
    assert (entry["source_files"], entry["source_files_changed"]) == (0, 1)


def test_a_newly_released_version_stands_next_to_the_withdrawn_one(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-rerelease")
    pid = _patient(
        client,
        "Neufassung Test (synthetic)",
        consents=[{"purpose": "report_release", "channel": "in_person"}],
    )
    _upload_and_import(client, pid, _CSV, "befund.csv")

    def as_role(role: Role) -> None:
        email = f"export-rerelease-{role.value}@synthetic.example"
        if admin_session.execute(select(User).where(User.email == email)).first() is None:
            switch_role(client, admin_session, email=email, tenant=tenant, role=role)
        else:
            _back_to(client, tenant, email)

    as_role(Role.CLINICIAN)
    report_id = client.post(f"/api/v1/patients/{pid}/reports").json()["report_id"]
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    as_role(Role.MEDICAL_DIRECTOR)
    assert client.post(f"/api/v1/reports/{report_id}/release").status_code == 200
    as_role(Role.CLINICIAN)
    view = client.get(f"/api/v1/reports/{report_id}").json()
    statements = [
        {
            "id": st["id"],
            "text": "Revised wording of the second version.",
            "evidence_observation_ids": [e["observation_id"] for e in st["evidence"]],
        }
        for st in view["statements"]
    ]
    assert (
        client.post(
            f"/api/v1/reports/{report_id}/edit", json={"statements": statements}
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/reports/{report_id}/approve").status_code == 200
    as_role(Role.MEDICAL_DIRECTOR)
    assert client.post(f"/api/v1/reports/{report_id}/release").status_code == 200

    _back_to(client, tenant, "export-rerelease-owner@synthetic.example")
    _archive, data = _open(_export(client, pid))
    assert [
        (r["version_no"], r["withdrawn"], r["edited_by_clinician"])
        for r in data["released_reports"]
    ] == [(1, True, False), (2, False, True)]


def test_the_demo_note_follows_the_record_not_a_constant(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _owner(client, admin_session, "export-real")
    pid = _patient(client, "Flag Test (synthetic)")
    archive, data = _open(_export(client, pid))
    assert data["synthetic"] is True
    assert "Synthetische Demo-Umgebung" in archive.read("LIESMICH.txt").decode("utf-8")

    # Flip the flags the way a lifted synthetic-only restriction would (test setup only).
    admin_session.execute(
        update(Patient).where(Patient.id == uuid.UUID(pid)).values(is_synthetic=False)
    )
    admin_session.execute(update(Tenant).where(Tenant.id == tenant.id).values(is_synthetic=False))
    admin_session.commit()
    archive, data = _open(_export(client, pid))
    assert data["synthetic"] is False
    assert "Synthetische Demo-Umgebung" not in archive.read("LIESMICH.txt").decode("utf-8")
