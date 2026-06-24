"""Source-document service: store the original file before parsing, idempotently."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.errors import ValidationFailed
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument

# Conservative allowlist for the pilot. Structured feeds are preferred over PDF.
ALLOWED_CONTENT_TYPES = {"text/csv", "text/plain", "application/pdf"}
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
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationFailed(f"unsupported content type: {content_type}")
    if len(data) == 0:
        raise ValidationFailed("empty file")
    if len(data) > MAX_BYTES:
        raise ValidationFailed("file too large")
    # Content inspection (not extension-only): text formats must actually be UTF-8 text.
    if content_type in {"text/csv", "text/plain"} and not _looks_like_text(data):
        raise ValidationFailed("declared text content is not valid UTF-8")

    checksum = hashlib.sha256(data).hexdigest()
    existing = db.execute(
        select(SourceDocument).where(
            SourceDocument.tenant_id == tenant_id,
            SourceDocument.checksum_sha256 == checksum,
        )
    ).scalar_one_or_none()
    if existing is not None:
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
