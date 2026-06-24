"""Deterministic, versioned normalization: terminology mapping + unit conversion.

This is the highest patient-safety-risk surface (wrong value/unit/interval). Rules:
- Conversions are deterministic, versioned, and only applied to APPROVED metric/unit pairs.
- Reference intervals convert with the exact same factor as the value.
- Units are never inferred from a value's magnitude.
- Unknown terms or unsupported units do NOT fail silently — they are returned with
  review reasons so the row enters the human review queue rather than being published.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

NORMALIZATION_VERSION = "norm-1"

# Terminology: source name (lowercased) -> (LOINC code, canonical unit).
_TERMINOLOGY: dict[str, tuple[str, str]] = {
    "ldl cholesterol": ("13457-7", "mmol/L"),
    "ldl": ("13457-7", "mmol/L"),
    "total cholesterol": ("2093-3", "mmol/L"),
    "hdl cholesterol": ("2085-9", "mmol/L"),
    "glucose": ("2345-7", "mmol/L"),
    "hba1c": ("4548-4", "%"),
}

# Approved unit conversions keyed by (metric_code, from_unit, to_unit) -> exact factor.
# Cholesterol mg/dL -> mmol/L uses the molar-mass factor 0.0258598; glucose uses 0.0555.
_CONVERSIONS: dict[tuple[str, str, str], Decimal] = {
    ("13457-7", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("2093-3", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("2085-9", "mg/dL", "mmol/L"): Decimal("0.0258598"),
    ("2345-7", "mg/dL", "mmol/L"): Decimal("0.0555"),
}


@dataclass
class NormalizationResult:
    metric_code: str | None
    code_system: str | None
    mapping_confidence: float
    normalized_value: Decimal | None
    normalized_unit: str | None
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
    u = unit.strip()
    aliases = {"mg/dl": "mg/dL", "mmol/l": "mmol/L", "%": "%"}
    return aliases.get(u.lower(), u)


def _parse_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def normalize(
    *,
    original_name: str,
    original_value: str,
    original_unit: str | None,
    reference_low: str | None = None,
    reference_high: str | None = None,
) -> NormalizationResult:
    reasons: list[str] = []
    name_key = original_name.strip().lower()
    mapping = _TERMINOLOGY.get(name_key)

    if mapping is None:
        # Never guess a terminology code with high confidence.
        return NormalizationResult(
            metric_code=None,
            code_system=None,
            mapping_confidence=0.0,
            normalized_value=None,
            normalized_unit=None,
            reference_low=None,
            reference_high=None,
            normalization_version=NORMALIZATION_VERSION,
            review_reasons=["unmapped_metric"],
        )

    metric_code, canonical_unit = mapping
    value = _parse_decimal(original_value)
    if value is None:
        reasons.append("unparseable_value")

    src_unit = _canonical_unit(original_unit)
    ref_low = _parse_decimal(reference_low) if reference_low is not None else None
    ref_high = _parse_decimal(reference_high) if reference_high is not None else None

    normalized_value: Decimal | None = None
    norm_low: Decimal | None = None
    norm_high: Decimal | None = None
    normalized_unit: str | None = None

    if value is not None:
        if src_unit == canonical_unit:
            normalized_value, norm_low, norm_high = value, ref_low, ref_high
            normalized_unit = canonical_unit
        else:
            factor = _CONVERSIONS.get((metric_code, src_unit or "", canonical_unit))
            if factor is None:
                reasons.append("unsupported_unit")
            else:
                # Reference intervals convert with the SAME exact factor as the value.
                normalized_value = value * factor
                norm_low = ref_low * factor if ref_low is not None else None
                norm_high = ref_high * factor if ref_high is not None else None
                normalized_unit = canonical_unit

    # Impossible/implausible: physiological values are non-negative.
    if normalized_value is not None and normalized_value < 0:
        reasons.append("impossible_value")

    return NormalizationResult(
        metric_code=metric_code,
        code_system="LOINC",
        mapping_confidence=1.0 if not reasons else 0.4,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        reference_low=norm_low,
        reference_high=norm_high,
        normalization_version=NORMALIZATION_VERSION,
        review_reasons=reasons,
    )
