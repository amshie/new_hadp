# Interpretation model — a clinical and biological review

**Status:** discussion paper, 2026-10-13. Not a decision and not clinical or regulatory advice.
**Decides:** the medical director, for every clinical definition below; the Regulatory Lead
(founder acting) for every item marked _register_; the founder for changes to ADR-0003.
**Reads with:** [ADR-0003](../adr/0003-adopt-hadp-governance-doctrine.md),
[ADR-0004](../adr/0004-kpi-catalog.md),
[INTENDED_USE](../regulatory/INTENDED_USE.md),
[CLASSIFICATION_REGISTER](../regulatory/CLASSIFICATION_REGISTER.md).

This paper reads the interpretation model (CIS, Actionability and the three tri-state axes) as a
clinician and a biologist would: what it gets right, where it is open, and what would make it
verifiable. The clinical readings of each value are the author's reading of the names, offered as
hypotheses for the medical director to confirm or correct. They are not definitions.

## 1. The model as built

Per patient, a clinician records an **interpretation run** (`apps/api/src/hadp_api/modules/interpretation/`):

- **Six domain axes**, always all six: metabolic, immune/inflammation, cardiovascular,
  neurocognitive, musculoskeletal, regenerative capacity.
- **Per domain:** one **CIS** value, one **Actionability** class, a follow-up adequacy
  (adequate / inadequate / not assessed) and an optional rationale (up to 2000 characters).
- **Per domain, three tri-state cells** — biological, risk, functional — each with a state, an
  endpoint adequacy, its evidence (published observations of this patient) and an optional
  rationale. A cell whose state is determined needs at least one piece of evidence.
- **Per run:** a required reason (up to 200 characters). Runs are append-only; a correction is a
  new run that supersedes the previous one.

The closed vocabularies (`apps/api/src/hadp_api/modules/enums.py`):

| Field                       | Values                                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CIS                         | 0 insufficient evidence · 1 apparent biological improvement only · 2 not yet credible · 3 risk-dominant or conflicting · 4 credible improvement · 5 stable, no material change |
| Actionability               | A discovery · B supportive · C clinically interpretable · D actionable under governance · E do not act                                                                         |
| Biological, functional cell | improved · stable · worsened · mixed · indeterminate                                                                                                                           |
| Risk cell                   | reduced · worsened · dominant · unresolved · conflicting · indeterminate                                                                                                       |

The rule that holds it together (ADR-0003): **the engine validates and records; it never
derives.** No function maps cells or markers to CIS, or CIS to Actionability. The clinician
chooses; the system checks the vocabulary and the evidence binding and keeps the record.

## 2. Strengths

1. **"Has it improved?" is kept apart from "what do we do?"** CIS and Actionability are disjoint
   and neither is derived from the other. Clinical practice routinely blurs three questions —
   did the marker change, did the intervention work, should we act — and this model keeps them
   separate by construction.
2. **The surrogate-endpoint trap has a name.** The split into biological, risk and functional
   cells, and the value "CIS-1: apparent biological improvement only", address one of medicine's
   costliest errors: a marker that improves while the outcome does not, or worsens. Raising HDL
   with torcetrapib increased mortality (ILLUMINATE, 2007); suppressing ventricular ectopy with
   encainide and flecainide increased deaths (CAST, 1989). A model that reserves a place for
   "the numbers moved, the patient may not have" is clinically literate.
3. **"Credible" asks for more than a change.** Requiring credibility, and evidence for every
   determined cell, pushes against reading within-person biological variation, analytical noise
   or regression to the mean as a result.
4. **Not knowing is a legitimate answer.** Indeterminate, not assessed and insufficient evidence
   are first-class values. Commercial longevity care is under constant pressure to always give an
   answer; a model that can say "we do not know" is scientifically honest.
5. **No unified score.** The six domains do not add up biologically. Any composite "longevity
   score" would hide uncertainty behind false precision — and it is also what keeps the product
   on the documentation side of the medical-device boundary.
6. **The human authors, the system records.** Append-only runs with a required reason give an
   auditable account of who judged what, when, and on which evidence.
7. **Every domain, every time.** Requiring all six domains in every run counters the pull towards
   the marker the patient happened to ask about.
8. **Comparisons are already fail-closed.** A change against the previous value is withheld when
   the measurement context differs or is unknown (ADR-0004, slice 3). That is part of credibility
   the platform already enforces.

## 3. Weaknesses and open questions

