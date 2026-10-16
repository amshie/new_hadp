"""Where a proposed value is printed is found by code (`modules/intake/locate.py`), never taken
from the proposal: unit cases on synthetic rows, every golden case, the one write over the
agent's tool, and the crop the confirmation screen shows."""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from hadp_api.modules.documents.pdf_text import Word, read_pages
from hadp_api.modules.intake import checks
from hadp_api.modules.intake.decisions import _FRAME_RGB, render_region
from hadp_api.modules.intake.locate import line_extent, lines_of, locate_value
from hadp_api.modules.intake.models import PendingValue
from hadp_api.modules.intake.tools import IntakeScope, IntakeTools
from tests.intake_support import CASES_DIR, case_dirs
from tests.test_intake_governance import TODAY, _patient, _staff, _upload

API = "/api/v1"
CASES = case_dirs()
SCALE = 144 / 72  # the crop's resolution, pixels per point


def _row(y: float, *cells: tuple[float, str]) -> list[Word]:
    """The words of one printed row at height y, from (x0, text) pairs; 6 points per character."""
    return [Word(text=t, x0=x, top=y, x1=x + 6 * len(t), bottom=y + 10) for x, t in cells]


def _box_of(word: Word) -> tuple[float, float, float, float]:
    return (word.x0, word.top, word.x1, word.bottom)


# --- the rules, on synthetic rows ----------------------------------------------------------------


def test_a_value_printed_once_is_boxed_where_it_stands() -> None:
    words = _row(
        100, (50, "HbA1c"), (280, "5,4"), (330, "%"), (400, "4,0"), (430, "-"), (445, "6,0")
    )
    assert locate_value(words, "HbA1c", "5,4") == _box_of(words[1])


def test_a_number_printed_in_several_rows_is_placed_on_the_analytes_row() -> None:
    glucose = _row(100, (50, "Glucose:"), (110, "5,0"), (140, "mmol/L"))
    total = _row(118, (50, "Total"), (90, "cholesterol:"), (170, "5,0"), (200, "mmol/L"))
    words = [*glucose, *total]
    assert locate_value(words, "Total cholesterol", "5,0") == _box_of(total[2])
    assert locate_value(words, "Glucose", "5,0") == _box_of(glucose[1])


def test_a_value_equal_to_its_reference_bound_is_placed_in_the_value_column() -> None:
    words = _row(
        100,
        (50, "Total"),
        (90, "cholesterol"),
        (280, "5,2"),
        (330, "mmol/L"),
        (420, "<"),
        (430, "5,2"),
    )
    assert locate_value(words, "Total cholesterol", "5,2") == _box_of(words[2])


def test_a_number_inside_the_analytes_name_is_not_the_value() -> None:
    words = _row(100, (50, "Vitamin"), (100, "D3"), (120, "(25-OH)"), (280, "25"), (310, "ng/ml"))
    assert locate_value(words, "Vitamin D3 (25-OH)", "25") == _box_of(words[3])


def test_a_number_inside_a_longer_number_is_not_the_value() -> None:
    words = _row(100, (50, "LDL"), (280, "15,2"), (320, "mmol/L"))
    assert locate_value(words, "LDL", "5,2") is None


def test_a_value_that_is_not_printed_has_no_box() -> None:
    words = _row(100, (50, "Glucose"), (280, "5,1"), (320, "mmol/L"))
    assert locate_value(words, "Glucose", "51") is None
    assert locate_value(words, "Glucose", "  ") is None
    assert locate_value([], "Glucose", "5,1") is None


def test_without_the_name_on_its_row_only_a_value_printed_once_is_placed() -> None:
    # The name wraps onto the line above its value: no line carries both.
    name = _row(100, (50, "Cholesterin,"), (130, "gesamt"))
    once = _row(112, (280, "5,0"), (310, "mmol/L"))
    assert locate_value([*name, *once], "Cholesterin, gesamt", "5,0") == _box_of(once[0])
    # The same value printed a second time elsewhere: code cannot tell which one — no box.
    again = _row(140, (280, "5,0"), (310, "mmol/L"))
    assert locate_value([*name, *once, *again], "Cholesterin, gesamt", "5,0") is None


