"""The page texts of a stored PDF, with OCR as an EXPLICIT step — never a default.

`load_pages` reads the text layer. A page without one (a scan) stays empty unless the
deployment has switched OCR on (`INTAKE_OCR=tesseract`); then that page, and only that page,
is rendered and read by tesseract, and the page's text is marked as coming from OCR. The checks
see the source: a value confirmed against OCR text is never green (`page_text_from_ocr`), because
OCR misreads look exactly like readings (CLAUDE.md: OCR is the last resort).

The engine is a subprocess (`tesseract`), chosen so the deployment decides what is installed;
a configured engine that is missing is an error at the first scan, not a silent fallback.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from hadp_api.config import Settings
from hadp_api.modules.documents.pdf_render import open_pdf
from hadp_api.modules.documents.pdf_text import PdfUnreadable, Word, read_pages

TEXT_LAYER = "text_layer"
OCR = "ocr"
NONE = "none"

OCR_OFF = "off"
OCR_TESSERACT = "tesseract"
# Resolution the scan is rendered at for the OCR engine.
OCR_DPI = 200


class OcrEngine(Protocol):
    @property
    def name(self) -> str: ...

    def read(self, png: bytes) -> str: ...


class OcrUnavailable(Exception):
    """OCR is configured but cannot run here. `detail` names the engine, never content."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class PageSet:
    """Page texts with, per page, where the text came from — and, for a text-layer page, where
    each word is printed. OCR text carries no positions here."""

    texts: tuple[str, ...]
    sources: tuple[str, ...]
    words: tuple[tuple[Word, ...], ...] = ()

    @property
    def page_count(self) -> int:
        return len(self.texts)

    def text(self, page: int) -> str:
        return self.texts[page - 1] if 1 <= page <= len(self.texts) else ""

    def source(self, page: int) -> str:
        return self.sources[page - 1] if 1 <= page <= len(self.sources) else NONE

    def words_on(self, page: int) -> tuple[Word, ...]:
        """The positioned words of a text-layer page; none for an OCR page or a scan."""
        if self.source(page) != TEXT_LAYER or not 1 <= page <= len(self.words):
            return ()
        return self.words[page - 1]


@dataclass(frozen=True)
class TesseractEngine:
    languages: str = "deu+eng"

    @property
    def name(self) -> str:
        return "tesseract"

    def version(self) -> str:
        binary = shutil.which("tesseract")
        if binary is None:
            raise OcrUnavailable("tesseract is not installed")
        out = subprocess.run([binary, "--version"], check=True, capture_output=True, text=True)
        return out.stdout.splitlines()[0].strip() if out.stdout else "tesseract"

    def read(self, png: bytes) -> str:
        binary = shutil.which("tesseract")
        if binary is None:
            raise OcrUnavailable("tesseract is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.png"
            path.write_bytes(png)
            out = subprocess.run(
                [binary, str(path), "stdout", "-l", self.languages, "--psm", "6"],
                check=True,
                capture_output=True,
                text=True,
            )
        return out.stdout


def engine_for(settings: Settings) -> OcrEngine | None:
    if settings.intake_ocr == OCR_OFF:
        return None
    if settings.intake_ocr == OCR_TESSERACT:
        return TesseractEngine(languages=settings.intake_ocr_languages)
    raise OcrUnavailable(f"unknown OCR engine {settings.intake_ocr!r}")


def _render_page_png(data: bytes, page_no: int) -> bytes:
    with open_pdf(data) as pdf:
        buf = io.BytesIO()
        pdf.pages[page_no - 1].to_image(resolution=OCR_DPI).original.save(buf, format="PNG")
        return buf.getvalue()


def load_pages(data: bytes, settings: Settings, *, engine: OcrEngine | None = None) -> PageSet:
    """Text layer first; OCR only for a page without one, and only when configured.

    Raises PdfUnreadable for a file that is not a readable PDF and OcrUnavailable when OCR is
    configured but cannot run — a scan then confirms nothing, visibly.
    """
    layer = read_pages(data)
    texts = list(layer.texts)
    sources = [TEXT_LAYER if t.strip() else NONE for t in texts]
    ocr = engine if engine is not None else engine_for(settings)
    if ocr is not None:
        for index, text in enumerate(texts):
            if text.strip():
                continue
            texts[index] = ocr.read(_render_page_png(data, index + 1))
            sources[index] = OCR if texts[index].strip() else NONE
    return PageSet(tuple(texts), tuple(sources), layer.words)


__all__ = [
    "NONE",
    "OCR",
    "OCR_OFF",
    "OCR_TESSERACT",
    "TEXT_LAYER",
    "OcrEngine",
    "OcrUnavailable",
    "PageSet",
    "PdfUnreadable",
    "TesseractEngine",
    "Word",
    "engine_for",
    "load_pages",
]
