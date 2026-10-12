"""Source-document service: store the original file before parsing, idempotently."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import Conflict, ValidationFailed
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.documents.xdt import is_wellformed_xdt

# Conservative allowlist for the pilot. Structured feeds are preferred over PDF.
ALLOWED_CONTENT_TYPES = {"text/csv", "text/plain", "application/pdf"}
# Stored for a file that IS an LDT file, whatever type the client declared for it.
LDT_CONTENT_TYPE = "application/x-ldt"
MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _looks_like_text(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def store_source_document(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    patient_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    uploaded_by_user_id: uuid.UUID,
) -> tuple[SourceDocument, bool]:
    """Validate, checksum, store the blob, and persist a SourceDocument.

    Returns (document, created). Idempotent: identical content within a tenant returns the
    existing document without re-storing (CLAUDE.md ingestion rules).
    """
    # Content inspection decides for the LDT line format: browsers send such files without a
    # useful content type, and they use the character set the file itself declares. Only a
    # file whose EVERY line is well-formed counts, and it is stored under a fixed type — the
    # client's declaration is neither trusted nor kept.
    if len(data) == 0:
        raise ValidationFailed("empty file")
    if len(data) > MAX_BYTES:
        raise ValidationFailed("file too large")
    is_xdt = is_wellformed_xdt(data)
    if is_xdt:
        content_type = LDT_CONTENT_TYPE
    elif content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationFailed("unsupported content type")
    # Content inspection (not extension-only): text formats must actually be UTF-8 text.
    if content_type in {"text/csv", "text/plain"} and not is_xdt and not _looks_like_text(data):
        raise ValidationFailed("declared text content is not valid UTF-8")

    checksum = hashlib.sha256(data).hexdigest()
    existing = db.execute(
        select(SourceDocument).where(
            SourceDocument.tenant_id == tenant_id,
            SourceDocument.checksum_sha256 == checksum,
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.patient_id != patient_id:
            # One stored file per clinic and content: handing back another patient's document
            # here would attach that patient's file (and its name) to this one.
            raise Conflict(
                "document_other_patient: this file is already stored for another patient"
            )
        return existing, False

    storage_key = f"{tenant_id}/{patient_id}/{checksum}"
    get_blob_store(get_settings()).put(storage_key, data, content_type)

    document = SourceDocument(
        tenant_id=tenant_id,
        patient_id=patient_id,
        filename=filename,
        content_type=content_type,
        byte_size=len(data),
        checksum_sha256=checksum,
        storage_key=storage_key,
        uploaded_by_user_id=uploaded_by_user_id,
        is_synthetic=True,
    )
    db.add(document)
    db.flush()
    return document, True


def list_source_documents(
    db: Session, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
) -> list[SourceDocument]:
    """The patient's stored source documents, newest first (metadata only, never content)."""
    return list(
        db.execute(
            select(SourceDocument)
            .where(
                SourceDocument.tenant_id == tenant_id,
                SourceDocument.patient_id == patient_id,
            )
            .order_by(SourceDocument.created_at.desc(), SourceDocument.id)
        ).scalars()
    )
