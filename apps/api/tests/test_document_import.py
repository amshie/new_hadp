"""Importing a stored structured laboratory file (CSV / LDT) through the real pipeline.

The reader only transports source values; normalization, the review queue, provenance and
tenant isolation are the existing pipeline's. Properties: all-or-nothing on a structural
problem, exactly-once per document, the file must be this patient's, and nothing the pipeline
cannot carry disappears silently.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from hadp_api.config import get_settings
from hadp_api.modules.audit.models import AuditEvent
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.enums import ImportStatus, ReviewStatus, Role
from hadp_api.modules.imports.models import ImportJob, ImportRow, ReviewItem
from hadp_api.modules.observations.models import Observation
from tests.helpers import login_as, switch_role
from tests.ldt3_fixtures import chemistry, ldt3_file, material, microbiology, reference, value
from tests.ldt3_fixtures import header as ldt3_header
from tests.ldt3_fixtures import report as ldt3_report
from tests.ldt_fixtures import TRAILER, header, lab_test, ldt_file, report

_CSV = (
    b"Analyt;Wert;Einheit;Referenz_von;Referenz_bis;Abnahmedatum\n"
    b"LDL Cholesterol;2,8;mmol/L;0;3,0;10.06.2025\n"
    b"Ferritin;85;ng/mL;30;400;10.06.2025\n"
)


def _clinician(client, admin_session, slug: str):  # type: ignore[no-untyped-def]
    return login_as(
        client,
        admin_session,
        email=f"{slug}@synthetic.example",
        tenant_name=f"{slug} clinic",
        tenant_slug=slug,
        role=Role.CLINICIAN,
    )


def _patient(client, **extra: Any) -> str:  # type: ignore[no-untyped-def]
    body = {"display_name": "Erika Mustermann (synthetic)", **extra}
    resp = client.post("/api/v1/patients", json=body)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _upload(client, patient_id: str, data: bytes, content_type: str, name: str = "labs") -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        f"/api/v1/patients/{patient_id}/documents",
        files={"file": (name, data, content_type)},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def _import(client, patient_id: str, document_id: str):  # type: ignore[no-untyped-def]
    return client.post(f"/api/v1/patients/{patient_id}/documents/{document_id}/import")


def _nothing_imported(admin_session) -> None:  # type: ignore[no-untyped-def]
    assert admin_session.execute(select(ImportJob)).scalars().all() == []
    assert admin_session.execute(select(Observation)).scalars().all() == []


def _refusals(admin_session) -> list[str]:  # type: ignore[no-untyped-def]
    events = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "import.refused")
    ).scalars()
    return [e.detail["code"] for e in events]


def test_csv_import_publishes_mapped_values_and_queues_the_rest(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    user, _tenant = _clinician(client, admin_session, "csv-import")
    pid = _patient(client)
    doc_id = _upload(client, pid, _CSV, "text/csv")

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (body["parser_name"], body["parser_version"]) == ("hadp-csv", "1")
    assert (body["published_count"], body["review_count"], body["not_imported_count"]) == (1, 1, 0)
    assert body["created"] is True

    by_name = {
        o.original_name: o for o in admin_session.execute(select(Observation)).scalars().all()
    }
    ldl, ferritin = by_name["LDL Cholesterol"], by_name["Ferritin"]
    # The source representation is the file's, verbatim; the normalized value is separate.
    assert (ldl.original_value, ldl.original_unit) == ("2,8", "mmol/L")
    assert ldl.normalized_value == Decimal("2.8")
    assert ldl.reference_high == Decimal("3.0")
    assert ldl.review_status == ReviewStatus.PUBLISHED
    assert ldl.source_record_locator == "line 2"
    assert str(ldl.source_document_id) == doc_id
    assert ldl.observed_at_is_date_only is True
    # An analyte the terminology does not know is never published on a guess.
    assert ferritin.review_status == ReviewStatus.PENDING
    assert ferritin.source_record_locator == "line 3"
    reasons = admin_session.execute(select(ReviewItem.reason)).scalars().all()
    assert reasons == ["unmapped_metric"]

    job = admin_session.execute(select(ImportJob)).scalars().one()
    assert (job.parser_name, job.parser_version) == ("hadp-csv", "1")
    assert job.created_by_user_id == user.id
    audit = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "import.run")
    ).scalar_one()
    assert audit.detail == {
        "published": 1,
        "review": 1,
        "not_imported": 0,
        "parser": "hadp-csv",
        "parser_version": "1",
    }


def test_a_document_is_imported_exactly_once(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "once")
    pid = _patient(client)
    doc_id = _upload(client, pid, _CSV, "text/csv")
    first = _import(client, pid, doc_id)
    assert first.status_code == 201

    again = _import(client, pid, doc_id)
    assert again.status_code == 200, again.text
    assert again.json() == {**first.json(), "created": False}

    assert len(admin_session.execute(select(Observation)).scalars().all()) == 2
    assert len(admin_session.execute(select(ImportJob)).scalars().all()) == 1
    audits = admin_session.execute(
        select(AuditEvent).where(AuditEvent.action == "import.run")
    ).scalars()
    assert len(audits.all()) == 1  # the repeat wrote nothing


def test_ldt_import_keeps_review_and_not_imported_results_visible(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "ldt-import")
    pid = _patient(client, date_of_birth="1980-01-15")
    data = ldt_file(
        header(),
        report(
            lab_test("LDL", "LDL Cholesterol", value="2.8", unit="mmol/L", low="0", high="3.0"),
            lab_test(
                "LDL", "LDL Cholesterol", value="3.6", unit="mmol/L", day="20250115", status="K"
            ),
            lab_test("HB", "Hämoglobin", value="14.2", unit="g/dl", reference=("12.0 - 16.0",)),
            lab_test("URIN", "Urinstatus", text=("unauffällig",)),
            lab_test("TSH", "TSH basal", status="F"),
        ),
        TRAILER,
    )
    # A browser sends an .ldt file without a useful content type: the content decides.
    doc_id = _upload(client, pid, data, "application/octet-stream", name="befund.ldt")

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["parser_name"] == "ldt2-8201"
    assert (body["published_count"], body["review_count"], body["not_imported_count"]) == (1, 2, 2)

    observations = admin_session.execute(select(Observation)).scalars().all()
    by_value = {o.original_value: o for o in observations}
    assert by_value["2.8"].review_status == ReviewStatus.PUBLISHED
    # A value the laboratory marked as corrected is a human's call, never auto-published.
    assert by_value["3.6"].review_status == ReviewStatus.PENDING
    assert by_value["14.2"].original_name == "Hämoglobin"
    assert by_value["14.2"].reference_text == "12.0 - 16.0"
    reasons = sorted(admin_session.execute(select(ReviewItem.reason)).scalars().all())
    assert reasons == ["corrected_result", "unmapped_metric"]

    skipped = admin_session.execute(
        select(ImportRow).where(ImportRow.status == ImportStatus.REJECTED)
    ).scalars()
    assert sorted(r.raw["not_imported_reason"] for r in skipped) == [
        "result_pending",
        "text_result",
    ]

    # The file's patient name is not copied anywhere outside the stored original.
    for row in admin_session.execute(select(ImportRow)).scalars():
        assert "Mustermann" not in str(row.raw)

    assert _import(client, pid, doc_id).json()["not_imported_count"] == 2  # replay keeps it


def test_ldt3_import_takes_the_sampling_time_and_the_si_value(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "ldt3-import")
    pid = _patient(client, date_of_birth="1980-01-15")
    data = ldt3_file(
        ldt3_header(),
        ldt3_report(
            material("S1"),  # sampled 2025-06-10 08:15 UTC+2
            chemistry(
                "GLUC",
                "Glucose",
                value("101", "mg/dl", system="2", references=(reference("60.0", "125.0"),)),
                value("5.6", "mmol/l", system="1", references=(reference("3.3", "6.9"),)),
            ),
            chemistry("LDL", "LDL Cholesterol", value("2.8"), status="08"),
            microbiology(),
        ),
    )
    doc_id = _upload(client, pid, data, "application/octet-stream", name="Z01befund.ldt")

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["parser_name"] == "ldt3-8205"
    # Not imported: the microbiology result and the mg/dl writing of the glucose value.
    assert (body["published_count"], body["review_count"], body["not_imported_count"]) == (1, 1, 2)

    by_name = {
        o.original_name: o for o in admin_session.execute(select(Observation)).scalars().all()
    }
    glucose, ldl = by_name["Glucose"], by_name["LDL Cholesterol"]
    # One measurement, one observation: the SI value with its own range, at the sampling time.
    assert (glucose.original_value, glucose.original_unit) == ("5.6", "mmol/l")
    assert (glucose.reference_low, glucose.reference_high) == (Decimal("3.3"), Decimal("6.9"))
    assert glucose.observed_at.isoformat() == "2025-06-10T06:15:00+00:00"
    assert glucose.observed_at_is_date_only is False
    assert glucose.review_status == ReviewStatus.PUBLISHED
    # A result the laboratory marks as replacing earlier ones waits for a human.
    assert ldl.review_status == ReviewStatus.PENDING
    assert admin_session.execute(select(ReviewItem.reason)).scalars().all() == ["corrected_result"]
    skipped = admin_session.execute(
        select(ImportRow).where(ImportRow.status == ImportStatus.REJECTED)
    ).scalars()
    assert sorted(r.raw["not_imported_reason"] for r in skipped) == [
        "alternate_unit_value",
        "unsupported_result_type",
    ]

    # A file whose bytes were altered after the laboratory wrote it imports nothing.
    tampered = data.replace(b"5.6", b"9.6")
    bad_id = _upload(client, pid, tampered, "application/octet-stream", name="Z01x.ldt")
    refused = _import(client, pid, bad_id)
    assert refused.status_code == 422
    assert refused.json()["error"]["detail"].startswith("checksum_mismatch")
    assert len(admin_session.execute(select(ImportJob)).scalars().all()) == 1


def test_a_file_with_another_date_of_birth_is_refused(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "dob-guard")
    pid = _patient(client, date_of_birth="1975-03-02")
    data = ldt_file(header(), report(lab_test("LDL", value="2.8")), TRAILER)  # born 1980-01-15
    doc_id = _upload(client, pid, data, "text/plain")

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "conflict"
    _nothing_imported(admin_session)
    # The attempt leaves a trace even though the request rolled back.
    assert _refusals(admin_session) == ["patient_mismatch"]


def test_a_structural_problem_imports_nothing_and_echoes_no_content(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "all-or-nothing")
    pid = _patient(client)
    broken = (
        b"name;value;date\n"
        b"LDL Cholesterol;2,8;10.06.2025\n"
        b"ZZ-secret-analyte;ZZ-secret-value;06/10/2025\n"
    )
    doc_id = _upload(client, pid, broken, "text/csv")

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 422, resp.text
    error = resp.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["detail"].startswith("unsupported_date: line 3")
    assert "ZZ-secret" not in resp.text
    # The valid first row is not imported either: a file is read whole or not at all.
    _nothing_imported(admin_session)
    assert _refusals(admin_session) == ["unsupported_date"]


def test_a_pdf_has_no_structured_reader(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "pdf")
    pid = _patient(client)
    doc_id = _upload(client, pid, b"%PDF-1.7\nsynthetic", "application/pdf")
    resp = _import(client, pid, doc_id)
    assert resp.status_code == 422
    assert resp.json()["error"]["detail"].startswith("unsupported_format")
    _nothing_imported(admin_session)


def test_the_document_must_belong_to_this_patient_and_tenant(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "owner-a")
    patient_a = _patient(client)
    patient_b = _patient(client, display_name="Second Patient (synthetic)")
    doc_id = _upload(client, patient_a, _CSV, "text/csv")

    # Same clinic, other patient: the document is not that patient's.
    assert _import(client, patient_b, doc_id).status_code == 404

    # Another clinic cannot reach the document at all.
    _clinician(client, admin_session, "owner-b")
    foreign_patient = _patient(client)
    assert _import(client, patient_a, doc_id).status_code == 404
    assert _import(client, foreign_patient, doc_id).status_code == 404
    _nothing_imported(admin_session)


def test_the_medical_director_cannot_run_imports(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _user, tenant = _clinician(client, admin_session, "md-gate")
    pid = _patient(client)
    doc_id = _upload(client, pid, _CSV, "text/csv")
    switch_role(
        client,
        admin_session,
        email="md-gate-director@synthetic.example",
        tenant=tenant,
        role=Role.MEDICAL_DIRECTOR,
    )
    assert _import(client, pid, doc_id).status_code == 403
    _nothing_imported(admin_session)


def test_upload_still_refuses_unknown_binary_content(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "upload-guard")
    pid = _patient(client)
    for payload in (
        b"\x00\x01\x02 not a laboratory file",
        # Opens like an LDT file, then is anything: a prefix is not a file format.
        b"01380008220\r\n" + bytes(range(256)),
        b"0138000" + bytes(range(256)),
    ):
        resp = client.post(
            f"/api/v1/patients/{pid}/documents",
            files={"file": ("x.bin", payload, "application/octet-stream")},
        )
        assert resp.status_code == 422, payload[:12]
        assert "octet-stream" not in resp.text  # the declared type is not echoed


def test_an_ldt_upload_is_stored_under_a_fixed_content_type(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "ldt-type")
    pid = _patient(client)
    data = ldt_file(header(), report(lab_test("LDL", value="2.8")), TRAILER)
    _upload(client, pid, data, "application/x-whatever; " + "x" * 300, name="befund.ldt")
    stored = admin_session.execute(select(SourceDocument.content_type)).scalar_one()
    assert stored == "application/x-ldt"  # never the client's declaration


def test_a_document_whose_stored_file_is_gone_is_refused_cleanly(client, admin_session) -> None:  # type: ignore[no-untyped-def]
    _clinician(client, admin_session, "blob-gone")
    pid = _patient(client)
    doc_id = _upload(client, pid, _CSV, "text/csv")
    key = admin_session.execute(select(SourceDocument.storage_key)).scalar_one()
    get_blob_store(get_settings()).delete(key)

    resp = _import(client, pid, doc_id)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["detail"].startswith("document_unavailable")
    _nothing_imported(admin_session)
    assert _refusals(admin_session) == ["document_unavailable"]
