"""Deterministic, versioned normalization: terminology resolution + unit conversion.

This is the highest patient-safety-risk surface (wrong value/unit/interval). Rules:
- A source name is looked up in the KPI catalog (ADR-0004 §9/§13) through an exact alias, or it
  does not resolve. Nothing is guessed.
- The import acts WITHOUT A HUMAN on a fixed set of names only (`_AUTOMATIC`) — the names
  norm-1 acted on, each bound here to its KPI and unit, and only while the catalog says the
  same. Every other name is held for a human, whatever the catalog knows about it.
- Conversions are deterministic, versioned, and only applied to APPROVED KPI/unit pairs.
- Reference intervals convert with the exact same factor as the value.
- Units are never inferred from a value's magnitude, and neither is the meaning of a decimal
  mark: a number that can be read two ways is not read.
- A value that is not normalized does NOT fail silently and is NOT erased: the source's number
  and its reference bounds are kept, in the source's unit, and the row enters the human review
  queue rather than being published.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from hadp_api.modules.kpi.terms import CatalogTerm

# norm-2: a name is looked up in the KPI catalog (norm-1 held its six names in this module); a
# value that is not normalized keeps its number and its reference bounds in the source's unit; a
# number or an interval that can be read two ways is not read.
NORMALIZATION_VERSION = "norm-2"


class Terminology(Protocol):
    def resolve(self, source_name: str) -> CatalogTerm | None:
        """The catalog KPI an exact, unambiguous alias names — or None. Never a guess."""
        ...


@dataclass(frozen=True)
class _Automatic:
    kpi_code: str
    # The unit the value is held in — the KPI's canonical unit.
    unit: str
    # The source code norm-1 stamped on the name, kept exactly as it was (stored rows, the
    # timeline and the interpretation evidence carry it). Not extended: a code from an
    # external terminology is stamped only from a verified mapping (ADR-0004 §11), and most
    # of these are not in the verified set — see docs/notes/0006.
    legacy_code: str


# The names the import normalizes — and so may publish — without a human, each with the KPI and
# the unit it stands for. Exactly norm-1's six names: looking a name up in the catalog does not
# change which names publish unseen. The catalog has to agree (an active KPI of this code, in
# this unit, under this alias); where it does not, the row waits for a human. A name is added
# here by a decision that names it — signed by a clinician, for a laboratory whose test list is
# known — never by what the catalog happens to contain: an alias says what a name may mean, not
# that a value under it may go unread (ADR-0004 §18).
_AUTOMATIC: dict[str, _Automatic] = {
    "ldl cholesterol": _Automatic("cardio.ldl_c", "mmol/L", "13457-7"),
    "ldl": _Automatic("cardio.ldl_c", "mmol/L", "13457-7"),
    "total cholesterol": _Automatic("cardio.total_cholesterol", "mmol/L", "2093-3"),
    "hdl cholesterol": _Automatic("cardio.hdl_c", "mmol/L", "2085-9"),
    "glucose": _Automatic("metabolic.fasting_plasma_glucose", "mmol/L", "2345-7"),
    "hba1c": _Automatic("metabolic.hba1c", "%", "4548-4"),
}

# Approved unit conversions: (KPI code, source unit, target unit) -> exact factor. The target is
# named, not read from the catalog: a conversion is to one unit. Cholesterol mg/dL -> mmol/L
# uses 0.0258598; glucose uses 0.0555.
_CONVERSIONS: dict[tuple[str, str, str], Decimal] = {
    ("cardio.ldl_c", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("cardio.total_cholesterol", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("cardio.hdl_c", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("metabolic.fasting_plasma_glucose", "mg/dL", "mmol/L"): Decimal("0.0555"),
}

# The three spellings accepted in any letter case; every other unit is compared as written.
_UNIT_SPELLINGS = {"mg/dl": "mg/dL", "mmol/l": "mmol/L", "%": "%"}


@dataclass
class NormalizationResult:
    kpi_code: str | None
    metric_code: str | None
    code_system: str | None
    mapping_confidence: float
    # The source's value as a number, in the source's unit (None when it is not one number).
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


def _canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    text = unit.strip()
    return _UNIT_SPELLINGS.get(text.lower(), text)


def unit_was_converted(original_unit: str | None, normalized_unit: str | None) -> bool:
    """True when normalization changed the unit — and with it the value and the reference
    bounds. A different spelling of the same unit ("mmol/l") is not a conversion; neither is
    a value whose source named no unit."""
    source = _canonical_unit(original_unit)
    return (
        bool(source) and normalized_unit is not None and source != _canonical_unit(normalized_unit)
    )


# A plain decimal number: ASCII digits, an optional sign, `.` or `,` as the decimal separator,
# an optional small exponent. Decimal() itself would also accept NaN, Infinity, digit-group
# underscores ("3_4" -> 34) and other scripts' digits — none of which is a laboratory value.
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]{1,2})?")
# One to three digits, a mark, exactly three digits: "4.000", "1,250", "150.000". Such a number
# reads two ways — the mark is a decimal mark (4), or it groups thousands (4000) — and nothing
# in the value says which. A leading zero settles it ("0.005" groups nothing), and so does an
# exponent. (A number with two marks, "1.234,5" or "12.345.678", is not a plain number at all.)
_GROUPED = re.compile(r"[+-]?[1-9][0-9]{0,2}[.,][0-9]{3}")


def is_plain_number(raw: str) -> bool:
    """Whether a source string is written as a plain decimal number — what a statement may
    repeat. Whether the platform also READS it as one number is `is_one_number`."""
    return _NUMBER.fullmatch(raw.strip()) is not None


def is_one_number(raw: str) -> bool:
    """Whether a source string is a number the platform reads: plainly written, and readable
    one way only."""
    text = raw.strip()
    return _NUMBER.fullmatch(text) is not None and _GROUPED.fullmatch(text) is None


def _parse_decimal(raw: str) -> Decimal | None:
    text = raw.strip()
    if not is_one_number(text):
        return None
    return Decimal(text.replace(",", "."))


def _parse_bound(raw: str | None, reasons: list[str]) -> Decimal | None:
    """Parse a reference bound. A bound the source gives but that cannot be read — it is not a
    number, or it reads two ways — is a reason for review: dropping it silently would turn a
    two-sided interval into a one-sided one."""
    if raw is None or not raw.strip():
        return None
    bound = _parse_decimal(raw)
    if bound is None:
        reason = "ambiguous_reference" if is_plain_number(raw) else "unparseable_reference"
        if reason not in reasons:
            reasons.append(reason)
    return bound


def _interval(
    raw_low: str | None, raw_high: str | None, reasons: list[str]
) -> tuple[Decimal | None, Decimal | None]:
    """The source's reference bounds as numbers. A pair in which the lower bound lies above the
    upper is not an interval: neither bound is held, and a human looks. The source's own
    wording stays in `reference_text` either way."""
    low = _parse_bound(raw_low, reasons)
    high = _parse_bound(raw_high, reasons)
    if low is not None and high is not None and low > high:
        if "ambiguous_reference" not in reasons:
            reasons.append("ambiguous_reference")
        return None, None
    return low, high


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
    automatic = _AUTOMATIC.get(original_name.strip().lower())
    value = _parse_decimal(original_value)

    if (
        automatic is None
        or term is None
        or (term.kpi_code, term.canonical_unit) != (automatic.kpi_code, automatic.unit)
    ):
        # Not a name the import acts on by itself — or one the catalog no longer describes as
        # this module does. The catalog's KPI, if the name has one, is recorded as where the
        # value belongs; the number and its interval are what the source wrote, in the
        # source's unit — kept, not normalized, and held for a human.
        reasons.append("unmapped_metric")
        low, high = _interval(reference_low, reference_high, reasons)
        return NormalizationResult(
            kpi_code=term.kpi_code if term is not None else None,
            metric_code=None,
            code_system=None,
            mapping_confidence=0.0,
            numeric_value=value,
            normalized_value=None,
            normalized_unit=None,
            reference_low=low,
            reference_high=high,
            normalization_version=NORMALIZATION_VERSION,
            review_reasons=reasons,
        )

    if value is None:
        reasons.append("unparseable_value")
    ref_low, ref_high = _interval(reference_low, reference_high, reasons)
    source_unit = _canonical_unit(original_unit)

    normalized_value: Decimal | None = None
    normalized_unit: str | None = None
    # Until a conversion is applied the bounds stay what the source wrote, in its unit.
    held_low, held_high = ref_low, ref_high

    if value is not None:
        if source_unit == automatic.unit:
            normalized_value, normalized_unit = value, automatic.unit
        else:
            factor = _CONVERSIONS.get((automatic.kpi_code, source_unit or "", automatic.unit))
            if factor is None:
                reasons.append("unsupported_unit")
            else:
                # Reference intervals convert with the SAME exact factor as the value.
                normalized_value, normalized_unit = value * factor, automatic.unit
                held_low = ref_low * factor if ref_low is not None else None
                held_high = ref_high * factor if ref_high is not None else None

    # Impossible/implausible: these quantities are non-negative.
    if normalized_value is not None and normalized_value < 0:
        reasons.append("impossible_value")

    return NormalizationResult(
        kpi_code=automatic.kpi_code,
        metric_code=automatic.legacy_code,
        code_system="LOINC",
        mapping_confidence=1.0 if not reasons else 0.4,
        numeric_value=value,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        reference_low=held_low,
        reference_high=held_high,
        normalization_version=NORMALIZATION_VERSION,
        review_reasons=reasons,
    )
