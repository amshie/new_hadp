# Regulatory Ownership

> **Not legal or regulatory advice.** This document is an internal engineering and governance artifact. It records who owns the device-classification position and which artifacts that role maintains. The binding determinations belong to qualified counsel (Fachanwalt IT-/Medizinrecht), a data protection officer, the named Regulatory Lead, and — for the final assessment — a notified body or competent authority.

## Purpose

The intended-use boundary is this product's most important and most fragile asset. The MVP is deliberately a **data aggregation, visualization, longitudinal-change, workflow, and documentation-support** product, and deliberately **not** an autonomous medical decision-maker. Staying on the documentation-support side of the EU MDR line is what keeps the product out of Medical Device Software (MDSW) classification under Annex VIII, Rule 11.

A boundary this important cannot be owned by "the team" in general. One named person must own it, be accountable for it, and gate the changes that threaten it. This document defines that role.

## Role: Regulatory Lead

### Holder

| Field               | Value                                                                                                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Current holder**  | **UNASSIGNED**                                                                                                                                                 |
| **Assignment gate** | **Founder gate — must be assigned before pilot go-live.** This is a human decision and a hard gate; it is not satisfied by code, automation, or this document. |
| **Backup / deputy** | UNASSIGNED                                                                                                                                                     |

**Gate condition (blocking):** The Regulatory Lead role MUST be assigned by the founder, and the holder recorded in this file, **before** any of the following:

- real patient data is processed for any clinic;
- a paid or unpaid pilot goes live with a real clinic;
- marketing, sales, or onboarding copy making any clinical claim is published.

Until the holder is recorded here, those activities are blocked regardless of technical readiness.

### Mandate

The Regulatory Lead **owns the device-classification position** for the product. The Regulatory Lead does not make the final legal or regulatory assessment — that belongs to counsel, a notified body, or a competent authority — but the Regulatory Lead owns the internal determination, its rationale, and the discipline that keeps the product inside the documented boundary.

### Responsibilities

1. **Own the classification position.** Maintain the current, defensible statement of why the MVP is documentation-support and not MDSW, and keep it consistent with what the software actually does and what the claims actually say.
2. **Drive the formal determination.** Ensure a formal qualification/classification determination is obtained from qualified counsel **before** real patient data or a paid pilot — not only when the boundary later changes. "Non-device by default" is not assumed; the determination and its rationale are documented.
3. **Gate clinical-meaning features.** Every feature that touches clinical meaning (rules, highlighting, narrative drafting, reference ranges, scores, comparisons) is checked against the classification register before merge. The Regulatory Lead owns that register and that gate.
4. **Block prohibited features.** Any feature on the **Prohibited MVP behavior** list — including any biological-age, "optimal"-range, autonomous-risk, or disease-risk-score feature — is blocked until the documented decision plus clinical, privacy, and regulatory reviews are complete. The Regulatory Lead holds this block.
5. **Enforce claims discipline.** Marketing, sales, and onboarding copy are reviewed against the same boundary as the software. The product cannot advertise diagnosis, risk detection, prevention, or "optimal" health targets while the classification depends on not making those claims. Intended purpose as stated in claims often drives classification more than the code does.
6. **Own the regulatory go-live gate.** Confirm, before pilot go-live, that the classification determination is on record and that the legal/data-protection prerequisites for processing real patient data are satisfied (see artifacts below).
7. **Trigger re-assessment.** Any proposed change to the intended-use boundary requires a documented product decision plus clinical, privacy, and regulatory reviews before implementation **or marketing**. The Regulatory Lead initiates and tracks that process.

### Authority

- The Regulatory Lead may **block** any merge, release, or claim that crosses, or risks crossing, the intended-use boundary.
- The Regulatory Lead may **require** a formal review (clinical, privacy, regulatory) before a feature or claim proceeds.
- The Regulatory Lead does **not** override counsel, a data protection officer, a notified body, or a competent authority; on the final assessment, those authorities prevail.

## Artifacts owned by the Regulatory Lead

The Regulatory Lead is the accountable owner of the following artifacts. Owning an artifact means keeping it current, defensible, and consistent with the as-built product and the published claims.

| Artifact                                                | Location (planned)                                   | Status                                                            | What it must contain                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Intended-use statement**                              | `docs/regulatory/INTENDED_USE.md`                    | Pending                                                           | The product's intended purpose, the allowed/prohibited behavior lists, and the neutral-terminology rules — the basis for the classification position.                                                                                                                                                                                                                                            |
| **Classification register**                             | `docs/regulatory/CLASSIFICATION_REGISTER.md`         | Pending — initialized in Milestone 0, maintained ongoing          | One entry per clinical-meaning feature, each checked against the boundary before merge.                                                                                                                                                                                                                                                                                                          |
| **Formal qualification / classification determination** | `docs/regulatory/` (counsel determination on record) | Pending — **hard gate before real patient data or paid pilot**    | The documented qualification (device vs. non-device) and classification determination, with rationale, from qualified counsel.                                                                                                                                                                                                                                                                   |
| **Claims review record**                                | `docs/regulatory/CLAIMS_REVIEW.md`                   | Pending                                                           | Record of marketing/sales/onboarding copy reviewed against the boundary, with outcomes.                                                                                                                                                                                                                                                                                                          |
| **DPA / TOMs gate**                                     | `docs/data-governance/` (DPA/AVV + TOMs)             | Pending — **gate before processing real patient data per clinic** | Confirmation that a signed Art. 28 data processing agreement (AVV) with documented technical and organizational measures (TOMs), §203-compliant safeguards, EU/EEA residency, and a compliant sub-processor list are in place for each pilot clinic. The signed contracts and legal determinations belong to counsel and the DPO; the Regulatory Lead owns the **gate**, not the legal drafting. |

> The DPA/AVV, TOMs, §203 safeguards, and the formal classification determination are **gated, pending items**, not completed controls. The Regulatory Lead is accountable for ensuring they exist and are recorded before the corresponding activity proceeds.

## What this role does not do

- It does not replace **qualified legal counsel** (the binding contracts and legal determinations are theirs).
- It does not replace the **data protection officer** (GDPR Art. 30 records, lawful-basis determinations, and DPIA where required are theirs).
- It does not replace a **notified body or competent authority**, which makes the final qualification/classification assessment.
- It does not weaken or override the engineering intended-use boundary to accommodate a commercial request; a boundary-crossing feature is raised for the documented review process, not implemented.

## Change control

- The current holder is recorded in this file. Reassignment is a founder decision and is recorded here with the date.
- This document is updated only for durable facts about the role and its owned artifacts. Detailed procedures live in the artifacts themselves.
- When the intended-use boundary, the classification position, or the set of owned artifacts changes, this file is updated in the same change.
