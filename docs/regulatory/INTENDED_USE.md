# Intended Use

> **Status:** Working intended-use statement for the synthetic-data-only Alpha. The MDR/MDSW qualification and classification determination is **PENDING** and owned by a human Regulatory Lead (see _Regulatory positioning_). Nothing in this document is legal or regulatory advice.

---

## Intended purpose

The Longevity Health Analytics Platform is a GDPR-first, multi-tenant **data aggregation, visualization, workflow, and documentation-support** product for longevity, functional-medicine, concierge, and preventive-care clinics in the DACH/EU market.

Its intended purpose is to let a clinic:

> Import laboratory (and, in a later phase, wearable) data, normalize it while preserving the original source representation, show longitudinal changes against the laboratory's own reference intervals, prepare a source-grounded pre-visit report draft, and require clinician approval before any patient release.

The product **supports** clinicians in preparing for appointments and documenting findings. It is **not** an autonomous medical decision-maker, and it does not make, confirm, or rule out any clinical determination on its own. Every patient-facing output passes through a qualified clinician who reviews the underlying evidence and approves release.

The primary intended benefit is operational: reducing median clinician appointment-preparation time, measured in-product against a per-clinic baseline.

---

## Intended users

The product is intended for use by authorized staff of a clinic that holds an account (tenant), under server-side, deny-by-default role-based authorization (roles: `owner`, `clinician`, `assistant`):

- **Clinic owner / tenant administrator** — manages the tenant, memberships, and clinic configuration.
- **Clinician** (qualified healthcare professional) — reviews observations and their provenance, reviews the longitudinal timeline and rule matches, edits drafts, and is the **only** role permitted to approve and release a patient-facing report.
- **Clinical assistant / care coordinator** — performs imports, manual data entry, and review-queue triage; cannot approve or release patient-facing content.
- **Patient** — receives only clinician-approved content through a secure channel.

The product is **not** intended for use by the general public as a self-service diagnostic, screening, or wellness-scoring tool, and is **not** intended for autonomous use without a qualified clinician in the loop.

---

## Clinical context

- The clinic is the data **controller**; the platform operator acts as a **processor**. A compliant Art. 28 data processing agreement (AVV) with documented TOMs, and §203 StGB-compliant professional-secrecy safeguards, are required **before** any real patient data is processed. These are **gates that are pending**, not satisfied controls.
- The product operates **after** laboratory analysis has been performed and **before / around** a clinician appointment. It consumes laboratory-provided results and reference intervals; it does not perform measurement, assay interpretation, or laboratory medicine.
- It is **not** intended for emergency, urgent-care, triage, or time-critical decision contexts, and provides no emergency or crisis guidance.
- The current Alpha processes **synthetic data only**. Every tenant, user, patient, and document carries an `is_synthetic` marker; real patient data is out of scope until the legal, privacy, and regulatory gates above are formally satisfied.

---

## Allowed behavior

The product may, within the intended purpose:

- Display measurements together with their full **provenance** (source document/connection, source record locator, observed date, original name, unit, and reference text — all immutable).
- Display **laboratory-provided reference intervals** exactly as supplied by the source.
- Distinguish **measured**, **normalized**, and **derived** values, and always expose the original value and the deterministic, versioned conversion method behind any normalized value.
- Calculate **deterministic** deltas, percentages, aggregates, and data-freshness metrics from versioned inputs, using exact decimal arithmetic.
- Highlight values using **explicitly configured clinic rules** (above/below the source reference interval, absolute or percentage change since a comparable observation, missing expected metric, stale data, configured threshold), labeled as `rule match` / `attention item`, each evaluation recording rule ID + version, input observation IDs, thresholds, units, timestamp, and reason.
- Identify and surface **missing, stale, duplicate, or conflicting** data, and route low-confidence mappings, unit conflicts, impossible values, and date/duplicate ambiguity into a human **review queue**.
- Draft a **factual, source-grounded summary** in which every generated statement references one or more underlying observation or rule-evaluation IDs, with evidence viewable inline at approval time.
- Require a **qualified clinician's attributable approval** before any patient-facing release, with editing after approval creating a new version that invalidates the prior approval.

## Prohibited behavior

The product must not, and is not intended to:

- Diagnose, screen for, or rule out a disease or condition.
- Recommend medication, dosage, treatment, therapy, or supplements.
- Produce autonomous clinical **risk predictions** or **disease-risk scores**.
- Produce a **biological-age** score or any merged health/longevity score.
- Replace laboratory reference intervals with undocumented **"optimal"** ranges.
- Claim to **detect, prevent, or cure** disease.
- Present an **inferred** value as if it were a **measured** value.
- **Send an AI-generated report directly to a patient**, or release any unapproved content.
- Provide **emergency triage** or crisis guidance.
- **Hide uncertainty, source conflicts, or missing information** — review status and uncertainty are shown explicitly.
- Compare measurements across incompatible methods, specimen types, fasting states, or units unless that compatibility is explicitly modeled.

**Vocabulary:** user-facing copy uses neutral terms — `observation`, `change`, `source reference interval`, `rule match`, `draft`. It avoids `diagnosis`, `treatment plan`, `disease detected`, `risk score`, `biological age`, and "optimal" range. Any change to this list is treated as a boundary change requiring the review process below.

---

## AI positioning

AI is a **constrained drafting component**, never the source of numerical truth. It may convert already-verified structured facts into readable prose, group related observations, and describe the direction and timing of deterministic changes in neutral wording. It may not perform calculations that application code performs, invent measurements/ranges/causes/diagnoses/recommendations, use any fact not present in the supplied evidence payload, or publish/approve a report. A deterministic local provider exists for development and tests; any production AI provider is a **gated vendor decision** subject to EU data-residency and no-training-on-customer-data requirements, and is not selected.

---

## Claims discipline

Marketing, sales, and onboarding copy are reviewed against **the same intended-use boundary as the software** — because, under EU MDR, the stated intended purpose (claims) can drive classification more strongly than the implementation does.

- The product **may not advertise or imply** diagnosis, disease detection, screening, risk prediction, prevention, biological-age, or "optimal" health targets while the MVP classification position depends on not making those claims.
- Any commercial, website, demo, or onboarding statement that crosses the prohibited-behavior list is blocked until the documented review process is complete, regardless of commercial appeal.
- A change to the intended purpose — in **code or in claims** — requires a documented product decision plus clinical, privacy, and **regulatory classification** review before implementation **or** marketing.

---

## Regulatory positioning (MDR / MDSW)

The commercial pull of "longevity / healthspan" is toward biological-age, optimal-range, and risk-score features. Such features are likely to qualify the product as **Medical Device Software (MDSW)** under **EU MDR (Annex VIII, Rule 11)**, which would trigger a notified body, clinical evaluation, an ISO 13485 quality system, and post-market surveillance. The MVP **deliberately stays on the documentation-support side of that line** by excluding every prohibited behavior above.

- The formal **qualification and classification determination is PENDING**. It must be on record **before** any real patient data or paid pilot — "non-device" is **not** assumed by default.
- A named, human **Regulatory Lead** owns the determination and its rationale (to be recorded under `docs/regulatory/`). A repository runbook or skill may assist with an MDR/MDSW analysis pass over this statement, but the human Regulatory Lead owns the position.
- A **notified body or competent authority** makes the final assessment.
- Every feature touching clinical meaning (rules, highlighting, narrative, ranges, scores, comparisons) is checked against the classification register before merge.

> This statement is an engineering and product-governance artifact. It is **not** legal or regulatory advice, and it does not constitute a regulatory determination.
