# Intended Use

> **Status:** Working intended-use statement for the synthetic-data-only Alpha. **Product model:** the
> HADP **governance** model adopted in [ADR-0003](../adr/0003-adopt-hadp-governance-doctrine.md) (founder
> decision, 2026-06-22), which **superseded** the original lab-analytics intended use. The MDR/MDSW
> qualification and classification determination for this governance model is **PENDING** and is an
> explicit open human gate (ADR-0003); it is owned by a human Regulatory Lead (currently **UNASSIGNED**,
> see [OWNERSHIP.md](OWNERSHIP.md)). Nothing in this document is legal or regulatory advice.

---

## Intended purpose

HADP is a GDPR-first, multi-tenant, **physician-governed, audit-first decision-support** workflow for
longevity, functional-medicine, concierge, and preventive-care clinics in the DACH/EU market.

Its canonical artifact is a **per-patient interpretation run** that a clinician authors and a medical
director gates. The product:

> Aggregates laboratory (and, in a later phase, wearable) data while preserving the original source
> representation; normalizes and displays it against the laboratory's own reference intervals with full
> provenance; lets a **clinician author** a per-axis interpretation (governance verdicts) over a fixed set
> of body-system domains, recorded append-only with its supporting evidence; and requires a medical
> director's review/lock before any patient-facing release.

The product **supports and documents** clinician judgement in a governed, auditable way. It is **not** an
autonomous medical decision-maker: the system **validates and records; it never derives** a verdict, a
score, or any clinical conclusion on its own. Every per-axis verdict is **authored by a qualified
clinician**, and every patient-facing output passes through a medical-director gate that reviews the
underlying evidence before release.

The primary intended benefit is operational and governance-related: a structured, attributable,
audit-complete record of clinician interpretation, and reduced median appointment-preparation time
measured in-product against a per-clinic baseline.

---

## Intended users

For authorized staff of a clinic that holds an account (tenant), under server-side, deny-by-default
role-based authorization:

- **Clinic owner / tenant administrator** — manages the tenant, memberships, and clinic configuration.
- **Clinician** (qualified healthcare professional) — reviews observations and provenance, the
  longitudinal timeline, and the supporting evidence; **authors** the per-axis interpretation (CIS and
  Actionability verdicts and the verdict-free tri-state cells); edits report drafts.
- **Medical director** (governance gate) — reviews authored interpretations and reports against their
  evidence and is the gate that **locks/releases** patient-facing content. Only released content reaches a
  patient.
- **Clinical assistant / care coordinator** — performs imports, manual entry, and review-queue triage;
  cannot author verdicts or release patient-facing content.
- **Patient** — receives only released (medical-director-gated) content through a secure channel.

The product is **not** intended for use by the general public as a self-service diagnostic, screening, or
wellness-scoring tool, and is **not** intended for autonomous use without a qualified clinician authoring
and a medical director gating.

---

## Clinical context

- The clinic is the data **controller**; the platform operator acts as a **processor**. A compliant
  Art. 28 data processing agreement (AVV) with documented TOMs, and §203 StGB-compliant
  professional-secrecy safeguards, are required **before** any real patient data is processed. These are
  **gates that are pending**, not satisfied controls.
- The product operates **after** laboratory analysis and **before / around** a clinician appointment. It
  consumes laboratory-provided results and reference intervals; it does not perform measurement, assay
  interpretation, or laboratory medicine.
- It is **not** intended for emergency, urgent-care, triage, or time-critical contexts, and provides no
  emergency or crisis guidance.
- The current Alpha processes **synthetic data only**. Every tenant, user, patient, and document carries
  an `is_synthetic` marker; real patient data is out of scope until the legal, privacy, and regulatory
  gates above are formally satisfied.

---

## The interpretation model (governance core)

Per patient interpretation run (ADR-0003 / ADR-0004), authored by a clinician:

- exactly **six domain axes**: `metabolic`, `immune_inflammation`, `cardiovascular`, `neurocognitive`,
  `musculoskeletal`, `regenerative_capacity`;
- per axis, **one CIS** (Credible Improvement Status) verdict **and one Actionability** verdict — two
  **disjoint closed enumerations**, never merged, never auto-derived from one another or from the cells;
- per axis, **three verdict-free tri-state cells** (`biological` / `risk` / `functional`) as supporting
  evidence only (no CIS/Actionability on a cell);
- runs are **append-only** — a correction creates a new run; nothing is overwritten.

CIS, Actionability, and the tri-state axes (including `Risk`) are **closed governance vocabularies**, not
free-text clinical claims. They record *the clinician's* structured judgement with attribution and
provenance. The engine **validates** an authored run against the closed vocabularies and the structural
rules and **records** it; **no function maps markers/cells → CIS, or CIS → Actionability, or anything →
a number.** Adequacy is a closed enum, never a numeric confidence.

A supporting KPI/observation layer (ADR-0004) provides a global, read-only KPI catalog, measurement-context
provenance, deterministic and version-pinned **comparability** (fail-closed: an incomparable longitudinal
delta is withheld, never fabricated), and a versioned **derived-value** formula registry that performs only
**deterministic arithmetic** from validated source observations, labelled `derived` (never presented as
measured) with immutable input lineage. None of this computes a clinical verdict or a score.

---

## Allowed behavior

The product may, within the intended purpose:

- Display measurements with full **provenance** (source, locator, observed date, original name, unit,
  reference text — immutable), and the laboratory-provided **reference intervals** exactly as supplied.
