# ADR-0005: Founder-approved dashboard product surfaces (VitaBahn redesign)

- Status: **Accepted** — founder decision, 2026-06-27. **Partially superseded by
  [ADR-0006](0006-dashboard-real-data-path.md)** (2026-06-27): the three added surfaces were migrated
  to the governed real-data path, where the data-quality **%**, patient **Risiko**, and
  **Normal/Grenzwertig/Auffällig** labels are **gated or replaced** (verdict-free positional Lage;
  Risiko/Datenqualität → "n. v."). See ADR-0006 §Decision and `CLASSIFICATION_REGISTER.md` rows
  46–48. This ADR records the original product decision; **ADR-0006 is the current state.**
- Decides: which contested surfaces from the Claude Design dashboard handoff
  (`HADP Dashboard.dc.html`, "VitaBahn" comp) enter the actual product in this iteration.
- Relates: ADR-0003 (HADP governance doctrine), ADR-0002 (§6 / Gate G1 — domain rollup &
  data-quality coverage intentionally absent), ADR-0004 (KPI catalog). Touches the
  [CLASSIFICATION_REGISTER](../regulatory/CLASSIFICATION_REGISTER.md) (rows added in the same PR).
- Scope of effect: **synthetic Alpha only** (`apps/web`, new `/overview`, `/patients`,
  `/patients/[id]` screens). Does not touch the existing assessment-review page
  (`/patients/[id]/assessments/[assessmentId]`), the interpretation model, or patient release.

## Context

The founder commissioned a redesigned clinician dashboard (a Claude Design HTML/CSS comp using
the "VitaBahn" design system) and asked for it to be implemented across three screens — an
**Übersicht** (overview), a **Patienten** directory, and a patient **Detail** view — adopting the
comp's visual tokens (Archivo / Hanken Grotesk / IBM Plex Mono, teal + "vital" palette, dark mode).

Pre-implementation review flagged that the comp contains four elements that collide with standing
HADP invariants:

1. A single merged **A–E "grade"** per domain (e.g. "C · Klinisch interpretierbar").
2. **Data-quality percentages** — an overview gauge (94 %), four sub-bars
   (Vollständigkeit / Aktualität / Quellenbindung / Plausibilität), per-row percentages in the
   work-list and patient directory, and an average ("Ø Datenqualität 94 %").
3. A patient-level **Risiko: Hoch / Mittel / Niedrig** indicator in the patient directory.
4. Observation statuses **Normal / Grenzwertig / Auffällig** in the evidence table and marker modal.

These were surfaced to the founder, who is the **doctrine owner**, with the regulatory exposure
made explicit (each touches clinical meaning; #2–#4 diverge from "no unified score / no %" in
[ADR-0003](0003-adopt-hadp-governance-doctrine.md) and from the strictly-positional,
verdict-free reference-position doctrine the register records for "Lage zum Referenzintervall").
The founder issued an explicit, on-record product decision. This ADR records it so the divergence
is **named, not an accidental design collision**.

## Decision

1. **Remove the merged A–E grade entirely.** No merged, rolled-up, or score-like per-domain grade
   is introduced anywhere. This **re-affirms** doctrine: where the comp collapsed Actionability into
   a single "grade" letter and dropped CIS, the Detail screen instead carries **no** grade. (The
   authoritative per-axis CIS + Actionability verdicts continue to live, as two separate fields,
   only on the existing assessment-review page, unchanged by this work.)

2. **Add the remaining three surfaces for this product iteration**, on synthetic data, as a
   deliberate founder-level product decision:

   - **Data-quality percentages** — overview gauge + four sub-bars + per-row percentages +
     average. **Static synthetic display figures ported from the comp — NOT computed from any
     observation; there is no data-quality rule or verification engine behind them, and labels
     such as "verifiziert" / "Datenqualitätsregel ausgelöst" are illustrative demo copy.** Not a
     domain verdict, not fed into any CIS / Actionability / tri-state cell.
   - **Patient-level Risiko (Hoch / Mittel / Niedrig)** — a directory indicator. Not derived from
     the interpretation model, not a tri-state Risk cell, not wired to any verdict or release.
   - **Observation status (Normal / Grenzwertig / Auffällig)** — grouping + status pill in the
     Detail evidence table and the marker modal. A presenter label, never written back to an
     observation, a domain verdict, or a report.

3. **Guardrails that stay in force.** Every new screen carries the synthetic-data labeling and the
   not-for-clinical-use framing; data is synthetic and clearly demo; nothing on these screens
   releases content to a patient or feeds the append-only interpretation/report model. The existing
   assessment-review surface (CIS + Actionability + tri-state + positional "Lage") is **unchanged**
   and remains the authoritative governance artifact.