Each item says what is open, why it matters, and what the code holds today.

### 3.1 "Credible" has no operational definition _(most important)_

What makes an improvement credible: how many measurements, over what period, a change larger than
the marker's reference change value, confirmation on another axis? Without a written answer, two
clinicians can give the same data different CIS values, and the model cannot be shown to measure
anything: without agreement between raters there is no reliability, and without reliability
there is no validity. The code holds the vocabulary only; the definitions live nowhere.

### 3.2 The period a verdict covers is implicit

"Improved" against which baseline, over which window? Improvement over three months and over
three years are different findings. The cited evidence carries its observation dates, but the run
does not state the baseline and comparison window its verdicts cover.

### 3.3 What happened between runs is not recorded

The platform records measurements and verdicts, not what the patient did between runs: a new
medication, a diet, an illness, weight change, a training block. "Credible improvement" without
the exposure has no causal reading. Recommending treatment is rightly out of scope (CLAUDE.md,
ADR-0003); _recording what was done, as a fact,_ is a different thing — but it adds health data
and moves the product towards a treatment record (see 4.7).

### 3.4 The six domains are not biologically independent

Inflammation drives cardiovascular and metabolic disease; metabolic state affects cognition; loss
of muscle is metabolic as well as musculoskeletal. The catalog already lists secondary domains for
a marker (for example creatinine), but a run has no place for the clinician to say "the metabolic
improvement and the musculoskeletal decline are the same process" — weight loss with lean-mass
loss. The run's reason field is not that place.

### 3.5 "Regenerative capacity" bundles several systems under one verdict

The catalog fills the domain with measurable markers: kidney function (creatinine, eGFR, cystatin
C, UACR), blood formation (haemoglobin, reticulocytes), autonomic recovery (HRV, heart-rate
recovery), sleep (duration, efficiency, regularity, latency, wake after sleep onset, nocturnal
SpO₂ and respiratory rate), and activity and fitness (steps, active and sedentary time, VO₂max).
Two concerns:

- **One CIS across kidney function, sleep and fitness** is hard to interpret: an improvement in
  sleep regularity and a decline in eGFR give one verdict that means little.
- **The name says more than the markers.** "Regenerative capacity" is not an established clinical
  entity; it invites the reading that the platform measures the body's ability to regenerate,
  which is a claim (_register_, claims discipline). The markers themselves are conventional.

### 3.6 "Risk" does not say risk of what

The risk cell can be reduced, worsened, dominant, unresolved or conflicting — but of what? A
cardiovascular event, mortality, disease progression? The product forbids autonomous risk
prediction, and the cell is meant as a clinician's judgment, not a computed risk. Without a
written meaning, "risk dominant" reads like a risk estimate (_register_).

### 3.7 The functional axis may often be empty

The catalog has functional tests in its core set (grip strength, gait speed, five-chair-stand) and
in the extended set. Whether pilot clinics measure them routinely is an open question; longevity
clinics often hold many laboratory values and few functional ones. If the functional cell is
usually indeterminate, CIS-4 becomes rare — honest, but a reason for clinics to find the model
"never positive", unless the reason is visible.

### 3.8 The reason behind a verdict is optional

Rationale fields exist for each domain and each cell, and both are optional. A non-obvious
verdict — CIS-1, CIS-3, CIS-4, a conflicting risk cell — is exactly where the reasoning matters,
for the next clinician and for any later review.

### 3.9 "Stable" does not say stable where

CIS-5 reads the same for a value stable in a healthy range and one stable in a harmful range. The
Actionability class may carry that difference, but nothing says so.

### 3.10 Reasoning about one person is left to the clinician alone

Clinical evidence is mostly population-level. Judging a single person's change needs repeated
measurements and knowledge of within-person variation. The model gives the clinician the deltas
and the comparability gate (strength 8), but no aid for "is this change larger than this marker
usually varies in one person?"

## 4. Proposals, in order of value for effort