- Distinguish **measured**, **normalized**, and **derived** values, always exposing the original value and
  the deterministic, versioned conversion/derivation method, with the derived value's formula id + version
  and immutable input observation IDs.
- Calculate **deterministic** deltas, percentages, aggregates, derived KPIs, and data-freshness from
  versioned inputs using exact decimal arithmetic; **withhold** a longitudinal comparison when measurement
  context differs or is undocumented (fail-closed), rather than fabricate a change.
- Let a **clinician author** a per-axis interpretation (CIS + Actionability verdicts and verdict-free
  tri-state cells) over the six domains, recorded append-only with its supporting observation/evidence IDs.
- Surface **missing, stale, duplicate, or conflicting** data and route low-confidence mappings, unit
  conflicts, impossible values, and ambiguity into a human **review queue**.
- Draft a **factual, source-grounded summary** in which every generated statement references underlying
  evidence, viewable inline at review time.
- Require a **medical director's attributable lock/release** before any patient-facing release, with
  editing after approval creating a new version that invalidates the prior approval.

## Prohibited behavior

The product must not, and is not intended to:

- **Autonomously derive** any verdict, score, or clinical conclusion — the engine validates and records
  authored judgement; it never computes CIS, Actionability, or a tri-state state from data.
- Produce a **unified / merged score**, a percentage health/longevity index, or a **biological-age** score.
- Diagnose, screen for, or rule out a disease; recommend medication, dosage, treatment, therapy, or
  supplements; or claim to **detect, prevent, or cure** disease.
- Produce an **autonomous risk prediction** or disease-risk score (the `risk` tri-state axis and the
  Actionability verdict are **clinician-authored governance entries**, not machine predictions).
- Replace laboratory reference intervals with undocumented **"optimal"** ranges.
- Present an **inferred or derived** value as if it were a **measured** value.
- **Release any unapproved content**, or send a machine-generated report directly to a patient.
- Provide **emergency triage** or crisis guidance.
- **Hide uncertainty, source conflicts, or missing information** — review status, adequacy, and
  comparability are shown explicitly; missing data reads as `not_observed`, never as normal/stable.
- Compare measurements across incompatible methods, specimen types, fasting states, devices, instrument or
  formula versions, or units unless that compatibility is explicitly modeled.

**Vocabulary (HADP governance bank, per ADR-0003).** User-facing copy may use the sanctioned governance
terms `CIS`, `Actionability`, and `Risk` (as a tri-state axis), plus neutral terms (`observation`,
`change`, `source reference interval`, `derived`, `not comparable`, `draft`). It forbids `diagnosis`,
`treatment`, `biological age`, any unified/health **score**, and `"optimal"` range. Any change to this list
is a boundary change requiring the review process below.

---

## AI positioning

AI is a **constrained drafting component**, never the source of numerical truth and never the author of a
verdict. It may convert already-verified structured facts into readable prose, group related observations,
and describe the direction/timing of deterministic changes in neutral wording. It may not perform
calculations application code performs, invent measurements/ranges/causes/diagnoses/recommendations, use any
fact absent from the supplied evidence payload, author a CIS/Actionability verdict, or publish/approve a
report. A deterministic local provider exists for development and tests; any production AI provider is a
**gated vendor decision** subject to EU data-residency and no-training-on-customer-data requirements, and is
not selected.

---

## Claims discipline

Marketing, sales, and onboarding copy are reviewed against **the same intended-use boundary as the
software** — under EU MDR, the stated intended purpose (claims) can drive classification more strongly than
the implementation. In particular:

- The product **may not advertise or imply** autonomous diagnosis, disease detection, screening, risk
  prediction, prevention, biological-age, or "optimal" health targets, nor present the governance verdicts
  as machine-generated clinical conclusions, while the classification position is pending.
- Public-facing copy (including the README, now that the repository is shared) is a **claim**. It is held
  conservative and routed through the documented review process; the claims-review record
  (`CLAIMS_REVIEW.md`) and Regulatory-Lead sign-off are pending.
- A change to the intended purpose — in **code or in claims** — requires a documented product decision plus
  clinical, privacy, and **regulatory classification** review before implementation **or** marketing.

---

## Regulatory positioning (MDR / MDSW) — open determination

ADR-0003 records this as the **first deliberate divergence of intended use** and states that a regulatory
re-confirmation of the HADP "governance tool, not a medical device" position **remains a human gate before
real data.** That gate is **open.**

- **The open question** a Regulatory Lead, counsel, and ultimately a notified body / competent authority
  must resolve: whether physician-authored, **validate-never-derive** per-axis CIS + Actionability
  governance verdicts (with no autonomous derivation, no unified score, no biological-age, and a
  medical-director release gate) sit on the **documentation/decision-support** side of EU MDR Annex VIII,
  Rule 11, or whether they qualify the product as **Medical Device Software (MDSW)**. This statement
  **frames** the question; it does **not** assert the answer.
- The product is **designed** to stay on the documentation/decision-support side — the engine never
  derives, there is no unified score or biological-age, and a clinician authors while a medical director
  gates — but "non-device" is **not assumed by default**.
- The formal **qualification and classification determination is PENDING** and must be on record **before**
  any real patient data or paid pilot.
- A named, human **Regulatory Lead** (currently UNASSIGNED) owns the determination and its rationale; a
  **notified body or competent authority** makes the final assessment.
- Every feature touching clinical meaning (interpretation verdicts, KPI catalog, comparability, derived
  values, rules, narrative) is checked against the classification register before merge.

> This statement is an engineering and product-governance artifact. It is **not** legal or regulatory
> advice, and it does not constitute a regulatory determination.