def test_the_name_and_the_value_together_on_two_rows_give_no_box() -> None:
    first = _row(100, (50, "HbA1c"), (280, "5,4"), (330, "%"))
    second = _row(130, (50, "HbA1c"), (280, "5,4"), (330, "%"))
    assert locate_value([*first, *second], "HbA1c", "5,4") is None


def test_a_value_glued_to_its_unit_is_boxed_with_the_word_it_is_printed_in() -> None:
    words = _row(100, (50, "Glucose"), (280, "92mg/dl"))
    assert locate_value(words, "Glucose", "92") == _box_of(words[1])


def test_rows_are_grouped_by_height_whatever_the_order_of_the_words() -> None:
    # A bold name set a point higher than its numbers still reads as one row.
    name = Word(text="LDL", x0=50, top=99, x1=68, bottom=110)
    value = Word(text="3,1", x0=280, top=100, x1=298, bottom=110)
    below = Word(text="3,1", x0=280, top=130, x1=298, bottom=140)
    lines = lines_of([below, value, name])
    assert [[w.text for w in line] for line in lines] == [["LDL", "3,1"], ["3,1"]]
    assert locate_value([below, value, name], "LDL", "3,1") == _box_of(value)


def test_line_extent_spans_the_whole_printed_row() -> None:
    words = [*_row(100, (50, "HbA1c"), (280, "5,4"), (445, "6,0")), *_row(130, (20, "Fußnote"))]
    assert line_extent(words, _box_of(words[1])) == (50, 463)


# --- every golden case ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_dir", CASES, ids=[c.name for c in CASES])
def test_every_golden_value_on_a_text_layer_is_boxed_on_its_own_row(case_dir: Path) -> None:
    proposal = json.loads((case_dir / "input" / "proposal.json").read_text(encoding="utf-8"))
    pages = read_pages((case_dir / "input" / "report.pdf").read_bytes())
    for v in proposal["values"]:
        # A page the report does not have (case 10 cites one) has no words.
        words = pages.words[v["page"] - 1] if v["page"] <= pages.page_count else ()
        box = locate_value(words, v["analyte_text"], v["value_text"])
        if not checks.value_on_page(v["value_text"], pages.text(v["page"])):
            # Not printed (an invented value, a scan without OCR): there is nowhere to point.
            assert box is None, v
            continue
        assert box is not None, v
        x0, top, x1, bottom = box
        inside = [
            w
            for w in words
            if w.x0 >= x0 - 0.1
            and w.x1 <= x1 + 0.1
            and w.top >= top - 0.1
            and w.bottom <= bottom + 0.1
        ]
        # The box holds the value as printed — and the row it sits on carries the analyte.
        assert checks.value_on_page(v["value_text"], " ".join(w.text for w in inside)), v
        row = next(line for line in lines_of(words) if inside[0] in line)
        assert checks.text_on_page(v["analyte_text"], " ".join(w.text for w in row)), v


def test_the_injected_value_points_at_the_paragraph_that_carries_it() -> None:
    case = CASES_DIR / "12_a_nord_prompt_injection"
    pages = read_pages((case / "input" / "report.pdf").read_bytes())
    box = locate_value(pages.words[0], "HbA1c", "12,0")
    assert box is not None
    row = next(line for line in lines_of(pages.words[0]) if line[0].top <= box[1] <= line[0].bottom)
    assert "Patientenakte:" in [w.text for w in row]  # the paragraph, not the table


# --- the one write: the stored box is code's, whatever the proposal says -----------------------


def _write(client, pid: str, did: str, raw: dict) -> uuid.UUID:  # type: ignore[no-untyped-def,type-arg]
    me = client.get(f"{API}/auth/me").json()
    tools = IntakeTools(
        IntakeScope(
            tenant_id=uuid.UUID(me["active_tenant_id"]),
            patient_id=uuid.UUID(pid),
            document_id=uuid.UUID(did),
            actor_user_id=uuid.UUID(me["user"]["id"]),
            extraction_provider="model",
            model_id="fixture-model",
            prompt_version="intake-extract-2",
        ),
        today=TODAY,
    )
    return tools.create_pending_batch(
        did,
        raw["values"],
        patient_date_of_birth=raw["patient_date_of_birth"],
        issue_date=raw["issue_date"],
    ).batch_id


