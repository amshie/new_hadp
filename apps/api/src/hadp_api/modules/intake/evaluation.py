"""Extraction evaluation over the golden cases — deterministic, repeatable, append-only.

For every case a provider reads the committed PDF `runs` times. Each proposal is scored
against `input/truth.json` (what is printed) with code, not with a model:

- **per-field accuracy** over the truth values a proposal matched (by analyte, letter case
  aside): value, unit, date, reference bounds — exact text, the way the checks compare;
- **recall / precision** of values: matched truth values over all truth values, and over all
  proposed values;
- **hallucination**: a proposed value whose analyte or number does not stand verbatim on the
  page it cites (`checks.value_on_page` / `text_on_page`), counted and rated;
- **document fields**: the date of birth and the issue date as printed;
- **variance**: how many distinct proposals the runs produced, and the spread of the per-run
  scores.

One record per (provider, case) run is APPENDED to a JSON-lines file; the file is never
rewritten (it is part of the evidence trail). Records carry the model id and prompt version
the provider stamps, and the checks' version.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from hadp_api.config import Settings
from hadp_api.modules.intake import checks
from hadp_api.modules.intake.pages import OcrEngine, PageSet, load_pages
from hadp_api.modules.intake.providers import ExtractionProvider
from hadp_api.modules.intake.schemas import ProposedBatchIn, ProposedValueIn

FIELDS = ("value_text", "unit_text", "observed_at", "reference_low", "reference_high")


@dataclass(frozen=True)
class RunScore:
    truth_count: int
    proposed_count: int
    matched: int
    field_correct: dict[str, int]
    hallucinated: int
    dob_correct: bool
    issue_correct: bool
    fingerprint: str
    error: str | None = None

    @property
    def recall(self) -> float:
        return self.matched / self.truth_count if self.truth_count else 1.0

    @property
    def precision(self) -> float:
        return self.matched / self.proposed_count if self.proposed_count else 1.0

    @property
    def hallucination_rate(self) -> float:
        return self.hallucinated / self.proposed_count if self.proposed_count else 0.0

    def field_accuracy(self) -> dict[str, float]:
        return {f: (self.field_correct[f] / self.matched if self.matched else 1.0) for f in FIELDS}


@dataclass
class CaseResult:
    case: str
    runs: list[RunScore] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        recalls = [r.recall for r in self.runs]
        precisions = [r.precision for r in self.runs]
        halluc = [r.hallucination_rate for r in self.runs]
        fields = {f: statistics.fmean([r.field_accuracy()[f] for r in self.runs]) for f in FIELDS}
        return {
            "runs": len(self.runs),
            "errors": sum(1 for r in self.runs if r.error),
            "recall_mean": statistics.fmean(recalls),
            "precision_mean": statistics.fmean(precisions),
            "hallucination_rate_mean": statistics.fmean(halluc),
            "field_accuracy_mean": fields,
            "dob_correct_rate": statistics.fmean(
                [1.0 if r.dob_correct else 0.0 for r in self.runs]
            ),
            "issue_correct_rate": statistics.fmean(
                [1.0 if r.issue_correct else 0.0 for r in self.runs]
            ),
            "distinct_outputs": len({r.fingerprint for r in self.runs}),
            "recall_stdev": statistics.pstdev(recalls) if len(recalls) > 1 else 0.0,
            "precision_stdev": statistics.pstdev(precisions) if len(precisions) > 1 else 0.0,
        }


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


def _day(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:10]
    return value.date().isoformat() if hasattr(value, "date") else str(value)[:10]


def _fingerprint(proposal: ProposedBatchIn) -> str:
    rows = sorted(
        (
            _norm(v.analyte_text).casefold(),
            _norm(v.value_text),
            _norm(v.unit_text),
            _day(v.observed_at) or "",
            _norm(v.reference_low),
            _norm(v.reference_high),
            v.page,
        )
        for v in proposal.values
    )
    raw = json.dumps(
        [list(r) for r in rows] + [str(proposal.patient_date_of_birth), str(proposal.issue_date)]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def score(proposal: ProposedBatchIn, truth: dict[str, Any], pages: PageSet) -> RunScore:
    """One proposal against the printed truth. Deterministic string comparison throughout."""
    remaining = list(truth["values"])
    matched = 0
    correct = dict.fromkeys(FIELDS, 0)
    hallucinated = 0
    value: ProposedValueIn
    for value in proposal.values:
        page_text = pages.text(value.page)
        if not (
            checks.text_on_page(value.analyte_text, page_text)
            and checks.value_on_page(value.value_text, page_text)
        ):
            hallucinated += 1
        hit = next(
            (
                t
                for t in remaining
                if _norm(t["analyte_text"]).casefold() == _norm(value.analyte_text).casefold()
            ),
            None,
        )
        if hit is None:
            continue
        remaining.remove(hit)
        matched += 1
        got = {
            "value_text": _norm(value.value_text),
            "unit_text": _norm(value.unit_text),
            "observed_at": _day(value.observed_at),
            "reference_low": _norm(value.reference_low),
            "reference_high": _norm(value.reference_high),
        }
        want = {
            "value_text": _norm(hit["value_text"]),
            "unit_text": _norm(hit["unit_text"]),
            "observed_at": hit.get("observed_at"),
            "reference_low": _norm(hit.get("reference_low")),
            "reference_high": _norm(hit.get("reference_high")),
        }
        for f in FIELDS:
            if got[f] == want[f]:
                correct[f] += 1
    return RunScore(
        truth_count=len(truth["values"]),
        proposed_count=len(proposal.values),
        matched=matched,
        field_correct=correct,
        hallucinated=hallucinated,
        dob_correct=str(proposal.patient_date_of_birth) == str(truth.get("patient_date_of_birth")),
        issue_correct=str(proposal.issue_date) == str(truth.get("issue_date")),
        fingerprint=_fingerprint(proposal),
    )


def _failed(truth: dict[str, Any], error: str) -> RunScore:
    return RunScore(
        truth_count=len(truth["values"]),
        proposed_count=0,
        matched=0,
        field_correct=dict.fromkeys(FIELDS, 0),
        hallucinated=0,
        dob_correct=False,
        issue_correct=False,
        fingerprint="error",
        error=error,
    )


def evaluate_case(
    case_dir: Path,
    provider: ExtractionProvider,
    settings: Settings,
    *,
    runs: int = 5,
    ocr: OcrEngine | None = None,
) -> CaseResult:
    data = (case_dir / "input" / "report.pdf").read_bytes()
    truth = json.loads((case_dir / "input" / "truth.json").read_text(encoding="utf-8"))
    pages = load_pages(data, settings, engine=ocr)
    result = CaseResult(case=case_dir.name)
    for _ in range(runs):
        try:
            proposal = provider.extract(data, pages)
        except Exception as exc:  # noqa: BLE001 - the harness records every failure kind
            # The error class only: a provider's message could quote the document.
            result.runs.append(_failed(truth, type(exc).__name__))
            continue
        result.runs.append(score(proposal, truth, pages))
    return result


def record(
    results_file: Path,
    *,
    provider: ExtractionProvider,
    result: CaseResult,
    ocr_name: str,
) -> dict[str, Any]:
    """Append one JSON line. Never rewrite the file."""
    entry = {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": provider.name,
        "model_id": provider.model_id,
        "prompt_version": provider.prompt_version,
        "checks_version": checks.CHECKS_VERSION,
        "ocr": ocr_name,
        "case": result.case,
        "summary": result.summary(),
        "runs": [
            {
                **{k: v for k, v in asdict(r).items() if k != "field_correct"},
                "field_accuracy": r.field_accuracy(),
                "recall": r.recall,
                "precision": r.precision,
                "hallucination_rate": r.hallucination_rate,
            }
            for r in result.runs
        ],
    }
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with results_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=_json_default) + "\n")
    return entry


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(type(value).__name__)


def report_table(entries: list[dict[str, Any]]) -> str:
    """A Markdown table of one evaluation run: one row per case."""
    head = [
        "Case", "Runs", "Recall", "Precision", "Hallucination", "Value", "Unit", "Date",
        "Ref low", "Ref high", "DOB", "Issue", "Distinct",
    ]  # fmt: skip
    lines = [
        "| " + " | ".join(head) + " |",
        "| --- |" + " ---: |" * (len(head) - 1),
    ]
    for e in entries:
        s = e["summary"]
        fa = s["field_accuracy_mean"]
        cells = [
            e["case"],
            str(s["runs"]),
            f"{s['recall_mean']:.2f}",
            f"{s['precision_mean']:.2f}",
            f"{s['hallucination_rate_mean']:.2f}",
            f"{fa['value_text']:.2f}",
            f"{fa['unit_text']:.2f}",
            f"{fa['observed_at']:.2f}",
            f"{fa['reference_low']:.2f}",
            f"{fa['reference_high']:.2f}",
            f"{s['dob_correct_rate']:.2f}",
            f"{s['issue_correct_rate']:.2f}",
            str(s["distinct_outputs"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
