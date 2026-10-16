"""Page texts of a stored PDF — the text layer only.

Used by the intake checks to confirm that what a model proposed stands on the page it cites.
A page without a text layer (a scan) yields '' here: OCR is an explicit, separate step, never
a default (CLAUDE.md), and until it runs such a page confirms nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from hadp_api.modules.documents.pdf_render import open_pdf

# A laboratory report beyond this is a different kind of document (CLAUDE.md: page limits).
MAX_PAGES = 50


class PdfUnreadable(Exception):
    """The bytes are not a PDF this reader can open. `detail` names no content."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class PdfPages:
    texts: tuple[str, ...]

    @property
    def page_count(self) -> int:
        return len(self.texts)

    def text(self, page: int) -> str:
        if page < 1 or page > len(self.texts):
            return ""
        return self.texts[page - 1]


def read_pages(data: bytes) -> PdfPages:
    """The text of every page, in page order. Refuses a file that is not a PDF, an encrypted
    PDF, and a PDF with more than MAX_PAGES pages."""
    if not data.startswith(b"%PDF-"):
        raise PdfUnreadable("not_a_pdf")
    try:
        with open_pdf(data) as pdf:
            if pdf.doc.is_extractable is False:
                raise PdfUnreadable("encrypted")
            if len(pdf.pages) > MAX_PAGES:
                raise PdfUnreadable("too_many_pages")
            texts = tuple((page.extract_text() or "") for page in pdf.pages)
    except PdfUnreadable:
        raise
    except Exception as exc:  # noqa: BLE001 - the library raises many types; the name suffices
        raise PdfUnreadable(type(exc).__name__) from exc
    if not texts:
        raise PdfUnreadable("no_pages")
    return PdfPages(texts)
