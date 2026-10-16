"""Where a proposed value is printed on its page: found by code, never taken from a model.

A model reads; it does not say where. A box it sends is not evidence: drawn around the wrong
row, it would show a clinician a crop that seems to confirm a reading it does not. So the box
the confirmation screen crops is computed here, from the stored PDF's text layer, and a box in
the proposal is never stored (`service.create_pending_batch`).

`locate_value` looks for the value as written, as a number of its own (the rule of the
`on_page` check), among the page's words grouped into printed lines:

1. On the line that carries the analyte's name: the first occurrence to the right of the name,
   so a number printed twice on its row (a value equal to its reference bound) is placed in the
   value column; else the only occurrence on that row outside the name itself.
2. Otherwise, when no line carries both: the only place on the page the value is printed.
3. Anything less certain gives no box: the name and the value together on several rows, or the
   value in several places and the name on none of them. The screen then shows the whole page.
   No crop is better than a crop that points at the wrong number.

A page read by OCR has no word positions here and never gets a box.
"""

from __future__ import annotations

from collections.abc import Sequence

from hadp_api.modules.documents.pdf_text import Word
from hadp_api.modules.intake import checks

# [x0, top, x1, bottom] in PDF points, origin top-left.
Box = tuple[float, float, float, float]
# First and last word index of a match within one line.
_Hit = tuple[int, int]


def lines_of(words: Sequence[Word]) -> list[tuple[Word, ...]]:
    """The words grouped into printed lines, top to bottom, each read left to right. A word
    joins the line above it when their vertical extents overlap by half the smaller height."""
    lines: list[list[Word]] = []
    bands: list[tuple[float, float]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if lines:
            top, bottom = bands[-1]
            overlap = min(bottom, word.bottom) - max(top, word.top)
            height = min(bottom - top, word.bottom - word.top)
            if overlap > 0 and overlap >= 0.5 * height:
                lines[-1].append(word)
                bands[-1] = (min(top, word.top), max(bottom, word.bottom))
                continue
        lines.append([word])
        bands.append((word.top, word.bottom))
    return [tuple(sorted(line, key=lambda w: w.x0)) for line in lines]


def _joined(line: tuple[Word, ...], *, fold: bool) -> tuple[str, list[tuple[int, int]]]:
    """The line as text (words joined by one space) and each word's character span in it."""
    parts: list[str] = []
    spans: list[tuple[int, int]] = []
    at = 0
    for word in line:
        text = word.text.casefold() if fold else word.text
        parts.append(text)
        spans.append((at, at + len(text)))
        at += len(text) + 1
    return " ".join(parts), spans


def _covered(spans: list[tuple[int, int]], start: int, end: int) -> _Hit | None:
    hit = [i for i, (a, b) in enumerate(spans) if a < end and start < b]
    return (hit[0], hit[-1]) if hit else None


def _box(words: Sequence[Word]) -> Box:
    return (
        round(min(w.x0 for w in words), 1),
        round(min(w.top for w in words), 1),
        round(max(w.x1 for w in words), 1),
        round(max(w.bottom for w in words), 1),
    )


def _value_hits(line: tuple[Word, ...], value_text: str) -> list[_Hit]:
    pattern = checks.value_pattern(value_text)
    if pattern is None:
        return []
    text, spans = _joined(line, fold=False)
    return [h for m in pattern.finditer(text) if (h := _covered(spans, m.start(), m.end()))]


def _name_hits(line: tuple[Word, ...], analyte_text: str) -> list[_Hit]:
    needle = checks.analyte_key(analyte_text)
    if not needle:
        return []
    text, spans = _joined(line, fold=True)
    hits: list[_Hit] = []
    at = text.find(needle)
    while at != -1:
        if (hit := _covered(spans, at, at + len(needle))) is not None:
            hits.append(hit)
        at = text.find(needle, at + 1)
    return hits


def _on_name_row(values: list[_Hit], names: list[_Hit]) -> _Hit | None:
    """The value occurrence that belongs to the name on this row, if one does unambiguously."""
    outside = [v for v in values if not any(v[0] <= n[1] and n[0] <= v[1] for n in names)]
    after = [v for v in outside if v[0] > names[0][1]]
    if after:
        return after[0]
    return outside[0] if len(outside) == 1 else None


def locate_value(words: Sequence[Word], analyte_text: str, value_text: str) -> Box | None:
    """The box of the printed value on a text-layer page, or None when code cannot place it
    with certainty (see the module docstring)."""
    on_name_rows: list[tuple[Word, ...]] = []
    anywhere: list[tuple[Word, ...]] = []
    for line in lines_of(words):
        values = _value_hits(line, value_text)
        if not values:
            continue
        anywhere.extend(line[a : b + 1] for a, b in values)
        names = _name_hits(line, analyte_text)
        if names and (hit := _on_name_row(values, names)) is not None:
            on_name_rows.append(line[hit[0] : hit[1] + 1])
    if len(on_name_rows) == 1:
        return _box(on_name_rows[0])
    if not on_name_rows and len(anywhere) == 1:
        return _box(anywhere[0])
    return None


def line_extent(words: Sequence[Word], box: Box) -> tuple[float, float]:
    """Left and right edge of the printed line a box sits on, so a crop can show the whole row
    (the analyte's name included); the box's own edges when no word shares its line."""
    x0, top, x1, bottom = box
    height = bottom - top
    row = [
        w
        for w in words
        if min(bottom, w.bottom) - max(top, w.top) > 0
        and min(bottom, w.bottom) - max(top, w.top) >= 0.5 * min(height, w.bottom - w.top)
    ]
    return min([x0, *(w.x0 for w in row)]), max([x1, *(w.x1 for w in row)])
