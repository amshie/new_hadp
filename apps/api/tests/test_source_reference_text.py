"""The reference text an imported value carries when the source wrote no wording of its own:
built from the bounds the source gave, and only from those (CLAUDE.md, "missing or one-sided
reference intervals")."""

from __future__ import annotations

import pytest

from hadp_api.modules.imports.service import source_reference_text


@pytest.mark.parametrize(
    ("text", "low", "high", "unit", "expected"),
    [
        # The source's own wording wins, verbatim.
        ("< 5,7 %", "0", "5.7", "%", "< 5,7 %"),
        # Both bounds, as the source wrote them.
        (None, "0", "3.0", "mmol/L", "0-3.0 mmol/L"),
        (None, "3,5", "5,1", None, "3,5-5,1"),
        # One bound: named as that bound — never "None-3", never an invented other bound.
        (None, None, "3.0", "mmol/L", "obere Grenze 3.0 mmol/L"),
        (None, "", "3.0", "mmol/L", "obere Grenze 3.0 mmol/L"),
        (None, "0,5", None, "mg/L", "untere Grenze 0,5 mg/L"),
        (None, "0,5", "  ", None, "untere Grenze 0,5"),
        # No bound, no wording: no reference text.
        (None, None, None, "mmol/L", None),
        (None, " ", "", "mmol/L", None),
    ],
)
def test_reference_text_names_only_what_the_source_gave(
    text: str | None, low: str | None, high: str | None, unit: str | None, expected: str | None
) -> None:
    assert source_reference_text(text, low, high, unit) == expected
