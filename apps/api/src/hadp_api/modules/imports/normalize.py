"""Deterministic, versioned normalization: terminology resolution + unit conversion.

This is the highest patient-safety-risk surface (wrong value/unit/interval). Rules:
- The terminology is the KPI catalog (ADR-0004 §9/§13): a source name resolves to a canonical
  KPI through an exact alias, or it does not resolve. Nothing is guessed.
- Conversions are deterministic, versioned, and only applied to APPROVED KPI/unit pairs.
- Reference intervals convert with the exact same factor as the value.
- Units are never inferred from a value's magnitude. A unit is compared in the catalog's
  notation (UCUM); bringing a source spelling into that notation is not a conversion.
- An unknown name or an unsupported unit does NOT fail silently and does NOT erase the
  value: the source's number and its reference bounds are kept, in the source's unit, and the
  row enters the human review queue rather than being published.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from hadp_api.modules.kpi.terms import CatalogTerm

# norm-2: the terminology is the KPI catalog (norm-1 knew six names); a value that is not
# normalized keeps its number and its reference bounds in the source's unit.
NORMALIZATION_VERSION = "norm-2"


class Terminology(Protocol):
    def resolve(self, source_name: str) -> CatalogTerm | None:
        """The catalog KPI an exact, unambiguous alias names — or None. Never a guess."""
        ...


# Source codes norm-1 stamped on six names, kept exactly as they were (stored rows, the
# timeline and the interpretation evidence carry them). NOT extended: a code from an external
# terminology is stamped only from a verified mapping (ADR-0004 §11), and most of these are not
# in the verified set — see docs/notes/0006.
_LEGACY_METRIC_CODES: dict[str, str] = {
    "ldl cholesterol": "13457-7",
    "ldl": "13457-7",
    "total cholesterol": "2093-3",
    "hdl cholesterol": "2085-9",
    "glucose": "2345-7",
    "hba1c": "4548-4",
}

# Approved unit conversions: (KPI code, source unit in catalog notation) -> exact factor to the
# KPI's canonical unit. Cholesterol mg/dL -> mmol/L uses 0.0258598; glucose uses 0.0555.
_CONVERSIONS: dict[tuple[str, str], Decimal] = {
    ("cardio.ldl_c", "mg/dL"): Decimal("0.0258598"),
    ("cardio.total_cholesterol", "mg/dL"): Decimal("0.0258598"),
    ("cardio.hdl_c", "mg/dL"): Decimal("0.0258598"),
    ("metabolic.fasting_plasma_glucose", "mg/dL"): Decimal("0.0555"),
}

# Spellings norm-1 accepted in any letter case; kept so a stored row reads as it did.
_LEGACY_SPELLINGS = {"mg/dl": "mg/dL", "mmol/l": "mmol/L", "%": "%"}
# The litre, alone or with a metric prefix. UCUM writes it "l" or "L"; the catalog uses "L".
_LITRE = frozenset({"l", "dl", "cl", "ml", "ul", "nl", "pl", "fl"})
_UNIT_SEPARATORS = re.compile(r"([/.])")


@dataclass
class NormalizationResult:
    kpi_code: str | None
    metric_code: str | None
    code_system: str | None
    mapping_confidence: float
    # The source's value as a number, in the source's unit (None when it is not a number).
    numeric_value: Decimal | None
    normalized_value: Decimal | None
    normalized_unit: str | None
    # The source's bounds as numbers, in the unit of the value the platform holds: the
    # canonical unit when the value was normalized, otherwise the source's own unit.
    reference_low: Decimal | None
    reference_high: Decimal | None
    normalization_version: str
    review_reasons: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.review_reasons)


def unit_notation(unit: str | None) -> str | None:
    """A source unit written the way the catalog writes units — notation only.

    Two things change, both defined by UCUM and neither a conversion: the micro sign becomes
    "u", and a litre becomes "L". Everything else is left exactly as written and compared
    case-sensitively: "G/l" (10^9 per litre) and "g/l" (gram per litre) stay different units.
    """
    if unit is None:
        return None
    text = unit.strip()
    legacy = _LEGACY_SPELLINGS.get(text.lower())
    if legacy is not None:
        return legacy
    text = text.replace("µ", "u").replace("μ", "u")
    parts = _UNIT_SEPARATORS.split(text)
    return "".join(part[:-1] + "L" if part in _LITRE else part for part in parts)


def unit_was_converted(original_unit: str | None, normalized_unit: str | None) -> bool:
    """True when normalization changed the unit — and with it the value and the reference
    bounds. A different spelling of the same unit ("mmol/l") is not a conversion; neither is
    a value whose source named no unit."""
    source = unit_notation(original_unit)
    return bool(source) and normalized_unit is not None and source != unit_notation(normalized_unit)


# A plain decimal number: ASCII digits, an optional sign, `.` or `,` as the decimal separator,
# an optional small exponent. Decimal() itself would also accept NaN, Infinity, digit-group
# underscores ("3_4" -> 34) and other scripts' digits — none of which is a laboratory value.
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]{1,2})?")


def is_plain_number(raw: str) -> bool:
    """Whether a source string is a plain decimal number in the grammar this module reads."""
    return _NUMBER.fullmatch(raw.strip()) is not None


def _parse_decimal(raw: str) -> Decimal | None:
    text = raw.strip()
    if not _NUMBER.fullmatch(text):
        return None
    return Decimal(text.replace(",", "."))


def _parse_bound(raw: str | None, reasons: list[str]) -> Decimal | None:
    """Parse a reference bound. A bound the source gives but that is not a number is a reason
    for review — dropping it silently would turn a two-sided interval into a one-sided one."""
    if raw is None or not raw.strip():
        return None
    bound = _parse_decimal(raw)
    if bound is None and "unparseable_reference" not in reasons:
        reasons.append("unparseable_reference")
    return bound


def normalize(
    *,
    terminology: Terminology,
    original_name: str,
    original_value: str,
    original_unit: str | None,
    reference_low: str | None = None,
    reference_high: str | None = None,
) -> NormalizationResult:
    reasons: list[str] = []
    term = terminology.resolve(original_name)
    value = _parse_decimal(original_value)

    if term is None or not term.automatic or term.canonical_unit is None:
        # No mapping the import may act on by itself. The number and its bounds are what the
        # source wrote, in the source's unit — kept, not normalized, and held for a human.
        reasons.append("unmapped_metric")
        return NormalizationResult(
            kpi_code=term.kpi_code if term is not None else None,
            metric_code=None,
            code_system=None,
            mapping_confidence=0.0,
            numeric_value=value,
            normalized_value=None,
            normalized_unit=None,
            reference_low=_parse_bound(reference_low, reasons),
            reference_high=_parse_bound(reference_high, reasons),
            normalization_version=NORMALIZATION_VERSION,
            review_reasons=reasons,
        )

    if value is None:
        reasons.append("unparseable_value")
    ref_low = _parse_bound(reference_low, reasons)
    ref_high = _parse_bound(reference_high, reasons)
    source_unit = unit_notation(original_unit)

    normalized_value: Decimal | None = None
    normalized_unit: str | None = None
    # Until a conversion is applied the bounds stay what the source wrote, in its unit.
    held_low, held_high = ref_low, ref_high

    if value is not None:
        if source_unit == term.canonical_unit:
            normalized_value, normalized_unit = value, term.canonical_unit
        else:
            factor = _CONVERSIONS.get((term.kpi_code, source_unit or ""))
            if factor is None:
                reasons.append("unsupported_unit")
            else:
                # Reference intervals convert with the SAME exact factor as the value.
                normalized_value, normalized_unit = value * factor, term.canonical_unit
                held_low = ref_low * factor if ref_low is not None else None
                held_high = ref_high * factor if ref_high is not None else None

    # Impossible/implausible: the catalog's quantities are non-negative.
    if normalized_value is not None and normalized_value < 0:
        reasons.append("impossible_value")

    metric_code = _LEGACY_METRIC_CODES.get(original_name.strip().lower())
    return NormalizationResult(
        kpi_code=term.kpi_code,
        metric_code=metric_code,
        code_system="LOINC" if metric_code is not None else None,
        mapping_confidence=1.0 if not reasons else 0.4,
        numeric_value=value,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        reference_low=held_low,
        reference_high=held_high,
        normalization_version=NORMALIZATION_VERSION,
        review_reasons=reasons,
    )
