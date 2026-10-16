"""The agent's tools — the whole list, and nothing else.

An extraction run is bound to ONE stored document of ONE patient in ONE clinic (`IntakeScope`),
and acts under the identity of the staff member whose request started it. Inside that scope the
agent has three reads and one write:

- `read_document(document_id)` — the page texts (text layer) and page images of the bound document.
- `get_atlas_kpi(query)` — catalog entries a name may mean: KPI code, canonical unit, aliases,
  verified LOINC codes. Reference data; it answers what a name MAY mean, never what a value is.
- `get_last_locked(patient_id, kpi_code)` — the last published value of this patient for a KPI,
  as context for the proposal.
- `create_pending_batch(...)` — the one write: a proposal, checked by code, into `pending_values`.
  Usable once per run.

There is no tool that confirms, locks, publishes or edits a value, no tool that reads another
patient, no file write and no network: a prompt injection inside a PDF has nothing to call. The
list `TOOL_NAMES` is the contract the MCP server exposes and the red-team tests count.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import pdfplumber
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from hadp_api.config import get_settings
from hadp_api.db.engine import get_sessionmaker, set_tenant_context
from hadp_api.errors import NotFound, ValidationFailed
from hadp_api.modules.audit.service import record_audit
from hadp_api.modules.documents.blob import get_blob_store
from hadp_api.modules.documents.models import SourceDocument
from hadp_api.modules.documents.pdf_text import MAX_PAGES, PdfUnreadable, read_pages
from hadp_api.modules.enums import KpiExternalCodeStatus, KpiStatus
from hadp_api.modules.intake import service
from hadp_api.modules.intake.schemas import ProposedBatchIn
from hadp_api.modules.kpi.models import KpiAlias, KpiCatalog, KpiExternalCode
from hadp_api.modules.patients.models import Patient

TOOL_NAMES: tuple[str, ...] = (
    "read_document",
    "get_atlas_kpi",
    "get_last_locked",
    "create_pending_batch",
)
# Page images for the model: enough to read a laboratory table, small enough to send.
IMAGE_DPI = 110
MAX_ATLAS_RESULTS = 20


class ToolError(Exception):
    """A tool refused. `code` is from a closed set; `detail` names no document content."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class IntakeScope:
    """What one extraction run may touch, and who it acts for."""

    tenant_id: uuid.UUID
    patient_id: uuid.UUID
    document_id: uuid.UUID
    actor_user_id: uuid.UUID
    extraction_provider: str
    model_id: str
    prompt_version: str


@dataclass(frozen=True)
class PageView:
    page: int
    text: str
    image_png: bytes | None


@dataclass(frozen=True)
class DocumentView:
    document_id: uuid.UUID
    page_count: int
    pages: tuple[PageView, ...]


@dataclass(frozen=True)
class AtlasEntry:
    kpi_code: str
    display_name: str
    canonical_unit: str | None
    measurement_class: str
    aliases: tuple[str, ...]
    loinc: tuple[str, ...]
    exact: bool


@dataclass(frozen=True)
class LastLocked:
    observation_id: uuid.UUID
    kpi_code: str
    value: Decimal
    unit: str
    observed_at: str


