"""OCR is an explicit step: off by default, per page, marked, and never green."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from hadp_api.config import get_settings
from hadp_api.modules.intake import pages as pages_mod
from hadp_api.modules.intake.checks import check_on_page
from hadp_api.modules.intake.providers import TextLayerProvider
from tests.intake_support import CASES_DIR, load_case

SCAN = (CASES_DIR / "05_c_west_scanned" / "input" / "report.pdf").read_bytes()
TEXT = (CASES_DIR / "01_a_nord_all_green" / "input" / "report.pdf").read_bytes()


@dataclass(frozen=True)
class FakeOcr:
    text: str = "Praxislabor West synthetisch\nHbA1c: 5,9 % [4,0 - 6,0]\nLDL: 3,4 mmol/L [< 3,0]\n"

    @property
    def name(self) -> str:
        return "fake-ocr"

    def read(self, png: bytes) -> str:
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        return self.text


def test_off_by_default_a_scan_has_no_text_and_confirms_nothing() -> None:
    settings = get_settings()
    assert settings.intake_ocr == "off"
    pages = pages_mod.load_pages(SCAN, settings)
    assert pages.page_count == 1 and pages.text(1) == "" and pages.source(1) == "none"
    case = load_case(CASES_DIR / "05_c_west_scanned")
    result = check_on_page(case.batch.values[0], pages)
    assert result.reason == "no_page_text"


def test_a_text_layer_page_is_never_sent_to_ocr() -> None:
    class Loud:
        name = "loud"

        def read(self, png: bytes) -> str:
            raise AssertionError("OCR ran on a page that has a text layer")

    pages = pages_mod.load_pages(TEXT, get_settings(), engine=Loud())
    assert pages.source(1) == "text_layer" and "HbA1c" in pages.text(1)


def test_with_an_engine_the_scan_is_read_marked_and_its_values_are_yellow() -> None:
    pages = pages_mod.load_pages(SCAN, get_settings(), engine=FakeOcr())
    assert pages.source(1) == "ocr" and "LDL: 3,4 mmol/L" in pages.text(1)
    case = load_case(CASES_DIR / "05_c_west_scanned")
    ldl = next(v for v in case.batch.values if v.analyte_text == "LDL")
    result = check_on_page(ldl, pages)
    assert result.reason == "page_text_from_ocr" and result.severity == "yellow"
    # The text-layer provider reads OCR text like any other and proposes from it.
    proposal = TextLayerProvider().extract(SCAN, pages)
    assert [v.analyte_text for v in proposal.values] == ["HbA1c", "LDL"]


def test_a_configured_engine_that_is_missing_is_an_error_not_a_fallback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(pages_mod.OcrUnavailable, match="not installed"):
        pages_mod.load_pages(SCAN, get_settings(), engine=pages_mod.TesseractEngine())
    monkeypatch.setenv("INTAKE_OCR", "nonsense")
    get_settings.cache_clear()
    try:
        with pytest.raises(pages_mod.OcrUnavailable, match="unknown OCR engine"):
            pages_mod.engine_for(get_settings())
    finally:
        monkeypatch.delenv("INTAKE_OCR")
        get_settings.cache_clear()


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed here")
def test_tesseract_reads_the_synthetic_scan() -> None:
    pages = pages_mod.load_pages(SCAN, get_settings(), engine=pages_mod.TesseractEngine())
    assert pages.source(1) == "ocr"
    text = " ".join(pages.text(1).split())
    assert "3,4 mmol/L" in text and "Praxislabor West" in text
    assert Path(shutil.which("tesseract") or "").name == "tesseract"