## Two comp elements corrected, not carried over

A pre-merge adversarial review caught two things the comp shipped that go **beyond** the three
approved surfaces; both were corrected so this iteration does not silently expand scope:

- **Domain narratives neutralized.** The comp's per-domain summaries contained explicit
  treatment / follow-up / supplement **recommendations** ("…wird empfohlen", "Intervention
  erforderlich", "Substitution", "Stressmanagement priorisieren") — a **Prohibited MVP behavior**
  that this ADR never approved. The rendered `DOMAIN_DESC` strings were rewritten to be
  source-grounded and **non-prescriptive** (they describe the synthetic observations and their
  position relative to the source reference interval and their trend only). Recommendation-style
  narrative is **not** part of this iteration.
- **Marker-modal gauge zones are cosmetic, not lab bounds.** The detail marker modal's gauge paints
  good/warn/bad colour zones derived by heuristic from a single reference threshold (`scaleMax`,
  the 0.7/0.4 splits). These are **not** lab-provided bounds. Meaning is carried by the approved
  Normal/Grenzwertig/Auffällig **status pill**, not the gauge gradient; the zones are retained as a
  faithful-comp cosmetic only. Flagged here as a borderline non-lab severity surface for the
  Regulatory Lead — it must not be presented as a lab-derived "optimal/abnormal" range.

## Named divergences (the honest record)

This decision **knowingly diverges** from prior records — recorded here, not hidden:

- **ADR-0003 / "no unified score, no %":** the data-quality percentages are numeric coverage
  displays. They re-introduce, for the dashboard, the kind of coverage figure that
  [ADR-0002 §6 / Gate G1](0002-frontend-backend-wiring.md) and the presenter comment in
  `apps/web/src/lib/presenters/review.ts` deliberately omitted.
- **CLASSIFICATION_REGISTER "Reference-position UI" row** states reference position stays
  positional and verdict-free and is **"never `Hoch`/`Niedrig`/`Normal`"**. The new
  Normal / Grenzwertig / Auffällig status and the Risiko indicator contradict that on the new
  screens. The register row for the assessment-review Lage column is **not** changed; these are
  separate new surfaces, recorded as their own rows.
- The BLOCKED register row **"Autonomous risk / disease-risk score & prediction"** remains BLOCKED.
  The Risiko indicator here is a **synthetic directory label**, not an autonomous prediction or a
  derived clinical score; it is explicitly scoped to the synthetic Alpha and gated below.

## Residual human gates (NOT satisfied by this ADR)

A founder product decision is **not** the documented clinical + privacy + regulatory review that the
[CLASSIFICATION_REGISTER](../regulatory/CLASSIFICATION_REGISTER.md) requires before these surfaces
may touch real patient data. The following remain open and **block real-patient go-live**,
unchanged:

- **MDR / SaMD qualification & classification** — these surfaces increase MDSW exposure (Annex VIII,
  Rule 11); a notified body / competent authority makes the final call.
- **Clinical review** of the risk indicator and the Normal/Grenzwertig/Auffällig status semantics.
- **Privacy / DPIA** review; **forbidden-language re-point** (ADR-0003 consequence) and a copy scan
  over the new German strings.
- Regulatory-Lead sign-off of record (Founder is **acting** Regulatory Lead per
  `docs/regulatory/OWNERSHIP.md`; external assessment still pending).

Until those are complete, the three surfaces exist **only** on the synthetic Alpha demo and must not
be presented as a compliant medical-device feature.

## Consequences

- New `apps/web` screens (`/overview`, `/patients`, `/patients/[id]`) + a shared "VitaBahn" shell,
  the VitaBahn design tokens (additive to `tokens.css`; existing screens untouched), and a synthetic
  demo dataset. No backend, schema, or interpretation-model change.
- **`/overview` replaces the old `/worklist` as the authenticated home** (founder direction): `/`
  redirects authed users to `/overview` (the `me()` login gate is unchanged), `/worklist` is a
  redirect to `/overview`, and the legacy AppShell brand/nav point to `/overview`. The old worklist
  UI (`WorklistContent`) is removed; the `worklist` API/presenter helpers remain as unused library
  surface. The legacy assessment-review page (`/patients/[id]/assessments/[assessmentId]`) is
  unchanged and still reachable by URL.
- The CLASSIFICATION_REGISTER gains rows for the three surfaces (and notes the A–E grade was
  **removed**), each marked synthetic-Alpha / founder-directed with the external + clinical/privacy/
  regulatory review **pending**.
- If a later decision retires any of these surfaces, this ADR is superseded rather than edited.
