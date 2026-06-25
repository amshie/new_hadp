"""Pure predicate: where a value sits relative to its lab-provided reference interval.

This is the SINGLE source of truth for the above/below/within determination. It states
only a deterministic FACT about the value versus the laboratory-provided interval — it
never introduces an "optimal"/normal bound and never asserts a clinical verdict.

Two callers rely on these exact semantics: the deterministic narrative provider
(`modules/reports/narrative.py`) and the web "Lage zum Referenzintervall" column. The
TypeScript twin in `apps/web/src/lib/referencePosition.ts` mirrors this truth table; the
authoritative cases live in `apps/api/tests/test_reference_position.py`. The planned
`out_of_source_interval` rule (docs/notes/0009) reuses this helper so the comparison has
one implementation, not three (the drift the 0009 review flagged).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

ReferencePosition = Literal["above", "below", "within", "no_reference", "not_evaluable"]


def position_vs_source_interval(
    value: Decimal | None,
    reference_low: Decimal | None,
    reference_high: Decimal | None,
) -> ReferencePosition:
    """Position of ``value`` relative to the lab interval ``[low, high]``.

    - no value                            -> ``"not_evaluable"``
    - no bound at all                     -> ``"no_reference"``
    - value strictly above the high bound -> ``"above"``
    - value strictly below the low bound  -> ``"below"``
    - both bounds present, not exceeded   -> ``"within"``
    - one-sided bound, not exceeded       -> ``"not_evaluable"`` (cannot place in an interval)

    Equality with a bound is ``"within"`` (strict inequalities), matching the narrative
    provider. A one-sided interval never yields a guessed ``"within"``.
    """
    if value is None:
        return "not_evaluable"
    if reference_low is None and reference_high is None:
        return "no_reference"
    if reference_high is not None and value > reference_high:
        return "above"
    if reference_low is not None and value < reference_low:
        return "below"
    if reference_low is not None and reference_high is not None:
        return "within"
    return "not_evaluable"