| #    | Proposal                                                                 | Decides                     | _register_ | Effort                    |
| ---- | ------------------------------------------------------------------------ | --------------------------- | ---------- | ------------------------- |
| 4.1  | Written, versioned operational definitions; each run records the version | Medical director            | yes        | document; one field       |
| 4.2  | Rationale required for CIS-1, -3, -4 and conflicting risk cells          | Medical director            | no         | small (validation, form)  |
| 4.3  | Explicit comparison window per run                                       | Medical director            | yes        | small (migration, form)   |
| 4.4  | Written meaning of the risk cell                                         | Medical director, Reg. Lead | yes        | document, wording         |
| 4.5  | Inter-rater calibration on a sample of runs                              | Medical director            | no         | process, no code at first |
| 4.6  | A deterministic reference-change flag per value                          | Reg. Lead, medical director | yes        | medium                    |
| 4.7  | Context between runs, recorded as facts                                  | Founder, Reg. Lead, DPO     | yes        | medium; privacy review    |
| 4.8  | Domain coverage shown while authoring                                    | Medical director            | no         | medium                    |
| 4.9  | Scope or rename "regenerative capacity"                                  | Founder (ADR-0003)          | yes        | ADR change, migration     |
| 4.10 | A run-level note for mechanisms that span domains                        | Medical director            | no         | small                     |

**4.1 Operational definitions.** For each CIS value and each cell state: the minimum number of
measurements, the period, what counts as confirmation on another axis, what counts as functional
evidence, when "stable" is stable. Owned and versioned by the medical director; every run records
the version it was authored under, so a verdict is always read against the definition it used.
This is the step that turns the doctrine into an instrument.

**4.2 Required rationale** for the verdicts that most need one. A validation rule and a form
change; the vocabulary does not change.

**4.3 Comparison window.** A baseline date and a comparison date on the run (or per domain),
shown with every verdict. A schema change (Alembic migration) and a form field.

**4.4 Meaning of "risk".** One plausible reading, consistent with the prohibition on risk
prediction: _the direction of the established risk factors measured in this domain, as judged by
the clinician — not an estimate of the probability of an event._ The wording is claims-bearing.

**4.5 Calibration.** A second clinician rates a sample of runs blind; agreement is measured per
domain (Cohen's or Fleiss' kappa). Low agreement means the definitions (4.1) are incomplete. Like
the preparation-time metric, this measures the instrument instead of assuming it works. It needs
no code to begin.

**4.6 Reference-change flag.** For each value, a deterministic statement that the change from the
previous comparable value exceeds the marker's reference change value, computed from published
analytical and within-person biological variation (for example the EFLM Biological Variation
Database). It is a computation on observations, never a CIS — the clinician still decides. It sits
next to the deterministic deltas and the comparability gate the platform already has, but it gives
a change clinical weight, so it goes through the register before it is built.

**4.7 Context between runs.** A structured note of what changed for the patient since the last run
(medication started or stopped, illness, weight change, training), recorded as fact and never as a
recommendation. More health data, a move towards a treatment record, and a new processing purpose:
it needs the register, a privacy review (data minimisation, DPIA) and counsel before design.

**4.8 Coverage while authoring.** When a clinician records a domain, show which of its core
markers have no value, or only a stale one. The patient page already shows a deterministic data
coverage (not a quality rating); this brings it to the point of judgment, and makes an
indeterminate or CIS-0 verdict visibly a data gap rather than a finding.

**4.9 Regenerative capacity.** Either define what one CIS means across its sub-systems (4.1), or
name and scope the domain by what it measures (for example recovery, sleep and renal reserve). The
six axes are fixed by ADR-0003, so a change is a founder decision and an ADR, with a migration.

**4.10 Cross-domain note.** A run-level field for mechanisms that span domains. It is free text,
so it should pass the same restricted-language check as report statements
(`apps/api/src/hadp_api/modules/reports/language.py`).

## 5. Questions for the medical director

1. What makes an improvement "credible" — per CIS value, in measurable terms (4.1)?
2. Which verdicts must carry a reason (4.2)?
3. Over which period should a verdict be read, and should the run say so (4.3)?
4. What does the risk cell mean (4.4)?
5. Would you rate a sample of runs blind with a colleague, to measure agreement (4.5)?
6. Is a reference-change flag useful at the point of judgment, and which source of biological
   variation would you trust (4.6)?
7. Which context between runs matters most, if any (4.7)?
8. Does "regenerative capacity" hold together for you as one verdict (4.9)?
9. Should "stable" distinguish a favourable from an unfavourable level, or is that
   Actionability's job (3.9)?
10. Which functional tests can the pilot clinics measure routinely (3.7)?

## 6. What this paper does not do

It changes no code, no vocabulary and no intended-use statement. It proposes no score, no derived
verdict and no recommendation of treatment. Every proposal that touches clinical meaning goes
through the classification register before it is built, and the medical director's answers to
section 5 are the input, not this paper.
