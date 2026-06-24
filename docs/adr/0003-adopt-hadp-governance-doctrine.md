# ADR-0003: Adopt the HADP governance doctrine (supersede the lab-analytics intended use)

- Status: **Accepted** — founder decision, 2026-06-22.
- Supersedes: the lab-analytics product doctrine in [CLAUDE.md](../../CLAUDE.md) (intended use,
  prohibited-feature list, forbidden-language policy) **for the product model**. Relates: ADR-0001
  (stack — unchanged), ADR-0002 (frontend↔backend wiring — unchanged).
- Reference doctrine: the HADP governance build (`~/Desktop/test2/docs/DOCTRINE.md`) and its data
  model (`~/Desktop/new_files/hadp-alpha/docs/SCHEMA.md`).

## Context

The repo was scaffolded as a **lab-analytics, documentation-support** product (CLAUDE.md): import
labs → normalize observations → deterministic deltas/rules → clinician-approved report. Its
intended-use boundary explicitly **excluded** interpretive constructs (biological-age / risk
scores, autonomous risk prediction).

The founder has decided that this app is the **HADP governance product**: a physician-governed,
audit-first decision-**support** workflow whose canonical artifact is a per-axis interpretation —
**not** the lab-analytics documentation tool. The earlier lab-panel "domains + rule counts" model
(the G1 work) is therefore **not** the product.

## Decision

1. **NEW_HADP adopts the HADP governance doctrine.** The lab-analytics intended-use, prohibited
   list, and forbidden-language bank in CLAUDE.md are **superseded** by the HADP doctrine. CLAUDE.md
   carries a banner pointing here.
2. **The interpretation model becomes the core.** Per patient interpretation run:
   - exactly **six domain axes** (founder-approved): `metabolic`, `immune_inflammation`,
     `cardiovascular`, `neurocognitive`, `musculoskeletal`, `regenerative_capacity`;
   - per axis, **one CIS + one Actionability** verdict — two **disjoint closed enums**, never merged,
     never auto-derived from each other or from the cells;
   - per axis, **three verdict-free tri-state cells** (`biological` / `risk` / `functional`) as
     supporting evidence (no CIS/Actionability on a cell);
   - i.e. **6 verdicts + 18 cells per run**; runs are **append-only**, corrections create a new run.
3. **The engine validates and records; it never derives** (HADP ADR-0003). No function maps
   cells/markers → CIS or CIS → Actionability. Adequacy is a **closed enum, never a number**.
4. **Clinician-in-the-loop, medical-director gate.** Drafts are clinician-authored; only a medical
   director locks/releases; patients see only released content.

## Preserved protective invariants (NOT dropped by "forget the old doctrine")

These existed in the lab doctrine and are **retained** because the HADP doctrine requires them too:

- **Synthetic data only**, mechanically enforced; **tenant isolation via RLS**; **append-only audit
  with provenance**; **no unified score / no %**; **closed vocabularies**; and the **human gates**
  for real patient data, MDR/SaMD qualification, and GDPR/DPIA — all remain in force.

"Forget the NEW_HADP doctrine" means **swap the product model**, not abandon safety, privacy, or the
regulatory gates.

## Consequences / migration

- New module `modules/interpretation` (`InterpretationRun`, `DomainAxisInterpretation`,
  `TriStateCell`) + closed enums in `modules/enums.py` + a pure validate-never-derive `run_shape`
  port. Alembic migration `0003` creates the tables with RLS + append-only triggers.
- The lab-analytics surfaces (observations/import/reports) remain for now; subsequent slices build
  the case/run review UI on the interpretation model and re-point the worklist.
- The **forbidden-language policy** must be re-pointed from the lab bank to the HADP bank (which
  permits `Risk` / `CIS` / `Actionability` as sanctioned governance vocabulary and forbids
  diagnosis/treatment/unified-score/biological-age) — done in a dedicated follow-up slice.
- This is the **first deliberate divergence** of intended use; a regulatory re-confirmation of the
  HADP "governance tool, not a medical device" position remains a human gate before real data.

## Out of scope (this ADR)

The forbidden-language re-point, the case/run UI, the interpretation write/review services, and the
report lock/release on the new model — each its own slice.
