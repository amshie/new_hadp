"""Closed vocabularies used across modules.

Enum values are stored as their lowercase string `value` (`native_enum=False`), which avoids
fragile native PostgreSQL enum types and keeps JSON payloads readable. `native_enum=False` does
NOT create a CHECK on its own; the closed set is DB-enforced by explicit CHECK constraints added
in migrations (0009 memberships.role, 0013 staff_invitations.role, 0014 all remaining enum
columns) and covered by `tests/test_enum_check_constraints.py`. See docs/notes/0006.
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
    # Governance gate (INTENDED_USE/ADR-0003): reviews authored content against its
    # evidence and is the ONLY role that releases patient-facing content.
    MEDICAL_DIRECTOR = "medical_director"


class ValueType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    CODED = "coded"


class InvitationStatus(str, Enum):
    """Lifecycle of a single-use patient-invitation credential (docs/notes/0010)."""

    PENDING = "pending"
    REDEEMED = "redeemed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ReviewDecision(str, Enum):
    """Closed decision vocabulary for resolving a review item (API layer).

    A human either PUBLISHes the observation (it becomes clinical-workflow-visible)
    or REJECTs it (it never publishes). There is no third outcome.
    """

    PUBLISH = "publish"
    REJECT = "reject"


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


class ReportRejectionReason(str, Enum):
    """Why a report version was rejected — a CLOSED vocabulary.

    Never free text: the reason is stored on the version and written to the audit trail, and
    neither may carry patient data. Whoever reworks the report reads it to know what to change.

    PROPOSED values (engineering proposal, 2026-10-12) awaiting the medical director's
    confirmation — see docs/regulatory/CLASSIFICATION_REGISTER.md. Changing the set is a
    migration (the DB CHECK lists the values).
    """

    # A statement is not, or not correctly, backed by its evidence.
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    # The wording has to change.
    WORDING = "wording"
    # Data is missing, or values are still waiting in the review queue.
    DATA_INCOMPLETE = "data_incomplete"
    # The underlying data changed after the draft was written.
    DATA_CHANGED = "data_changed"
    # None of the above; the reason is communicated outside the system.
    OTHER = "other"


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class ConsentEventType(str, Enum):
    """An append-only consent state change. Withdrawal is a NEW event, never an overwrite."""

    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class DuplicateMatchBasis(str, Enum):
    """How an existing patient matched a pre-create duplicate probe — a CLOSED vocabulary.

    Response-only (never stored in a column, so no CHECK-constraint migration). The matching
    heuristic is deliberately conservative and documented (docs/notes/0011): exact matches on
    normalized fields only, never fuzzy similarity — an over-eager matcher would train staff
    to click through the warning.
    """

    EXTERNAL_REF = "external_ref"  # same clinic-assigned reference (strong)
    NAME_DOB = "name_dob"  # same normalized name AND same date of birth (strong)
    NAME = "name"  # same normalized name only (weak — surfaced, never blocking)


class ConsentPurpose(str, Enum):
    """Purpose a consent event scopes — a CLOSED vocabulary.

    These are SYNTHETIC-ALPHA PLACEHOLDER values. The real, lawful purpose taxonomy and the
    per-purpose Art. 9(2) lawful basis are a DPO/counsel deliverable (PENDING), NOT an engineering
    default — see docs/regulatory (Regulatory-Lead UNASSIGNED). Only `report_release` is enforced as
    a gate today (on patient-facing report release); the others name transitions for completeness.
    """

    REPORT_RELEASE = "report_release"  # gates patient-facing release of a report (enforced)
    ANALYTICS = "analytics"
    DATA_SOURCE_CONNECT = "data_source_connect"


class DeletionRequestStatus(str, Enum):
    """Lifecycle of a patient-erasure request — a CLOSED vocabulary (docs/notes/0012).

    A two-person gate: an owner REQUESTS (`pending`), a medical director DECIDES
    (`approved` / `rejected`), and an approved request is later EXECUTED (`executed`,
    the irreversible gated erasure — PR B). The requester may `cancelled` a still-pending
    request. `pending` and `approved` are the two NON-TERMINAL states (at most one per
    patient); `rejected` / `cancelled` / `executed` are terminal.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXECUTED = "executed"


class DeletionReasonCategory(str, Enum):
    """Why an erasure is requested — a CLOSED vocabulary, never free text.

    SYNTHETIC-ALPHA PLACEHOLDER values (like ConsentPurpose): the real, counsel-authored
    erasure-basis taxonomy — and the balance against clinical retention duties (e.g.
    § 630f BGB / Art. 17(3) exemptions) — is a pending DPO/counsel deliverable. A closed
    enum (not free text) so the request itself can never carry PII.
    """

    PATIENT_REQUEST = "patient_request"  # data-subject Art. 17 erasure request
    WITHDRAWN_CONSENT = "withdrawn_consent"  # processing basis withdrawn
    DATA_MINIMIZATION = "data_minimization"  # no longer necessary for the purpose


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
