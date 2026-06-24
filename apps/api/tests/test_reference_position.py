"""Authoritative truth table for the value-vs-source-interval predicate.

This pins the semantics the narrative provider, the web "Lage zum Referenzintervall"
column (apps/web/src/lib/referencePosition.ts — a hand-kept TS twin), and the planned
out_of_source_interval rule all share. The doctrine-critical case is `no_reference`: a
marker with no lab interval (the SYN-* values) must NEVER read as within/normal.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hadp_api.modules.observations.reference_position import position_vs_source_interval


def _d(x: str) -> Decimal:
    return Decimal(x)


@pytest.mark.parametrize(
    ("value", "low", "high", "expected"),
    [
        # two-sided intervals (the shape every seed reference uses)
        ("3.6", "0", "3.0", "above"),  # LDL 3.6, ref 0-3.0
        ("1.02", "0", "1.0", "above"),  # ApoB 1.02, ref 0-1.0
        ("5.3", "3.9", "5.6", "within"),  # Nuechternglukose
        ("2.0", "3.9", "5.6", "below"),
        # equality with a bound is strictly within (matches narrative.py strict inequalities)
        ("3.0", "0", "3.0", "within"),
        ("3.9", "3.9", "5.6", "within"),
        # no value -> not evaluable
        (None, "0", "3.0", "not_evaluable"),
        # one-sided intervals: exceeded states a fact; not-exceeded never guesses "within"
        ("4.0", None, "3.0", "above"),
        ("1.0", None, "3.0", "not_evaluable"),
        ("1.0", "3.9", None, "below"),
        ("5.0", "3.9", None, "not_evaluable"),
    ],
)
def test_position(value: str | None, low: str | None, high: str | None, expected: str) -> None:
    v = None if value is None else _d(value)
    lo = None if low is None else _d(low)
    hi = None if high is None else _d(high)
    assert position_vs_source_interval(v, lo, hi) == expected


def test_no_reference_never_reads_as_within() -> None:
    # SYN-* markers (VO2max, HRV, grip strength, appendicular lean mass) carry no interval.
    # The single most important invariant: this must be "no_reference", never "within".
    assert position_vs_source_interval(_d("21"), None, None) == "no_reference"
    assert position_vs_source_interval(None, None, None) == "not_evaluable"