def _rows(admin_session, batch_id: uuid.UUID) -> dict[str, PendingValue]:  # type: ignore[no-untyped-def]
    found = admin_session.execute(select(PendingValue).where(PendingValue.batch_id == batch_id))
    return {r.proposed_analyte_text: r for r in found.scalars()}


def test_a_model_answer_without_boxes_gets_them_from_code_and_a_wrong_box_is_ignored(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _staff(client, admin_session, "locate")
    case = CASES_DIR / "09_c_west_dates"
    pid = _patient(client)
    did = _upload(client, pid, case)
    raw = json.loads((case / "input" / "proposal.json").read_text(encoding="utf-8"))
    for v in raw["values"]:
        v["bbox"] = None  # a model answers without boxes (prompt intake-extract-2)
    total = next(v for v in raw["values"] if v["analyte_text"] == "Total cholesterol")
    total["bbox"] = [96.4, 196.4, 112.3, 206.4]  # around Glucose's "5,0", one row up
    rows = _rows(admin_session, _write(client, pid, did, raw))
    assert set(rows) == {v["analyte_text"] for v in raw["values"]}
    assert all(r.bbox is not None for r in rows.values())
    # Placed on its own row, not where the proposal drew it.
    assert rows["Total cholesterol"].bbox == [140.0, 232.4, 155.9, 242.4]
    assert rows["Glucose"].bbox == [96.4, 196.4, 112.3, 206.4]


def test_a_scanned_page_gets_no_box_and_the_screen_shows_the_whole_page(
    client, admin_session
) -> None:  # type: ignore[no-untyped-def]
    _staff(client, admin_session, "locate-scan")
    case = CASES_DIR / "05_c_west_scanned"
    pid = _patient(client)
    did = _upload(client, pid, case)
    raw = json.loads((case / "input" / "proposal.json").read_text(encoding="utf-8"))
    raw["values"][0]["bbox"] = [50.0, 100.0, 80.0, 110.0]  # a box with nothing behind it
    rows = _rows(admin_session, _write(client, pid, did, raw))
    assert rows and all(r.bbox is None for r in rows.values())
    one = next(iter(rows.values()))
    region = client.get(f"{API}/intake/values/{one.id}/region")
    assert region.status_code == 200
    image = Image.open(io.BytesIO(region.content))
    assert image.width >= int(590 * SCALE) and image.height >= int(830 * SCALE)


# --- the crop -----------------------------------------------------------------------------------


def _frame_pixels(image: Image.Image) -> int:
    rgb = image.convert("RGB")
    return sum(1 for px in rgb.getdata() if px == _FRAME_RGB)


def test_the_crop_shows_the_whole_row_with_the_value_framed() -> None:
    data = (CASES_DIR / "01_a_nord_all_green" / "input" / "report.pdf").read_bytes()
    words = read_pages(data).words[0]
    box = locate_value(words, "LDL", "3,1")
    assert box is not None
    image = Image.open(io.BytesIO(render_region(data, 1, box)))
    left, right = line_extent(words, box)
    # From the analyte's name at the left margin to the reference at the right, one row high.
    assert left <= 51 and right > box[2]
    assert image.width == pytest.approx((right - left + 24) * SCALE, abs=2)
    assert image.height == pytest.approx((box[3] - box[1] + 28) * SCALE, abs=2)
    assert _frame_pixels(image) > 50


def test_without_a_box_the_crop_is_the_whole_page_unframed() -> None:
    data = (CASES_DIR / "01_a_nord_all_green" / "input" / "report.pdf").read_bytes()
    image = Image.open(io.BytesIO(render_region(data, 1, None)))
    assert image.width >= int(590 * SCALE) and image.height >= int(830 * SCALE)
    assert _frame_pixels(image) == 0
