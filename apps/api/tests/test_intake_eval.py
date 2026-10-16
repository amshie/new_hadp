"""The evaluation harness: deterministic scoring, append-only results, swappable provider."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hadp_api.config import get_settings
from hadp_api.modules.intake import evaluation
from hadp_api.modules.intake.model_provider import ModelProvider
from hadp_api.modules.intake.pages import load_pages
from hadp_api.modules.intake.providers import TextLayerProvider
from hadp_api.modules.intake.schemas import ProposedBatchIn
from tests.intake_support import CASES_DIR, case_dirs


def test_every_case_has_a_truth_file_that_matches_its_page() -> None:
    for case in case_dirs():
        truth = json.loads((case / "input" / "truth.json").read_text(encoding="utf-8"))
        assert truth["values"], case.name
        pages = json.loads((case / "input" / "pages.json").read_text(encoding="utf-8"))
        if pages["reader"].startswith("pdfplumber"):
            text = " ".join(pages["pages"][0].split())
            for v in truth["values"]:
                assert v["value_text"] in text, (case.name, v)


def test_the_text_layer_provider_scores_perfectly_on_the_clean_report_and_is_stable() -> None:
    settings = get_settings()
    result = evaluation.evaluate_case(
        CASES_DIR / "01_a_nord_all_green", TextLayerProvider(), settings, runs=3
    )
    s = result.summary()
    assert s["runs"] == 3 and s["errors"] == 0
    assert s["recall_mean"] == 1.0 and s["precision_mean"] == 1.0
    assert s["hallucination_rate_mean"] == 0.0
    assert all(v == 1.0 for v in s["field_accuracy_mean"].values())
    assert s["dob_correct_rate"] == 1.0 and s["issue_correct_rate"] == 1.0
    assert s["distinct_outputs"] == 1 and s["recall_stdev"] == 0.0


def test_a_scan_without_ocr_is_scored_as_read_nothing() -> None:
    result = evaluation.evaluate_case(
        CASES_DIR / "05_c_west_scanned", TextLayerProvider(), get_settings(), runs=1
    )
    [run] = result.runs
    # The provider's one "nothing recognised" entry matches no truth and is not on the page.
    assert run.matched == 0 and run.proposed_count == 1 and run.hallucinated == 1
    assert run.recall == 0.0


def test_scoring_counts_a_misread_value_and_a_value_that_is_not_on_the_page() -> None:
    case = CASES_DIR / "10_a_nord_hallucination"
    data = (case / "input" / "report.pdf").read_bytes()
    pages = load_pages(data, get_settings())
    truth = json.loads((case / "input" / "truth.json").read_text(encoding="utf-8"))
    proposal = ProposedBatchIn.model_validate(
        json.loads((case / "input" / "proposal.json").read_text(encoding="utf-8"))
    )
    run = evaluation.score(proposal, truth, pages)
    # Three printed values, five proposed: HbA1c and LDL right, Glucose misread ("51"),
    # Ferritin not on the page, HDL citing a page that does not exist.
    assert (run.truth_count, run.proposed_count, run.matched) == (3, 5, 3)
    assert run.field_correct["value_text"] == 2 and run.field_correct["unit_text"] == 3
    assert run.hallucinated == 3  # the misread number, the absent analyte, the absent page
    assert run.precision == 3 / 5 and run.recall == 1.0


def test_results_are_appended_never_rewritten(tmp_path: Path) -> None:
    settings = get_settings()
    out = tmp_path / "results.jsonl"
    provider = TextLayerProvider()
    for case in ("01_a_nord_all_green", "03_b_sued_mgdl_conversions"):
        result = evaluation.evaluate_case(CASES_DIR / case, provider, settings, runs=2)
        evaluation.record(out, provider=provider, result=result, ocr_name="off")
    first = out.read_text(encoding="utf-8").splitlines()
    assert len(first) == 2
    result = evaluation.evaluate_case(CASES_DIR / "01_a_nord_all_green", provider, settings, runs=1)
    evaluation.record(out, provider=provider, result=result, ocr_name="off")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == first and len(lines) == 3
    entry = json.loads(lines[-1])
    assert entry["provider"] == "text-layer" and entry["model_id"] == "none"
    assert (
        entry["prompt_version"] == "text-layer-1" and entry["checks_version"] == "intake-checks-1"
    )
    assert entry["summary"]["runs"] == 1 and len(entry["runs"]) == 1
    assert evaluation.report_table([entry]).count("\n") == 2


def test_the_same_harness_runs_a_model_provider_through_the_router_seam() -> None:
    @dataclass
    class ScriptedBackend:
        """Plays a model that reads the clean report right, except one misread number."""

        @property
        def name(self) -> str:
            return "scripted"

        @property
        def model_id(self) -> str:
            return "scripted-1"

        def complete(self, system: str, user_text: str, images: list[bytes]) -> str:
            proposal = json.loads(
                (CASES_DIR / "01_a_nord_all_green" / "input" / "proposal.json").read_text(
                    encoding="utf-8"
                )
            )
            values = proposal["values"]
            values[1]["value_text"] = "31"  # LDL misread
            return json.dumps(
                {
                    "patient_date_of_birth": proposal["patient_date_of_birth"],
                    "issue_date": proposal["issue_date"],
                    "values": [
                        {k: v for k, v in val.items() if k != "bbox"} | {"bbox": None}
                        for val in values
                    ],
                }
            )

    result = evaluation.evaluate_case(
        CASES_DIR / "01_a_nord_all_green", ModelProvider(ScriptedBackend()), get_settings(), runs=2
    )
    s = result.summary()
    assert s["errors"] == 0 and s["recall_mean"] == 1.0
    assert s["field_accuracy_mean"]["value_text"] == 5 / 6
    assert s["hallucination_rate_mean"] == 1 / 6  # "31" is not on the page
    assert s["distinct_outputs"] == 1
