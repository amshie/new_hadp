# 05 — Praxislabor West, scanned (image-only) report

**Layout C** rendered to an image at 200 dpi and embedded as a page **without a text layer**.
`pages.json` holds what tesseract 5.3.4 (deu) read from it; the text-layer reader finds nothing.

**What must hold**

- The OCR misreads "HbA1c" as "HbAlc" → `analyte_not_on_page` (red) for HbA1c even though the
  value itself is right: a proposal is confirmed against the page text, not against intuition.
- LDL and glucose are on the OCR text verbatim; with confidence 0.80 / 0.85 they are yellow
  (`low_confidence`) and must be viewed before confirmation.
- Nothing is green on a scan at these confidences.

**Why it matters** — OCR is the last resort (CLAUDE.md); this case shows what it costs and that
the verbatim check catches its characteristic error rather than passing it through.
