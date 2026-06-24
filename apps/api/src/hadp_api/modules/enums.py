"""Closed vocabularies used across modules.

Enum values are stored as their lowercase string `value` via a CHECK constraint
(`native_enum=False`), so the database enforces the closed set without fragile native
PostgreSQL enum types, and JSON payloads stay readable.
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[Enum], *, length: int = 40) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
        length=length,
    )


class Role(str, Enum):
    """Tenant staff roles. Patients are not staff and have no Membership."""

    OWNER = "owner"  # clinic owner / tenant administrator
    CLINICIAN = "clinician"
    ASSISTANT = "assistant"  # clinical assistant / care coordinator


class ValueType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    CODED = "coded"


class ReviewStatus(str, Enum):
    PENDING = "pending"  # low confidence / conflict — needs human resolution
    PUBLISHED = "published"  # human-resolved and visible
    REJECTED = "rejected"


class ImportStatus(str, Enum):
    RECEIVED = "received"
    STORED = "stored"
    EXTRACTED = "extracted"
    MAPPED = "mapped"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ReportStatus(str, Enum):
    DRAFT_GENERATED = "draft_generated"
    DRAFT_EDITED = "draft_edited"
    APPROVED = "approved"
    RELEASED = "released"
    REJECTED = "rejected"


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


# --- HADP interpretation doctrine (ADR-0003): six axes, two engines, tri-state ---
#
# The domain axis is the canonical unit: ONE CIS + ONE Actionability per axis per run, with three
# verdict-free tri-state cells per axis (6 verdicts + 18 cells per run). CIS and Actionability are
# two DISJOINT closed enums — never merged, never derived from each other or from the cells. The
# engine validates and records; it never derives (ADR-0003).


class DomainAxis(str, Enum):
    """The six founder-approved longevity body-system axes (closed; ADR-0003)."""

    METABOLIC = "metabolic"
    IMMUNE_INFLAMMATION = "immune_inflammation"
    CARDIOVASCULAR = "cardiovascular"
    NEUROCOGNITIVE = "neurocognitive"
    MUSCULOSKELETAL = "musculoskeletal"
    REGENERATIVE_CAPACITY = "regenerative_capacity"


class TriStateAxis(str, Enum):
    """Verdict-free supporting-evidence axes (three cells per domain verdict)."""

    BIOLOGICAL = "biological"
    RISK = "risk"
    FUNCTIONAL = "functional"


class CisStatus(str, Enum):
    """Engine 1 — Credible Improvement Status (closed, one per domain axis)."""

    CIS_0_INSUFFICIENT_EVIDENCE = "CIS_0_INSUFFICIENT_EVIDENCE"
    CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY = "CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY"
    CIS_2_NOT_YET_CREDIBLE = "CIS_2_NOT_YET_CREDIBLE"
    CIS_3_RISK_DOMINANT_OR_CONFLICTING = "CIS_3_RISK_DOMINANT_OR_CONFLICTING"
    CIS_4_CREDIBLE_IMPROVEMENT = "CIS_4_CREDIBLE_IMPROVEMENT"
    CIS_5_STABLE_NO_MATERIAL_CHANGE = "CIS_5_STABLE_NO_MATERIAL_CHANGE"


class ActionabilityClass(str, Enum):
    """Engine 2 — Actionability class (closed, DISJOINT from CIS, one per domain axis)."""

    A_DISCOVERY = "A_DISCOVERY"
    B_SUPPORTIVE = "B_SUPPORTIVE"
    C_CLINICALLY_INTERPRETABLE = "C_CLINICALLY_INTERPRETABLE"
    D_ACTIONABLE_UNDER_GOVERNANCE = "D_ACTIONABLE_UNDER_GOVERNANCE"
    E_DO_NOT_ACT = "E_DO_NOT_ACT"


class AdequacyStatus(str, Enum):
    """Adequacy is a closed enum, NEVER a number (a numeric confidence is a forbidden score)."""

    ADEQUATE = "adequate"
    INADEQUATE = "inadequate"
    NOT_ASSESSED = "not_assessed"


class InterpretationReviewStatus(str, Enum):
    """Per-domain-verdict review projection (distinct from observation ReviewStatus)."""

    DRAFT = "draft"
    CLINICIAN_REVIEWED = "clinician_reviewed"


class BiologicalFunctionalState(str, Enum):
    """Cell-state vocabulary for the biological and functional axes."""

    IMPROVED = "IMPROVED"
    STABLE = "STABLE"
    WORSENED = "WORSENED"
    MIXED = "MIXED"
    INDETERMINATE = "INDETERMINATE"


class RiskState(str, Enum):
    """Cell-state vocabulary for the risk axis (disjoint: MIXED is not a risk value)."""

    REDUCED = "REDUCED"
    WORSENED = "WORSENED"
    DOMINANT = "DOMINANT"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTING = "CONFLICTING"
    INDETERMINATE = "INDETERMINATE"


# Union of all legal cell-state values (the DB CHECK on tri_state_cells.state). Axis-correctness
# (risk-only vs biological/functional values) is enforced at the service layer, not by this set.
CELL_STATES: tuple[str, ...] = tuple(
    dict.fromkeys([s.value for s in BiologicalFunctionalState] + [s.value for s in RiskState])
)


def cell_states_for_axis(axis: TriStateAxis) -> frozenset[str]:
    """The legal cell-state vocabulary for a tri-state axis (risk values are disjoint)."""
    if axis is TriStateAxis.RISK:
        return frozenset(s.value for s in RiskState)
    return frozenset(s.value for s in BiologicalFunctionalState)


# --- KPI catalog (ADR-0004): closed vocabularies for the global KPI terminology layer ---


class KpiMeasurementClass(str, Enum):
    LABORATORY = "laboratory"
    VITAL_SIGN = "vital_sign"
    ANTHROPOMETRIC = "anthropometric"
    BODY_COMPOSITION = "body_composition"
    FUNCTIONAL_TEST = "functional_test"
    WEARABLE = "wearable"
    IMAGING = "imaging"
    DERIVED = "derived"
    OMICS = "omics"


class KpiValueKind(str, Enum):
    QUANTITY = "quantity"
    COUNT = "count"
    DURATION = "duration"
    RATIO = "ratio"
    SCORE = "score"
    PANEL = "panel"


class KpiCatalogTier(str, Enum):
    CORE = "core"
    EXTENDED = "extended"
    SPECIALIST = "specialist"
    RESEARCH = "research"


class KpiComparisonPolicy(str, Enum):
    METHOD_AWARE = "method_aware"
    SAME_METHOD_REQUIRED = "same_method_required"
    SAME_PROTOCOL_REQUIRED = "same_protocol_required"
    SAME_DEVICE_PROTOCOL_REQUIRED = "same_device_protocol_required"
    SAME_DEVICE_ALGORITHM_REQUIRED = "same_device_algorithm_required"
    SAME_INSTRUMENT_VERSION_REQUIRED = "same_instrument_version_required"
    SAME_IMAGING_PROTOCOL_REQUIRED = "same_imaging_protocol_required"
    SAME_FORMULA_VERSION_REQUIRED = "same_formula_version_required"
    SAME_OMICS_PLATFORM_REQUIRED = "same_omics_platform_required"
    NOT_LONGITUDINAL = "not_longitudinal"


class KpiStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


class KpiExternalCodeStatus(str, Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    REJECTED = "rejected"


class KpiReleaseStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


# --- Observation comparability (ADR-0004 Slice 3, §8/§9 non-merge) ---
#
# A verdict-free marker on a timeline point: was a longitudinal delta against the prior comparable
# observation legitimate? It is grouping/validation, NOT a clinical verdict — disjoint from CIS and
# Actionability, never a score. When NOT comparable, the numeric delta is withheld (fail-closed):
# an incomparable delta is a fabricated change.


class ComparabilityState(str, Enum):
    COMPARABLE = "comparable"
    NOT_COMPARABLE = "not_comparable"


class ComparabilityReason(str, Enum):
    CONTEXT_DIFFERS = "context_differs"  # required context present on both but unequal
    CONTEXT_MISSING = "context_missing"  # required context absent on either side (never inferred)
    NOT_LONGITUDINAL = "not_longitudinal"  # the KPI is not longitudinally comparable at all
