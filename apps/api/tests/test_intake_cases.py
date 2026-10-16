"""The intake golden cases: the deterministic layer over fixed proposals, bit for bit.

Each case's `expected.json` is compared whole; on top of that, a hand-written table of statuses
and reasons per case guards the expectations themselves, so regenerating the golden files
cannot quietly ratify a changed rule. No database, no model (tests/intake_support.py).
"""

from __future__ import annotations

import json

import pytest

from hadp_api.modules.documents.pdf_text import read_pages
from tests.intake_support import case_dirs, load_case, run_case, serialize

CASES = case_dirs()
assert len(CASES) >= 10, "the specification asks for at least ten golden cases"

# (case, analyte) -> (status, reasons). Written by hand from each rubric.md.
EXPECTED: dict[str, list[tuple[str, str, list[str]]]] = {
    "01_a_nord_all_green": [
        ("HbA1c", "green", []),
        ("LDL", "green", []),
        ("HDL cholesterol", "green", []),
        ("Total cholesterol", "green", []),
        ("Glucose", "green", []),
        ("Triglycerides", "green", []),
    ],
    "02_a_nord_german_names_no_dob": [
        ("HbA1c", "yellow", ["patient_dob_not_proposed"]),
        ("Kreatinin", "yellow", ["patient_dob_not_proposed", "unmapped_analyte"]),
        ("Harnsäure", "yellow", ["patient_dob_not_proposed", "unmapped_analyte"]),
        ("Triglyceride", "yellow", ["patient_dob_not_proposed", "unmapped_analyte"]),
        ("TSH", "yellow", ["patient_dob_not_proposed", "unmapped_analyte"]),
    ],
    "03_b_sued_mgdl_conversions": [
        ("LDL", "green", []),
        ("HDL cholesterol", "green", []),
        ("Total cholesterol", "green", []),
        ("Glucose", "green", []),
        ("Triglycerides", "red", ["unit_unknown"]),
        ("Creatinine", "red", ["unit_unknown"]),
    ],
    "04_b_sued_impossible_values": [
        ("HbA1c", "red", ["outside_hard_bounds"]),
        ("LDL", "red", ["outside_hard_bounds"]),
        ("Glucose", "green", []),
    ],
    "05_c_west_scanned": [
        ("HbA1c", "red", ["analyte_not_on_page", "low_confidence"]),
        ("LDL", "yellow", ["low_confidence"]),
        ("Glucose", "yellow", ["low_confidence"]),
    ],
    "06_c_west_non_ucum_units": [
        ("Glucose", "red", ["unit_unknown"]),
        ("HbA1c", "red", ["unit_unknown"]),
        ("Ferritin", "red", ["unit_unknown", "reference_unreadable"]),
        ("LDL", "green", []),
    ],
    "07_a_nord_duplicates": [
        ("HbA1c", "red", ["duplicate_of_published"]),
        ("LDL", "red", ["duplicate_of_published"]),
        ("Glucose", "green", []),
        ("HbA1c", "red", ["duplicate_in_batch"]),
    ],
    "08_b_sued_delta_jump": [
        ("LDL", "yellow", ["implausible_delta"]),
        ("HbA1c", "green", []),
    ],
    "09_c_west_dates": [
        ("HbA1c", "green", []),
        ("LDL", "yellow", ["date_in_future"]),
        ("Glucose", "yellow", ["date_outside_window"]),
        ("HDL cholesterol", "red", ["date_before_birth"]),
        ("Total cholesterol", "red", ["date_missing"]),
    ],
    "10_a_nord_hallucination": [
        ("HbA1c", "green", []),
        ("LDL", "green", []),
        ("Glucose", "red", ["value_not_on_page"]),
        ("Ferritin", "red", ["analyte_not_on_page", "unit_unknown"]),
        ("HDL cholesterol", "red", ["page_out_of_range"]),
    ],
    "11_b_sued_patient_mismatch": [
        ("LDL", "red", ["patient_mismatch"]),
        ("HbA1c", "red", ["patient_mismatch"]),
    ],
    "12_a_nord_prompt_injection": [
        ("HbA1c", "yellow", ["conflicting_in_batch"]),
        ("LDL", "green", []),
        ("Glucose", "green", []),
        ("HbA1c", "yellow", ["conflicting_in_batch"]),
    ],
}


def test_every_case_has_a_hand_written_expectation() -> None:
    assert {c.name for c in CASES} == set(EXPECTED)


@pytest.mark.parametrize("case_dir", CASES, ids=[c.name for c in CASES])
def test_golden_output_matches_bit_for_bit(case_dir) -> None:  # type: ignore[no-untyped-def]
    case = load_case(case_dir)
    actual = serialize(run_case(case))
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    assert actual == expected, "regenerate only on purpose, and review the diff"


@pytest.mark.parametrize("case_dir", CASES, ids=[c.name for c in CASES])
def test_statuses_and_reasons_are_the_rubrics(case_dir) -> None:  # type: ignore[no-untyped-def]
    checked = run_case(load_case(case_dir))
    got = [
        (v.proposal.analyte_text, v.status.value, [c.reason for c in v.checks if c.reason])
        for v in checked.values
    ]
    assert got == EXPECTED[case_dir.name]


@pytest.mark.parametrize("case_dir", CASES, ids=[c.name for c in CASES])
def test_the_text_layer_reader_reproduces_the_recorded_pages(case_dir) -> None:  # type: ignore[no-untyped-def]
    """`pages.json` is what the reader produces from the committed PDF — for a text-layer PDF.
    The scan has no text layer: the reader finds nothing, and the recorded OCR text is what a
    separate OCR step produced (not re-run here)."""
    pages = json.loads((case_dir / "input" / "pages.json").read_text(encoding="utf-8"))
    read = read_pages((case_dir / "input" / "report.pdf").read_bytes())
    if pages["reader"].startswith("pdfplumber"):
        assert list(read.texts) == pages["pages"]
    else:
        assert pages["reader"].startswith("tesseract")
        assert all(not t.strip() for t in read.texts), "a scan must have no text layer"


@pytest.mark.parametrize("case_dir", CASES, ids=[c.name for c in CASES])
def test_every_case_declares_itself_synthetic(case_dir) -> None:  # type: ignore[no-untyped-def]
    pages = json.loads((case_dir / "input" / "pages.json").read_text(encoding="utf-8"))
    assert any("synthetisch" in p.casefold() for p in pages["pages"])
    patient = json.loads((case_dir / "input" / "patient.json").read_text(encoding="utf-8"))
    assert "TEST-ONLY" in patient["_note"]
    assert (case_dir / "rubric.md").exists()


def test_bounding_boxes_point_at_the_value_on_the_page() -> None:
    """Where the generator could locate the value word, the box lies on page 1 of an A4 page
    and is a few points high — provenance a confirmation screen can crop."""
    seen = 0
    for case_dir in CASES:
        case = load_case(case_dir)
        for v in case.proposal.values:
            if v.bbox is None:
                continue
            x0, y0, x1, y1 = v.bbox
            assert 0 <= x0 < x1 <= 596 and 0 <= y0 < y1 <= 842
            assert 5 <= y1 - y0 <= 20
            seen += 1
    assert seen >= 30
