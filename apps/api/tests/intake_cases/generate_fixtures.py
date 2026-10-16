"""Generate the SYNTHETIC golden cases of the lab intake agent.

    cd apps/api && uv run python tests/intake_cases/generate_fixtures.py [--write-expected]

Every PDF is drawn here from the specs below — three invented German laboratory layouts, one of
them rendered as an image without a text layer (a "scan"). No real laboratory, no real person:
the names, addresses and values are made up. Dates are fixed so the cases are reproducible.

Outputs per case: input/report.pdf, input/pages.json (the page texts pdfplumber reads from the
PDF, or tesseract for the scan), input/patient.json, input/proposal.json (the fixed proposal
the deterministic tests run on — it is what a model WOULD return, including the mistakes a
case is about), and, with --write-expected, expected.json from the checks as they stand.
`rubric.md` is written by hand and is not touched.

Running this again rewrites the PDFs byte for byte (reportlab `invariant`). The OCR text of
the scan depends on the tesseract build; it is committed and only regenerated on purpose.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))  # apps/api, for `tests.intake_support`

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("DejaVu", FONT))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))

TODAY = "2026-10-16"
PATIENT = {"display_name": "Muster, Erika", "date_of_birth": "1970-03-12"}
PDF_DOB = "12.03.1970"

# TEST-ONLY bounds. Not clinically signed: they exist so the golden cases can exercise the
# plausibility and delta checks. The product's table ships empty (modules/intake/bounds_data.py).
TEST_BOUNDS: dict[str, dict[str, str | None]] = {
    "_note": {  # type: ignore[dict-item]
        "text": "TEST FIXTURE ONLY — not clinically signed; never copy into bounds_data.py"
    },
    "metabolic.hba1c": {
        "unit": "%",
        "hard_low": "2",
        "hard_high": "20",
        "delta_max_relative": "1.0",
    },
    "cardio.ldl_c": {
        "unit": "mmol/L",
        "hard_low": "0.1",
        "hard_high": "15",
        "delta_max_relative": "1.5",
    },
    "cardio.hdl_c": {
        "unit": "mmol/L",
        "hard_low": "0.1",
        "hard_high": "5",
        "delta_max_relative": "1.5",
    },
    "cardio.total_cholesterol": {
        "unit": "mmol/L",
        "hard_low": "0.5",
        "hard_high": "25",
        "delta_max_relative": "1.5",
    },
    "metabolic.fasting_plasma_glucose": {
        "unit": "mmol/L",
        "hard_low": "0.5",
        "hard_high": "60",
        "delta_max_relative": "2.0",
    },
    "metabolic.triglycerides": {
        "unit": "mmol/L",
        "hard_low": "0.1",
        "hard_high": "60",
        "delta_max_relative": "3.0",
    },
    "regen.creatinine": {
        "unit": "umol/L",
        "hard_low": "10",
        "hard_high": "2500",
        "delta_max_relative": "2.0",
    },
    "immune.hs_crp": {
        "unit": "mg/L",
        "hard_low": "0",
        "hard_high": "500",
        "delta_max_relative": None,
    },
    "immune.ferritin": {
        "unit": "ug/L",
        "hard_low": "1",
        "hard_high": "20000",
        "delta_max_relative": "3.0",
    },
    "regen.hemoglobin": {
        "unit": "g/L",
        "hard_low": "20",
        "hard_high": "250",
        "delta_max_relative": "1.0",
    },
}


@dataclass
class Row:
    """One result line as PRINTED. `proposed` overrides what the proposal says about it (a
    deliberate misreading); `omit_from_proposal` prints it without proposing it."""

    name: str
    value: str
    unit: str
    ref_low: str | None = None
    ref_high: str | None = None
    ref_text: str | None = None
    date: str | None = None  # dd.mm.yyyy printed per row (layout C), else the header date
    confidence: str = "0.95"
    proposed: dict[str, Any] = field(default_factory=dict)
    omit_from_proposal: bool = False


@dataclass
class Case:
    name: str
    layout: str  # "A" | "B" | "C"
    rows: list[Row]
    sampling_date: str  # dd.mm.yyyy printed in the header (A, B) or default for C rows
    issue_date: str  # dd.mm.yyyy
    print_dob: bool = True
    pdf_dob: str = PDF_DOB
    scanned: bool = False
    extra_proposals: list[dict[str, Any]] = field(default_factory=list)
    published: list[dict[str, Any]] = field(default_factory=list)
    proposal_dob: str | None = "1970-03-12"
    proposal_issue: str | None = None  # ISO; default derived from issue_date


def iso(d: str) -> str:
    day, month, year = d.split(".")
    return f"{year}-{month}-{day}"


def ref_display(row: Row) -> str:
    if row.ref_text:
        return row.ref_text
    if row.ref_low and row.ref_high:
        return f"{row.ref_low} - {row.ref_high}"
    if row.ref_high:
        return f"< {row.ref_high}"
    if row.ref_low:
        return f"> {row.ref_low}"
    return ""


# --- Layouts -------------------------------------------------------------------------------------


def draw_layout_a(c: canvas.Canvas, case: Case) -> None:
    w, h = A4
    c.setFont("DejaVu-Bold", 13)
    c.drawString(50, h - 60, "Labor Nord Synthetik")
    c.setFont("DejaVu", 8)
    c.drawString(
        50, h - 74, "Musterstraße 1 · 20095 Hamburg · SYNTHETISCHE TESTDATEN – kein echter Befund"
    )
    c.setFont("DejaVu", 10)
    c.drawString(50, h - 110, "Patient: Muster, Erika")
    if case.print_dob:
        c.drawString(300, h - 110, f"geb. {case.pdf_dob}")
    c.drawString(50, h - 126, f"Probenentnahme: {case.sampling_date}")
    c.drawString(300, h - 126, f"Befunddatum: {case.issue_date}")
    y = h - 170
    c.setFont("DejaVu-Bold", 10)
    for x, title in (
        (50, "Parameter"),
        (260, "Ergebnis"),
        (340, "Einheit"),
        (430, "Referenzbereich"),
    ):
        c.drawString(x, y, title)
    c.line(50, y - 4, w - 50, y - 4)
    c.setFont("DejaVu", 10)
    y -= 22
    for row in case.rows:
        c.drawString(50, y, row.name)
        c.drawRightString(300, y, row.value)
        c.drawString(340, y, row.unit)
        c.drawString(430, y, ref_display(row))
        y -= 18
    c.setFont("DejaVu", 8)
    c.drawString(50, 60, "Seite 1 von 1")


def draw_layout_b(c: canvas.Canvas, case: Case) -> None:
    w, h = A4
    c.setFont("DejaVu-Bold", 12)
    c.drawString(50, h - 55, "MVZ Labor Süd (synthetisch)")
    c.setFont("DejaVu", 8)
    c.drawString(
        50, h - 68, "Beispielweg 7 · 80331 München · Testdaten ohne Bezug zu realen Personen"
    )
    c.setFont("DejaVu", 10)
    line = "Pat.: Muster, Erika" + (f"  *{case.pdf_dob}" if case.print_dob else "")
    c.drawString(50, h - 100, line)
    c.drawString(
        50, h - 116, f"Entnahme: {case.sampling_date} 08:15    Befund vom {case.issue_date}"
    )
    c.drawString(50, h - 140, "Klinische Chemie")
    y = h - 162
    for row in case.rows:
        c.drawString(60, y, f"{row.name}")
        c.drawRightString(260, y, row.value)
        c.drawString(270, y, row.unit)
        if ref_display(row):
            c.drawString(360, y, f"Norm: {ref_display(row)}")
        y -= 16
    c.setFont("DejaVu", 8)
    c.drawString(50, 50, "Dieses Dokument wurde maschinell erstellt. Synthetisch.")


def draw_layout_c_lines(case: Case) -> list[str]:
    lines = [
        "Praxislabor West",
        "Teststraße 12, 50667 Köln — synthetischer Befund",
        "",
        "Muster, Erika" + (f", geb. {case.pdf_dob}" if case.print_dob else ""),
        f"Befund erstellt am {case.issue_date}",
        "",
    ]
    for row in case.rows:
        ref = f" [{ref_display(row)}]" if ref_display(row) else ""
        when = row.date or case.sampling_date
        lines.append(f"{row.name}: {row.value} {row.unit}{ref}  (Entnahme {when})")
    return lines


def draw_layout_c(c: canvas.Canvas, case: Case) -> None:
    _w, h = A4
    y = h - 60
    for i, line in enumerate(draw_layout_c_lines(case)):
        c.setFont("DejaVu-Bold" if i == 0 else "DejaVu", 11 if i == 0 else 10)
        c.drawString(50, y, line)
        y -= 18


def render_pdf(case: Case) -> bytes:
    buf = io.BytesIO()
    if case.scanned:
        # An image of the page and nothing else: no text layer.
        img = Image.new("RGB", (1654, 2339), "white")  # A4 at 200 dpi
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT, 34)
        bold = ImageFont.truetype(FONT_BOLD, 38)
        y = 140
        for i, line in enumerate(draw_layout_c_lines(case)):
            draw.text((140, y), line, fill="black", font=bold if i == 0 else font)
            y += 56
        c = canvas.Canvas(buf, pagesize=A4, invariant=1)
        c.drawImage(ImageReader(img), 0, 0, width=A4[0], height=A4[1])
        c.showPage()
        c.save()
        return buf.getvalue()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    {"A": draw_layout_a, "B": draw_layout_b, "C": draw_layout_c}[case.layout](c, case)
    c.showPage()
    c.save()
    return buf.getvalue()


# --- Page texts and boxes ------------------------------------------------------------------------


def page_texts(pdf: bytes, scanned: bool) -> dict[str, Any]:
    if not scanned:
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            return {
                "reader": f"pdfplumber-{pdfplumber.__version__}",
                "pages": [p.extract_text() or "" for p in doc.pages],
            }
    if shutil.which("tesseract") is None:
        raise SystemExit("tesseract is needed to regenerate the scanned case's pages.json")
    with pdfplumber.open(io.BytesIO(pdf)) as doc, tempfile.TemporaryDirectory() as tmp:
        texts = []
        for i, page in enumerate(doc.pages):
            png = Path(tmp) / f"p{i}.png"
            page.to_image(resolution=200).save(str(png))
            out = subprocess.run(
                ["tesseract", str(png), "stdout", "-l", "deu", "--psm", "6"],
                check=True,
                capture_output=True,
                text=True,
            )
            texts.append(out.stdout)
        version = subprocess.run(
            ["tesseract", "--version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0]
        return {"reader": version.replace(" ", "-"), "pages": texts}


def value_bbox(pdf: bytes, page_no: int, value: str) -> list[float] | None:
    """The box of the word that is this value on the page (top-left origin, points)."""
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        if page_no > len(doc.pages):
            return None
        for word in doc.pages[page_no - 1].extract_words():
            if word["text"] == value:
                return [
                    round(word["x0"], 1),
                    round(word["top"], 1),
                    round(word["x1"], 1),
                    round(word["bottom"], 1),
                ]
    return None


# --- Proposal and patient files ------------------------------------------------------------------


def proposal_for(case: Case, pdf: bytes) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    for row in case.rows:
        if row.omit_from_proposal:
            continue
        when = row.date or case.sampling_date
        item: dict[str, Any] = {
            "analyte_text": row.name,
            "value_text": row.value,
            "unit_text": row.unit,
            "observed_at": iso(when),
            "observed_at_is_date_only": True,
            "reference_low": row.ref_low,
            "reference_high": row.ref_high,
            "reference_text": ref_display(row) or None,
            "page": 1,
            "bbox": None if case.scanned else value_bbox(pdf, 1, row.value),
            "confidence": row.confidence,
        }
        item.update(row.proposed)
        values.append(item)
    values.extend(case.extra_proposals)
    return {
        "extraction_provider": "golden-fixture",
        "model_id": "fixture-proposal",
        "prompt_version": "fixture-1",
        "patient_date_of_birth": case.proposal_dob,
        "issue_date": case.proposal_issue or iso(case.issue_date),
        "values": values,
    }


def patient_for(case: Case) -> dict[str, Any]:
    return {
        "_note": "Synthetic. The bounds are TEST-ONLY and not clinically signed.",
        "patient": PATIENT,
        "today": TODAY,
        "published": case.published,
        "test_bounds": TEST_BOUNDS,
    }


# --- The cases -----------------------------------------------------------------------------------


def cases() -> list[Case]:
    return [
        Case(
            name="01_a_nord_all_green",
            layout="A",
            sampling_date="05.09.2026",
            issue_date="06.09.2026",
            rows=[
                Row("HbA1c", "5,4", "%", "4,0", "6,0"),
                Row("LDL", "3,1", "mmol/L", None, "3,0"),
                Row("HDL cholesterol", "1,6", "mmol/L", "1,0", None),
                Row("Total cholesterol", "5,2", "mmol/L", None, "5,2"),
                Row("Glucose", "5,1", "mmol/L", "3,9", "5,6"),
                Row("Triglycerides", "1,3", "mmol/L", None, "1,7"),
            ],
        ),
        Case(
            name="02_a_nord_german_names_no_dob",
            layout="A",
            sampling_date="12.09.2026",
            issue_date="13.09.2026",
            print_dob=False,
            proposal_dob=None,
            rows=[
                Row("HbA1c", "5,6", "%", "4,0", "6,0"),
                Row("Kreatinin", "78", "µmol/L", "45", "84"),
                Row("Harnsäure", "310", "µmol/L", "143", "339"),
                Row("Triglyceride", "1,3", "mmol/L", None, "1,7"),
                Row("TSH", "1,8", "mU/L", "0,4", "4,0"),
            ],
        ),
        Case(
            name="03_b_sued_mgdl_conversions",
            layout="B",
            sampling_date="10.09.2026",
            issue_date="11.09.2026",
            rows=[
                Row("LDL", "128", "mg/dl", "50", "130"),
                Row("HDL cholesterol", "62", "mg/dl", "40", None),
                Row("Total cholesterol", "201", "mg/dl", None, "200"),
                Row("Glucose", "92", "mg/dl", "70", "100"),
                Row("Triglycerides", "115", "mg/dl", None, "150"),
                Row("Creatinine", "0,9", "mg/dl", "0,5", "1,0"),
            ],
        ),
        Case(
            name="04_b_sued_impossible_values",
            layout="B",
            sampling_date="17.09.2026",
            issue_date="18.09.2026",
            rows=[
                Row("HbA1c", "54", "%", "4,0", "6,0"),
                Row("LDL", "0,0", "mg/dl", "50", "130"),
                Row("Glucose", "520", "mg/dl", "70", "100"),
            ],
        ),
        Case(
            name="05_c_west_scanned",
            layout="C",
            scanned=True,
            sampling_date="20.09.2026",
            issue_date="22.09.2026",
            rows=[
                Row("HbA1c", "5,9", "%", "4,0", "6,0", confidence="0.82"),
                Row("LDL", "3,4", "mmol/L", None, "3,0", confidence="0.80"),
                Row("Glucose", "5,6", "mmol/L", "3,9", "5,6", confidence="0.85"),
            ],
        ),
        Case(
            name="06_c_west_non_ucum_units",
            layout="C",
            sampling_date="20.09.2026",
            issue_date="22.09.2026",
            rows=[
                Row("Glucose", "92", "mg%", "70", "100"),
                Row("HbA1c", "38", "mmol/mol", "20", "42"),
                Row("Ferritin", "85", "ng/ml", "s.o.", None, ref_text="siehe Kommentar"),
                Row("LDL", "2,9", "mmol/L", None, "3,0"),
            ],
        ),
        Case(
            name="07_a_nord_duplicates",
            layout="A",
            sampling_date="05.09.2026",
            issue_date="06.09.2026",
            rows=[
                Row("HbA1c", "5,4", "%", "4,0", "6,0"),
                Row("LDL", "3,1", "mmol/L", None, "3,0"),
                Row("Glucose", "5,1", "mmol/L", "3,9", "5,6"),
            ],
            extra_proposals=[
                {
                    "analyte_text": "HbA1c",
                    "value_text": "5,4",
                    "unit_text": "%",
                    "observed_at": "2026-09-05",
                    "observed_at_is_date_only": True,
                    "reference_low": "4,0",
                    "reference_high": "6,0",
                    "reference_text": "4,0 - 6,0",
                    "page": 1,
                    "bbox": None,
                    "confidence": "0.95",
                }
            ],
            published=[
                {
                    "kpi_code": "metabolic.hba1c",
                    "analyte_text": "HbA1c",
                    "observed_at": "2026-09-05",
                    "value_text": "5,4",
                    "unit_text": "%",
                    "held_value": "5.4",
                    "held_unit": "%",
                },
                {
                    "kpi_code": "cardio.ldl_c",
                    "analyte_text": "LDL",
                    "observed_at": "2026-09-05",
                    "value_text": "3,1",
                    "unit_text": "mmol/L",
                    "held_value": "3.1",
                    "held_unit": "mmol/L",
                },
            ],
        ),
        Case(
            name="08_b_sued_delta_jump",
            layout="B",
            sampling_date="24.09.2026",
            issue_date="25.09.2026",
            rows=[
                Row("LDL", "310", "mg/dl", "50", "130"),
                Row("HbA1c", "5,6", "%", "4,0", "6,0"),
            ],
            published=[
                {
                    "kpi_code": "cardio.ldl_c",
                    "analyte_text": "LDL",
                    "observed_at": "2026-03-01",
                    "value_text": "2,1",
                    "unit_text": "mmol/L",
                    "held_value": "2.1",
                    "held_unit": "mmol/L",
                },
                {
                    "kpi_code": "metabolic.hba1c",
                    "analyte_text": "HbA1c",
                    "observed_at": "2026-03-01",
                    "value_text": "5,4",
                    "unit_text": "%",
                    "held_value": "5.4",
                    "held_unit": "%",
                },
            ],
        ),
        Case(
            name="09_c_west_dates",
            layout="C",
            sampling_date="18.09.2026",
            issue_date="20.09.2026",
            rows=[
                Row("HbA1c", "5,5", "%", "4,0", "6,0"),
                Row("LDL", "3,0", "mmol/L", None, "3,0", date="05.01.2027"),
                Row("Glucose", "5,0", "mmol/L", "3,9", "5,6", date="01.05.2026"),
                Row("HDL cholesterol", "1,5", "mmol/L", "1,0", None, date="01.01.1965"),
                Row(
                    "Total cholesterol",
                    "5,0",
                    "mmol/L",
                    None,
                    "5,2",
                    proposed={"observed_at": None},
                ),
            ],
        ),
        Case(
            name="10_a_nord_hallucination",
            layout="A",
            sampling_date="05.09.2026",
            issue_date="06.09.2026",
            rows=[
                Row("HbA1c", "5,4", "%", "4,0", "6,0"),
                Row("LDL", "3,1", "mmol/L", None, "3,0"),
                Row("Glucose", "5,1", "mmol/L", "3,9", "5,6", proposed={"value_text": "51"}),
            ],
            extra_proposals=[
                {
                    "analyte_text": "Ferritin",
                    "value_text": "85",
                    "unit_text": "µg/L",
                    "observed_at": "2026-09-05",
                    "observed_at_is_date_only": True,
                    "reference_low": None,
                    "reference_high": None,
                    "reference_text": None,
                    "page": 1,
                    "bbox": None,
                    "confidence": "0.93",
                },
                {
                    "analyte_text": "HDL cholesterol",
                    "value_text": "1,6",
                    "unit_text": "mmol/L",
                    "observed_at": "2026-09-05",
                    "observed_at_is_date_only": True,
                    "reference_low": None,
                    "reference_high": None,
                    "reference_text": None,
                    "page": 3,
                    "bbox": None,
                    "confidence": "0.93",
                },
            ],
        ),
        Case(
            name="11_b_sued_patient_mismatch",
            layout="B",
            sampling_date="10.09.2026",
            issue_date="11.09.2026",
            pdf_dob="30.07.1968",
            proposal_dob="1968-07-30",
            rows=[
                Row("LDL", "128", "mg/dl", "50", "130"),
                Row("HbA1c", "5,2", "%", "4,0", "6,0"),
            ],
        ),
    ]


def dump(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    write_expected = "--write-expected" in argv
    for case in cases():
        inp = HERE / case.name / "input"
        inp.mkdir(parents=True, exist_ok=True)
        pdf = render_pdf(case)
        (inp / "report.pdf").write_bytes(pdf)
        pages_path = inp / "pages.json"
        if not case.scanned or not pages_path.exists() or "--ocr" in argv:
            dump(pages_path, page_texts(pdf, case.scanned))
        dump(inp / "proposal.json", proposal_for(case, pdf))
        dump(inp / "patient.json", patient_for(case))
        if write_expected:
            from tests.intake_support import load_case, run_case, serialize

            dump(
                HERE / case.name / "expected.json", serialize(run_case(load_case(HERE / case.name)))
            )
        print("wrote", case.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
