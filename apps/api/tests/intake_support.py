"""Loader and fakes for the intake golden cases (tests/intake_cases/<case>/).

A case is: `input/report.pdf` (synthetic), `input/pages.json` (the page texts a reader produced
from it), `input/patient.json` (what the record holds: date of birth, published values, the
TEST-ONLY bounds), `input/proposal.json` (a fixed proposal, the shape the agent's write tool
takes), `expected.json` (the checked batch, bit for bit) and `rubric.md`. The deterministic
layer is exercised from these files without a database or a model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from hadp_api.modules.intake import checks
from hadp_api.modules.intake.schemas import ProposedBatchIn
from hadp_api.modules.kpi.service import seed_terminology

CASES_DIR = Path(__file__).parent / "intake_cases"


def case_dirs() -> list[Path]:
    return sorted(p for p in CASES_DIR.iterdir() if (p / "input").is_dir())


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class FakePages:
    texts: tuple[str, ...]
    # Where the recorded text came from: the reader named in pages.json (tesseract = OCR).
    kind: str = "text_layer"

    @property
    def page_count(self) -> int:
        return len(self.texts)

    def text(self, page: int) -> str:
        return self.texts[page - 1] if 1 <= page <= len(self.texts) else ""

    def source(self, page: int) -> str:
        return self.kind if self.text(page).strip() else "none"


@dataclass(frozen=True)
class FakeBounds:
    table: dict[str, checks.PlausibilityBound]

    def for_kpi(self, kpi_code: str) -> checks.PlausibilityBound | None:
        return self.table.get(kpi_code)


@dataclass(frozen=True)
class _Published:
    kpi_code: str | None
    analyte_key: str
    day: date
    value_text: str
    unit_text: str | None
    held_value: Decimal
    held_unit: str


@dataclass(frozen=True)
class FakeRecord:
    _date_of_birth: date | None
    published: tuple[_Published, ...]

    @property
    def date_of_birth(self) -> date | None:
        return self._date_of_birth

    def last_published(self, kpi_code: str) -> checks.PriorValue | None:
        rows = sorted((p for p in self.published if p.kpi_code == kpi_code), key=lambda p: p.day)
        if not rows:
            return None
        last = rows[-1]
        return checks.PriorValue(
            value=last.held_value,
            unit=last.held_unit,
            observed_at=datetime(last.day.year, last.day.month, last.day.day, tzinfo=UTC),
        )

    def is_published(
        self,
        *,
        kpi_code: str | None,
        analyte_key: str,
        day: date | None,
        value_text: str,
        unit_text: str | None,
    ) -> bool:
        return any(
            ((kpi_code is not None and p.kpi_code == kpi_code) or p.analyte_key == analyte_key)
            and p.day == day
            and p.value_text == value_text
            and p.unit_text == unit_text
            for p in self.published
        )


@dataclass(frozen=True)
class LoadedCase:
    name: str
    path: Path
    proposal: ProposedBatchIn
    batch: checks.ProposedBatch
    pages: FakePages
    bounds: FakeBounds
    record: FakeRecord
    today: date


def _observed_at(value: datetime | None, date_only: bool) -> datetime | None:
    if value is None:
        return None
    if date_only:
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def to_batch(proposal: ProposedBatchIn) -> checks.ProposedBatch:
    return checks.ProposedBatch(
        patient_date_of_birth=proposal.patient_date_of_birth,
        issue_date=proposal.issue_date,
        values=tuple(
            checks.ProposedValue(
                analyte_text=v.analyte_text,
                value_text=v.value_text,
                unit_text=v.unit_text,
                observed_at=_observed_at(v.observed_at, v.observed_at_is_date_only),
                observed_at_is_date_only=v.observed_at_is_date_only,
                page=v.page,
                confidence=v.confidence,
                reference_low=v.reference_low,
                reference_high=v.reference_high,
                reference_text=v.reference_text,
                bbox=v.bbox,
            )
            for v in proposal.values
        ),
    )


def load_case(path: Path) -> LoadedCase:
    inp = path / "input"
    proposal = ProposedBatchIn.model_validate(_read(inp / "proposal.json"))
    pages = _read(inp / "pages.json")
    patient = _read(inp / "patient.json")
    bounds = {
        code: checks.PlausibilityBound(
            unit=b["unit"],
            hard_low=Decimal(b["hard_low"]) if b.get("hard_low") is not None else None,
            hard_high=Decimal(b["hard_high"]) if b.get("hard_high") is not None else None,
            delta_max_relative=(
                Decimal(b["delta_max_relative"])
                if b.get("delta_max_relative") is not None
                else None
            ),
        )
        for code, b in patient.get("test_bounds", {}).items()
        if not code.startswith("_")
    }
    dob = patient["patient"].get("date_of_birth")
    published = tuple(
        _Published(
            kpi_code=p.get("kpi_code"),
            analyte_key=checks.analyte_key(p["analyte_text"]),
            day=date.fromisoformat(p["observed_at"]),
            value_text=" ".join(p["value_text"].split()),
            unit_text=p.get("unit_text"),
            held_value=Decimal(p["held_value"]),
            held_unit=p["held_unit"],
        )
        for p in patient.get("published", [])
    )
    return LoadedCase(
        name=path.name,
        path=path,
        proposal=proposal,
        batch=to_batch(proposal),
        pages=FakePages(
            tuple(pages["pages"]),
            "ocr" if str(pages["reader"]).startswith("tesseract") else "text_layer",
        ),
        bounds=FakeBounds(bounds),
        record=FakeRecord(date.fromisoformat(dob) if dob else None, published),
        today=date.fromisoformat(patient["today"]),
    )


def run_case(case: LoadedCase) -> checks.CheckedBatch:
    return checks.run_checks(
        case.batch,
        terminology=seed_terminology(),
        bounds=case.bounds,
        record=case.record,
        pages=case.pages,
        today=case.today,
    )


def _dec(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def serialize(checked: checks.CheckedBatch) -> dict[str, Any]:
    """The checked batch as the golden file holds it: every number as exact text."""
    return {
        "checks_version": checks.CHECKS_VERSION,
        "batch_checks": [c.as_dict() for c in checked.checks],
        "values": [
            {
                "analyte_text": v.proposal.analyte_text,
                "value_text": v.proposal.value_text,
                "unit_text": v.proposal.unit_text,
                "page": v.proposal.page,
                "kpi_code": v.kpi_code,
                "canonical_unit": v.canonical_unit,
                "normalized_value": _dec(v.normalized_value),
                "normalized_reference_low": _dec(v.normalized_reference_low),
                "normalized_reference_high": _dec(v.normalized_reference_high),
                "status": v.status.value,
                "reasons": [c.reason for c in v.checks if c.reason is not None],
                "checks": [c.as_dict() for c in v.checks],
            }
            for v in checked.values
        ],
    }