@dataclass(frozen=True)
class BatchOutcome:
    batch_id: uuid.UUID
    green: int
    yellow: int
    red: int
    values: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def _uuid(value: str | uuid.UUID, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ToolError("invalid_argument", f"{what} is not an id") from exc


class IntakeTools:
    """The registry. Every public tool opens its own tenant-bound session under the application
    role (RLS applies) and closes it; the one write commits."""

    def __init__(self, scope: IntakeScope, *, today: date | None = None) -> None:
        self.scope = scope
        self._today = today
        self._write_used = False

    # --- dispatch ---------------------------------------------------------------------------

    @staticmethod
    def names() -> tuple[str, ...]:
        return TOOL_NAMES

    def call(self, name: str, **arguments: Any) -> Any:
        """Call a tool by name. A name not in TOOL_NAMES is refused — there is no hidden tool."""
        if name not in TOOL_NAMES:
            raise ToolError("unknown_tool", f"no tool named {name!r}")
        return getattr(self, name)(**arguments)

    # --- sessions ---------------------------------------------------------------------------

    def _session(self) -> Session:
        session = get_sessionmaker()()
        set_tenant_context(session, self.scope.tenant_id, self.scope.actor_user_id)
        return session

    def _bound_document(self, db: Session, document_id: str | uuid.UUID) -> SourceDocument:
        wanted = _uuid(document_id, "document_id")
        if wanted != self.scope.document_id:
            raise ToolError("out_of_scope", "this run is bound to one document")
        document = db.execute(
            select(SourceDocument).where(
                SourceDocument.id == wanted,
                SourceDocument.tenant_id == self.scope.tenant_id,
                SourceDocument.patient_id == self.scope.patient_id,
            )
        ).scalar_one_or_none()
        if document is None:
            raise ToolError("not_found", "document not found")
        return document

    # --- the three reads --------------------------------------------------------------------

    def read_document(self, document_id: str, with_images: bool = True) -> DocumentView:
        db = self._session()
        try:
            document = self._bound_document(db, document_id)
            store = get_blob_store(get_settings())
            if not store.exists(document.storage_key):
                raise ToolError("unavailable", "the stored file cannot be read")
            data = store.get(document.storage_key)
            try:
                pages = read_pages(data)
            except PdfUnreadable as exc:
                raise ToolError("unreadable", exc.detail) from exc
            images: list[bytes | None] = [None] * pages.page_count
            if with_images:
                images = _render_pages(data, pages.page_count)
            record_audit(
                db,
                action="intake.document_read",
                actor_user_id=self.scope.actor_user_id,
                tenant_id=self.scope.tenant_id,
                target_type="source_document",
                target_id=document.id,
                detail={"page_count": pages.page_count, "with_images": with_images},
            )
            db.commit()
            return DocumentView(
                document_id=document.id,
                page_count=pages.page_count,
                pages=tuple(
                    PageView(page=i + 1, text=pages.texts[i], image_png=images[i])
                    for i in range(pages.page_count)
                ),
            )
        finally:
            db.close()

    def get_atlas_kpi(self, query: str) -> list[AtlasEntry]:
        needle = " ".join(str(query).split()).casefold()
        if not needle:
            raise ToolError("invalid_argument", "query is empty")
        db = self._session()
        try:
            exact = (
                db.execute(
                    select(KpiAlias.kpi_code).where(
                        KpiAlias.alias_normalized == needle, KpiAlias.source_system == ""
                    )
                )
                .scalars()
                .all()
            )
            like = f"%{needle}%"
            codes = (
                db.execute(
                    select(KpiCatalog.code)
                    .outerjoin(KpiAlias, KpiAlias.kpi_code == KpiCatalog.code)
                    .where(
                        KpiCatalog.status == KpiStatus.ACTIVE,
                        or_(
                            KpiCatalog.code.ilike(like),
                            KpiCatalog.display_name.ilike(like),
                            KpiAlias.alias_normalized.ilike(like),
                        ),
                    )
                    .distinct()
                    .order_by(KpiCatalog.code)
                    .limit(MAX_ATLAS_RESULTS)
                )
                .scalars()
                .all()
            )
            ordered = list(dict.fromkeys([*exact, *codes]))
            out: list[AtlasEntry] = []
            for code in ordered:
                kpi = db.get(KpiCatalog, code)
                if kpi is None or kpi.status != KpiStatus.ACTIVE:
                    continue
                aliases = (
                    db.execute(
                        select(KpiAlias.alias_normalized)
                        .where(KpiAlias.kpi_code == code, KpiAlias.source_system == "")
                        .order_by(KpiAlias.alias_normalized)
                    )
                    .scalars()
                    .all()
                )
                loinc = (
                    db.execute(
                        select(KpiExternalCode.external_code)
                        .where(
                            KpiExternalCode.kpi_code == code,
                            KpiExternalCode.code_system == "LOINC",
                            KpiExternalCode.verification_status == KpiExternalCodeStatus.VERIFIED,
                        )
                        .order_by(KpiExternalCode.external_code)
                    )
                    .scalars()
                    .all()
                )
                out.append(
                    AtlasEntry(
                        kpi_code=code,
                        display_name=kpi.display_name,
                        canonical_unit=kpi.canonical_unit_ucum,
                        measurement_class=kpi.measurement_class.value,
                        aliases=tuple(aliases),
                        loinc=tuple(loinc),
                        exact=code in exact,
                    )
                )
            return out
        finally:
            db.close()

    def get_last_locked(self, patient_id: str, kpi_code: str) -> LastLocked | None:
        if _uuid(patient_id, "patient_id") != self.scope.patient_id:
            raise ToolError("out_of_scope", "this run is bound to one patient")
        db = self._session()
        try:
            patient = db.get(Patient, self.scope.patient_id)
            if patient is None:
                raise ToolError("not_found", "patient not found")
            prior = service.record_view(db, patient).last_published(str(kpi_code))
            record_audit(
                db,
                action="intake.last_value_read",
                actor_user_id=self.scope.actor_user_id,
                tenant_id=self.scope.tenant_id,
                detail={
                    "patient_id": str(self.scope.patient_id),
                    "kpi_code": str(kpi_code),
                    "found": prior is not None,
                },
            )
            db.commit()
            if prior is None or prior.observation_id is None or prior.observed_at is None:
                return None
            return LastLocked(
                observation_id=prior.observation_id,
                kpi_code=str(kpi_code),
                value=prior.value,
                unit=prior.unit,
                observed_at=prior.observed_at.isoformat(),
            )
        finally:
            db.close()

    # --- the one write ----------------------------------------------------------------------

    def create_pending_batch(
        self,
        document_id: str,
        values: list[dict[str, Any]],
        patient_date_of_birth: str | None = None,
        issue_date: str | None = None,
    ) -> BatchOutcome:
        """Validate the proposal, run the checks, write the batch. Once per run. The model, the
        prompt and the provider are stamped from the scope — the agent does not say who it is."""
        if self._write_used:
            raise ToolError("write_already_used", "this run has already proposed its batch")
        try:
            proposal = ProposedBatchIn.model_validate(
                {
                    "extraction_provider": self.scope.extraction_provider,
                    "model_id": self.scope.model_id,
                    "prompt_version": self.scope.prompt_version,
                    "patient_date_of_birth": patient_date_of_birth,
                    "issue_date": issue_date,
                    "values": values,
                }
            )
        except ValidationError as exc:
            # Field names and error types only — never the offending input.
            where = sorted(
                {".".join(str(p) for p in e["loc"]) + ":" + e["type"] for e in exc.errors()}
            )
            raise ToolError("invalid_proposal", "; ".join(where)[:500]) from exc
        db = self._session()
        try:
            self._bound_document(db, document_id)
            try:
                result = service.create_pending_batch(
                    db,
                    tenant_id=self.scope.tenant_id,
                    patient_id=self.scope.patient_id,
                    document_id=self.scope.document_id,
                    proposal=proposal,
                    created_by_user_id=self.scope.actor_user_id,
                    today=self._today,
                )
            except (NotFound, ValidationFailed) as exc:
                db.rollback()
                raise ToolError("refused", str(exc)) from exc
            # Read back inside the same transaction: the commit ends the tenant binding.
            rows = service.pending_values_of(db, self.scope.tenant_id, result.batch_id)
            db.commit()
            self._write_used = True
            return BatchOutcome(
                batch_id=result.batch_id,
                green=result.green,
                yellow=result.yellow,
                red=result.red,
                values=tuple(
                    {
                        "row_index": r.row_index,
                        "analyte_text": r.proposed_analyte_text,
                        "status": r.status.value,
                        "reasons": [c["reason"] for c in r.checks if c.get("reason")],
                    }
                    for r in rows
                ),
            )
        finally:
            db.close()


def _render_pages(data: bytes, page_count: int) -> list[bytes | None]:
    if page_count > MAX_PAGES:
        return [None] * page_count
    images: list[bytes | None] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            buf = io.BytesIO()
            page.to_image(resolution=IMAGE_DPI).original.save(buf, format="PNG")
            images.append(buf.getvalue())
    return images
