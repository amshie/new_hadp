"""The generated narrative must never cross the intended-use language boundary.

The deterministic provider is the surface that produces patient/clinician-facing clinical
prose, so it is the surface most likely to regress into prohibited claims. This guards it
directly across above/below/within-interval and change cases.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from hadp_api.modules.reports.language import restricted_terms
from hadp_api.modules.reports.narrative import DeterministicNarrativeProvider, EvidenceItem

# Restricted terms (substring, case-insensitive) from the intended-use boundary.
FORBIDDEN = [
    "diagnos",
    "treatment",
    "prescrib",
    "medication",
    "supplement",
    "risk score",
    "biological age",
    "optimal",
    "disease",
    "recommend",
    "cure",
]

# The provider writes German. This guards its OWN templates (with one fixed analyte name)
# against the German words for the same claims. It is a test of generated text only — not the
# write-time term list for human edits (modules/reports/language.py), whose extension to
# German is a recorded open decision. It says nothing about what a source supplies: an
# analyte name is printed as written, a result only if it is a number, a unit only if it is
# one token (tests/test_narrative_wording.py, tests/test_report_statements_api.py).
FORBIDDEN_GERMAN = [
    "therap",
    "behandl",
    "empfehl",
    "empfohlen",
    "medikament",
    "arznei",
    "nahrungsergänz",
    "krank",
    "heil",
    "risiko",
    "biologisches alter",
    "normal",
    "auffällig",
    "gesund",
]


def _item(value: str, low: str | None, high: str | None, delta: str | None = None) -> EvidenceItem:
    return EvidenceItem(
        observation_id=uuid.uuid4(),
        metric_code="13457-7",
        name="LDL Cholesterol",
        source_value=value,
        source_unit="mmol/L",
        value=Decimal(value),
        unit="mmol/L",
        converted=False,
        reference_low=Decimal(low) if low is not None else None,
        reference_high=Decimal(high) if high is not None else None,
        observed_at_label="10.06.2025 um 08:30 Uhr (UTC+2)",
        delta_vs_previous=Decimal(delta) if delta is not None else None,
        previous_observation_id=uuid.uuid4() if delta is not None else None,
    )


def test_narrative_contains_no_prohibited_claims() -> None:
    payload = [
        _item("2.8", "0", "3.0"),  # within interval
        _item("3.6", "0", "3.0", delta="-0.8"),  # above interval, with change
        _item("0.2", "0.5", "3.0"),  # below interval
        _item("1.0", None, "3.0"),  # one-sided interval (upper bound only)
        _item("1.0", "0.5", None),  # one-sided interval (lower bound only)
        _item("1.0", None, None),  # no interval
    ]
    unquoted = _item("1.0", None, None)
    unquoted.source_value = None  # a result the statement mentions without quoting
    payload.append(unquoted)
    statements = DeterministicNarrativeProvider().generate(payload)
    assert statements
    blob = " ".join(s.text for s in statements).lower()
    for term in FORBIDDEN + FORBIDDEN_GERMAN:
        assert term not in blob, f"prohibited term in narrative: {term!r}"
    # The write-time guard for human edits must accept every generated statement unchanged.
    assert restricted_terms(s.text for s in statements) == []


def test_every_statement_is_evidence_linked() -> None:
    statements = DeterministicNarrativeProvider().generate([_item("2.8", "0", "3.0")])
    assert all(s.evidence_observation_ids for s in statements)
