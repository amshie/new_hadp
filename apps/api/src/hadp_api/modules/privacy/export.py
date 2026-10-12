"""Patient data export (GDPR Art. 15 access / Art. 20 portability) — the clinic's tool.

The clinic is the controller and answers a data subject's request; this builds the package it
hands over: ONE self-describing ZIP for ONE patient, generated on request and never stored
(its record is the audit event, with the package's checksum). Format `hadp-patient-export`,
version 1 — described in docs/product/DATA_EXPORT.md.

The scope is deliberately the data that is the patient's own, or has already been released to
them: profile, consent events, observations (source and normalized representation, provenance
and review state), the stored original source files that were READ INTO this record, and
report versions that passed the release gate.

Three rules keep the package truthful and keep other people out of it:

- A stored file is shipped only if a reader imported it into this record. The import is the
  only identity check the product has (one person per file; the date of birth, when both the
  file and the record carry one) — weak, but it is a check. A file that was merely uploaded
  here — refused as another person's report, a file for several patients, a format without a
  reader, a file values were only typed from by hand — never passed it: its content, its name
  and its id stay out, and only their number is given.
- A storage failure fails the export. A file that definitely no longer exists, or whose bytes
  no longer match the checksum recorded at upload, is listed without content, and the cover
  note says so.
- A value the platform computed is said to be computed, a value whose basis a laboratory
  correction replaced is marked, and a released version that was later withdrawn is marked.

NOT included — and listed as such inside the package: unreleased report versions, the
clinician's interpretation runs, review decisions, technical import records, the audit trail,
privacy requests, staff identities, invitations and access links. Whether those belong in a
subject-access answer is a DPO/counsel decision (pending). Until then nothing unreleased leaves
through this path: the two-tier physician gate stays the only way clinical content reaches a
patient.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, ServiceUnavailable
from hadp_api.modules.consents import service as consents_service
from hadp_api.modules.documents.blob import BlobUnavailable, get_blob_store
from hadp_api.modules.documents.service import list_source_documents
from hadp_api.modules.enums import KpiMeasurementClass, ReportStatus
from hadp_api.modules.imports.document_import import import_outcome
from hadp_api.modules.observations import service as obs_service
from hadp_api.modules.observations.models import Observation
from hadp_api.modules.patients.models import Patient
from hadp_api.modules.reports import service as reports_service
from hadp_api.modules.tenancy.models import Tenant

FORMAT_NAME = "hadp-patient-export"
FORMAT_VERSION = "1"
# The package is built in memory (about twice the size of the files while it is assembled):
# beyond this the original files do not fit one request.
MAX_DOCUMENT_BYTES = 100 * 1024 * 1024

# What a reader of the package must know is missing, and why (also rendered into LIESMICH.txt).
NOT_INCLUDED: tuple[tuple[str, str, str], ...] = (
    (
        "unreleased_report_versions",
        "Report drafts and versions that were not released to the patient.",
        "Berichtsentwürfe und Fassungen, die nicht an Sie freigegeben wurden",
    ),
    (
        "interpretation_runs",
        "The clinic's unreleased interpretation working documentation.",
        "nicht freigegebene Arbeitsdokumentation der Klinik zur Interpretation",
    ),
    (
        "review_decisions",
        "Individual review decisions (the resulting state of each value is included).",
        "einzelne Prüfentscheidungen (der daraus folgende Stand jedes Werts ist enthalten)",
    ),
    (
        "stored_files_not_imported",
        "Stored files that no reader imported into this record — the product never checked "
        "whose data they hold (their number is given as source_documents_not_imported; a value "
        "typed by hand from such a file is included and marked source_document_withheld).",
        "gespeicherte Dateien, die nicht maschinell in diese Akte eingelesen wurden – die "
        "Plattform hat nie geprüft, wessen Daten sie enthalten",
    ),
    (
        "import_records",
        "Technical records of each import (the original files that were read are included).",
        "technische Protokolle der einzelnen Einlesevorgänge (die eingelesenen Originaldateien "
        "sind enthalten)",
    ),
    (
        "audit_trail",
        "The audit trail of accesses and changes.",
        "das Protokoll der Zugriffe und Änderungen",
    ),
    (
        "privacy_requests",
        "Requests to erase or export this record.",
        "Vorgänge zu Löschung und Datenauskunft dieser Akte",
    ),
    (
        "staff_identities",
        "Names and identifiers of clinic staff.",
        "Namen und Kennungen des Klinikpersonals",
    ),
    (
        "invitations_and_access_links",
        "Invitations and access links (stored only as one-way hashes).",
        "Einladungen und Zugriffslinks (nur als Prüfwerte gespeichert)",
    ),
)


@dataclass(frozen=True)
class PatientExport:
    filename: str
    data: bytes
    checksum_sha256: str
    # Counts only — what the audit event records about the package.
    counts: dict[str, int]


def _instant(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _decimal(value: Decimal | None) -> str | None:
    # Plain notation: str() writes a small magnitude with an exponent ("0E-7").
    return None if value is None else format(value, "f")


_UNSAFE = re.compile(r"[^A-Za-z0-9._ \-äöüÄÖÜß]")
# Names a Windows file system reserves, whatever the extension.
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)


def _safe_filename(name: str) -> str:
    """A file name that is safe as one path component inside the archive (no directories)."""
    base = re.split(r"[\\/]", name)[-1]
    cleaned = _UNSAFE.sub("_", base)[:120].strip(" .")
    if not cleaned:
        return "original"
    return f"_{cleaned}" if _RESERVED.match(cleaned) else cleaned


def _observation(
    observation: Observation,
    *,
    replaced: dict[uuid.UUID, uuid.UUID],
    stale_derived: set[uuid.UUID],
    inputs: dict[uuid.UUID, list[tuple[str, uuid.UUID]]],
    listed_documents: set[uuid.UUID],
) -> dict[str, Any]:
    derived = observation.source_category == KpiMeasurementClass.DERIVED
    # A value may cite a stored file that is not part of the package (typed by hand from a
    # file no reader imported): the value is included, the file's id is not.
    cites_listed = observation.source_document_id in listed_documents
    return {
        "id": str(observation.id),
        # False: reported by a source. True: computed by the platform from other values — the
        # original_* fields then hold the computed result, not a source's writing.
        "computed": derived,
        "original_name": observation.original_name,
        "original_value": observation.original_value,
        "original_unit": observation.original_unit,
        "reference_text": observation.reference_text,
        "observed_at": observation.observed_at.astimezone(UTC).date().isoformat()
        if observation.observed_at_is_date_only
        else _instant(observation.observed_at),
        "observed_at_is_date_only": observation.observed_at_is_date_only,
        "received_at": _instant(observation.received_at),
        # pending = waiting for a clinical decision, rejected = not accepted, published = accepted.
        "review_status": observation.review_status.value,
        "measurement_class": observation.source_category.value
        if observation.source_category is not None
        else None,
        # Measurement context, where the source supplied it.
        "source_system": observation.source_system,
        "method": observation.method,
        "protocol": observation.protocol,
        "device_model": observation.device_model,
        "firmware_or_algorithm_version": observation.firmware_or_algorithm_version,
        "instrument_version": observation.instrument_version,
        "metric_code": observation.metric_code,
        "code_system": observation.code_system,
        "kpi_code": observation.kpi_code,
        "mapping_confidence": observation.mapping_confidence,
        "normalized_value": _decimal(observation.normalized_value),
        "normalized_unit": observation.normalized_unit,
        "reference_low": _decimal(observation.reference_low),
        "reference_high": _decimal(observation.reference_high),
        "normalization_version": observation.normalization_version,
        "derivation": {
            "formula_id": observation.formula_id,
            "formula_version": observation.formula_version,
            "algorithm_name": observation.algorithm_name,
            "inputs": [
                {"role": role, "observation_id": str(input_id)}
                for role, input_id in inputs.get(observation.id, [])
            ],
            # True when a laboratory correction has since replaced one of the inputs: the
            # computed value rests on a value that no longer stands.
            "input_replaced": observation.id in stale_derived,
        }
        if derived
        else None,
        "source_document_id": str(observation.source_document_id) if cites_listed else None,
        "source_document_withheld": observation.source_document_id is not None and not cites_listed,
        "source_record_locator": observation.source_record_locator,
        # Correction lineage: the value this one was sent to correct, and the published
        # correction that has replaced this value.
        "supersedes_observation_id": str(observation.supersedes_observation_id)
        if observation.supersedes_observation_id is not None
        else None,
        "superseded_by_observation_id": str(replaced[observation.id])
        if observation.id in replaced
        else None,
    }


def _readme(
    *, tenant: Tenant, generated_at: datetime, counts: dict[str, int], synthetic: bool
) -> str:
    lines = [
        "Datenauskunft",
        "=============",
        "",
        f"Erstellt am {generated_at.astimezone(UTC).strftime('%d.%m.%Y um %H:%M')} UTC "
        f"durch: {tenant.name}",
        "",
        "Diese Datei enthält zu Ihrer Person in der Plattform gespeicherte Daten. Die Klinik",
        "stellt sie für eine Auskunft (Art. 15 DSGVO) oder eine Datenübertragung (Art. 20 DSGVO)",
        "bereit. Was die Datei nicht enthält, steht unten.",
        "",
        "Inhalt",
        "------",
        "export.json    alle Angaben in maschinenlesbarer Form (Format "
        f"{FORMAT_NAME}, Version {FORMAT_VERSION})",
        f"documents/     {counts['source_files']} eingelesene Originaldatei(en), unverändert "
        "(mit der beim Hochladen gespeicherten Prüfsumme verglichen)",
        "",
        f"Stammdaten: 1 · Einwilligungsvermerke: {counts['consent_events']}",
        f"Werte aus Quellen (z. B. Labor): {counts['observations'] - counts['computed_values']}"
        f" · von der Plattform berechnete Werte: {counts['computed_values']}",
        f"An Sie freigegebene Berichtsfassungen: {counts['released_report_versions']}"
        f" (davon später zurückgezogen: {counts['withdrawn_report_versions']})",
    ]
    if counts["source_files_missing"]:
        lines += [
            "",
            f"HINWEIS: {counts['source_files_missing']} eingelesene Originaldatei(en) sind im "
            "Speicher nicht mehr vorhanden",
            "und fehlen deshalb in dieser Datei. Die daraus gelesenen Werte sind enthalten.",
        ]
    if counts["source_files_changed"]:
        lines += [
            "",
            f"HINWEIS: {counts['source_files_changed']} eingelesene Originaldatei(en) stimmen "
            "nicht mehr mit der beim",
            "Hochladen gespeicherten Prüfsumme überein und fehlen deshalb in dieser Datei.",
        ]
    if counts["source_documents_not_imported"]:
        lines += [
            "",
            f"HINWEIS: {counts['source_documents_not_imported']} gespeicherte Datei(en) wurden "
            "nicht maschinell in diese Akte",
            "eingelesen und sind nicht enthalten (siehe unten).",
        ]
    lines += [
        "",
        "Zu den Werten",
        "-------------",
        "Ein Wert aus einer Quelle steht so da, wie die Quelle ihn geschrieben hat (original_*),",
        "und zusätzlich in umgerechneter Form, wo eine Umrechnung hinterlegt ist.",
        "Ein von der Plattform berechneter Wert ist mit computed = true gekennzeichnet; er wurde",
        "nicht gemessen, sondern aus anderen Werten berechnet (derivation). Steht dort",
        "input_replaced = true, hat das Labor einen der zugrunde liegenden Werte später",
        "korrigiert.",
        "review_status zeigt den Stand: published = übernommen, pending = wartet auf eine",
        "klinische Prüfung, rejected = nicht übernommen. superseded_by_observation_id ist gesetzt,",
        "wenn das Labor den Wert später korrigiert hat.",
        "",
        "Zu den Berichten",
        "----------------",
        "Enthalten sind nur Fassungen, die an Sie freigegeben wurden. withdrawn = true bedeutet:",
        "Die Klinik hat diese Fassung später zurückgezogen oder durch eine neue ersetzt.",
        "",
        "Nicht enthalten",
        "---------------",
    ]
    lines += [f"- {german}" for _key, _english, german in NOT_INCLUDED]
    lines += [
        "",
        "Wenn Sie dazu Fragen haben oder weitere Auskunft wünschen, wenden Sie sich an die Klinik.",
        "",
    ]
    if synthetic:
        lines += ["Synthetische Demo-Umgebung: Die Daten in dieser Datei sind Beispieldaten.", ""]
    return "\n".join(lines)


def build_patient_export(
    db: Session, *, tenant: Tenant, patient: Patient, now: datetime | None = None
) -> PatientExport:
    """Assemble the package for one patient of one tenant (the caller has authorized both)."""
    if patient.erased_at is not None:
        raise Conflict("patient_erased: an erased record has no data to export")
    generated_at = now or datetime.now(UTC)

    # Only a file a reader imported into this record is shipped: an upload alone proves
    # nothing, and the import is the one identity check there is.
    stored = list_source_documents(db, tenant_id=tenant.id, patient_id=patient.id)
    documents = [
        d for d in stored if import_outcome(db, tenant_id=tenant.id, document_id=d.id) is not None
    ]
    if sum(d.byte_size for d in documents) > MAX_DOCUMENT_BYTES:
        raise Conflict("export_too_large: the stored source files exceed the export limit")

    observations = obs_service.list_observations(db, patient.id)
    replaced = obs_service.superseded_by(db, patient.id)
    stale_derived = obs_service.derived_from(db, set(replaced))
    computed = {o.id for o in observations if o.source_category == KpiMeasurementClass.DERIVED}
    inputs = obs_service.derivation_inputs(db, computed)
    consent_events = consents_service.list_consent_events(
        db, tenant_id=tenant.id, patient_id=patient.id
    )
    released = reports_service.released_versions(db, tenant_id=tenant.id, patient_id=patient.id)

    store = get_blob_store(get_settings())
    files: list[tuple[str, bytes]] = []
    document_entries: list[dict[str, Any]] = []
    for document in documents:
        path = f"documents/{document.id}/{_safe_filename(document.filename)}"
        try:
            content = store.get_or_none(document.storage_key)
        except BlobUnavailable as exc:
            # An outage must never produce a package that looks complete.
            raise ServiceUnavailable(
                "storage_unavailable: a stored source file could not be read"
            ) from exc
        # "Unchanged" is checked, not assumed: bytes that no longer match the checksum recorded
        # at upload are not this record's file any more.
        problem: str | None = None
        if content is None:
            problem = "missing"
        elif hashlib.sha256(content).hexdigest() != document.checksum_sha256:
            problem = "checksum_mismatch"
        else:
            files.append((path, content))
        document_entries.append(
            {
                "id": str(document.id),
                "filename": document.filename,
                "content_type": document.content_type,
                "byte_size": document.byte_size,
                "checksum_sha256": document.checksum_sha256,
                "uploaded_at": _instant(document.created_at),
                # null with a stated problem: said, not invented.
                "file": path if problem is None else None,
                "file_problem": problem,
            }
        )

    listed_documents = {d.id for d in documents}
    withdrawn = [
        not (report.status == ReportStatus.RELEASED and report.current_version_id == version.id)
        for report, version in released
    ]
    counts = {
        "consent_events": len(consent_events),
        "observations": len(observations),
        "computed_values": len(computed),
        "source_documents": len(documents),
        "source_files": len(files),
        "source_files_missing": sum(e["file_problem"] == "missing" for e in document_entries),
        "source_files_changed": sum(
            e["file_problem"] == "checksum_mismatch" for e in document_entries
        ),
        "source_documents_not_imported": len(stored) - len(documents),
        "released_report_versions": len(released),
        "withdrawn_report_versions": sum(withdrawn),
    }
    synthetic = bool(patient.is_synthetic or tenant.is_synthetic)
    payload = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "generated_at": _instant(generated_at),
        "synthetic": synthetic,
        "controller": {"tenant_id": str(tenant.id), "name": tenant.name},
        "patient": {
            "id": str(patient.id),
            "display_name": patient.display_name,
            "external_ref": patient.external_ref,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "record_created_at": _instant(patient.created_at),
        },
        "consent_events": [
            {
                "purpose": event.purpose.value,
                "event_type": event.event_type.value,
                "consent_text_version": event.consent_text_version,
                "channel": event.channel,
                "recorded_at": _instant(event.recorded_at),
            }
            for event in consent_events
        ],
        "observations": [
            _observation(
                o,
                replaced=replaced,
                stale_derived=stale_derived,
                inputs=inputs,
                listed_documents=listed_documents,
            )
            for o in observations
        ],
        "source_documents": document_entries,
        # Stored here but never read into this record — counted, never described.
        "source_documents_not_imported": counts["source_documents_not_imported"],
        "released_reports": [
            {
                "report_id": str(report.id),
                "version_no": version.version_no,
                "approved_at": _instant(version.approved_at),
                "released_at": _instant(version.released_at),
                # True: the clinic later withdrew this version or replaced it with a new one.
                "withdrawn": is_withdrawn,
                # Where the wording comes from: the drafting component, and whether a
                # clinician revised it by hand.
                "narrative_provider": version.narrative_provider,
                "narrative_version": version.narrative_version,
                "edited_by_clinician": version.edited_by_user_id is not None,
                "statements": [
                    {
                        "id": statement["id"],
                        "text": statement["text"],
                        "evidence_observation_ids": [
                            str(i) for i in statement.get("evidence_observation_ids") or []
                        ],
                    }
                    for statement in version.body.get("statements", [])
                ],
            }
            for (report, version), is_withdrawn in zip(released, withdrawn, strict=True)
        ],
        "not_included": [
            {"what": key, "description": english} for key, english, _german in NOT_INCLUDED
        ],
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "LIESMICH.txt",
            _readme(tenant=tenant, generated_at=generated_at, counts=counts, synthetic=synthetic),
        )
        archive.writestr("export.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for path, content in files:
            archive.writestr(path, content)
    data = buffer.getvalue()
    return PatientExport(
        filename=f"datenauskunft-{generated_at.astimezone(UTC):%Y%m%d-%H%M%S}.zip",
        data=data,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        counts=counts,
    )
