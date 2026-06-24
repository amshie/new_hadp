# Product Workflow

This document specifies the product workflow for the Longevity Health Analytics Platform: the
primary users, the end-to-end clinic workflow, the report lifecycle, the meaningful-approval
requirement, and the preparation-time metric plan. The binding contract is `CLAUDE.md`; this
specification refines it and does not override it.

It describes the intended workflow across the pilot milestones. Where a step depends on a milestone
that is not yet built (notably imports/observations depth and the full report lifecycle in
Milestone 3), this is labelled **(planned)** so the document is not read as a claim of as-built
behaviour. Foundation and the vertical-spike scaffolding (auth, sessions, tenancy/RLS, audit,
redaction, consent and observation data models) exist as described in the architecture notes.

This document is not legal or regulatory advice. The device-classification position and the
GDPR/§203 contractual gates (OIDC vendor, cloud region, DPA/TOMs, formal classification
determination) are owned by the named Regulatory Lead and qualified counsel, and remain pending
until recorded.

---

## 1. Intended-use boundary (workflow constraint)

Every step below operates inside the intended-use boundary and must not cross it:

- The product **aggregates, visualizes, computes deterministic change, runs configured clinic
  rules, and supports documentation**. It is **not** an autonomous medical decision-maker.
- No step diagnoses, rules out disease, recommends medication/treatment/supplements, produces an
  autonomous risk prediction, presents an inferred value as measured, substitutes an undocumented
  "optimal" range for a lab reference interval, or releases an unapproved report to a patient.
- User-facing copy uses neutral terms — _observation, change, source reference interval, rule
  match, attention item, draft_ — and avoids _diagnosis, treatment plan, disease detected, risk
  score, biological age,_ and _"optimal" range_.
- A statement of uncertainty, a source conflict, or missing data is never hidden by any step.

A feature that would move a workflow step across this boundary is not built; it is raised through
the documented product/clinical/privacy/regulatory review process instead.

---

## 2. Primary users

Roles are enforced server-side by a deny-by-default role matrix in
`apps/api/src/hadp_api/auth/`; client-side hiding is never an authorization control. The implemented
roles are **owner**, **clinician**, and **assistant**; **patient** is a workflow actor who consumes
released content through a separate, narrowly-scoped surface rather than a clinic-staff role.

### 2.1 Clinic owner / tenant administrator (`owner`)

- Owns the tenant: configures the clinic, invites and manages staff, assigns roles.
- Configures clinic rules (`rules` module, planned) and clinic-level settings.
- Initiates and oversees privacy-request workflows (export, deletion) and reviews the tenant audit
  trail.
- Captures the per-clinic preparation-time **baseline** at onboarding (see §6).
- May not approve or release patient-facing reports unless that user is also a clinician — approval
  is a clinical act (§4.3).

### 2.2 Clinician (`clinician`)

- The clinical decision-maker in the workflow and the **only** role permitted to approve and release
  a patient-facing report.
- Reviews the longitudinal timeline, source reference intervals, deterministic changes, rule
  matches, data gaps, and conflicts.
- Resolves clinical review-queue items (ambiguous mappings, unit conflicts, impossible values,
  duplicate/date ambiguity) (planned, Milestone 1).
- Edits the report draft, inspects the evidence behind each statement, and performs the meaningful
  approval (§4.3).

### 2.3 Clinical assistant / care coordinator (`assistant`)

- Operational support: creates/invites patients, records consent status, uploads laboratory files,
  enters manual observations, and triages the import review queue.
- May **not** approve or release reports and may **not** perform clinical resolution that requires a
  clinician's judgement.
- Operates entirely within tenant scope; all actions are audited with actor and correlation ID.

### 2.4 Patient

- Records versioned, purpose-scoped consent (`ConsentRecord`; `consents` module) and may optionally
  connect a data source (wearables are Phase 2 / planned).
- Receives **only approved, released** report versions through a secure, narrowly-scoped channel.
- Never sees draft, edited-but-unapproved, rejected, or superseded content, and never sees another
  patient's or another tenant's data (enforced by app-level authorization and PostgreSQL RLS;
  see `apps/api/alembic/versions/0002_security_rls.py`).

---

## 3. Core workflow

The numbered steps mirror the core workflow in `CLAUDE.md`. Each step resolves an authenticated
principal and an active tenant context, is deny-by-default authorized, and emits an append-only
audit event (`audit_events`) carrying identifiers/codes/timings only — never health-data values.

1. **Create or invite a patient.** An owner or assistant creates a patient record (or sends an
   invitation). Every patient row carries `tenant_id` and `is_synthetic`. _(models exist; UI
   workflow planned, Milestone 0/1.)_
2. **Record consent; optionally connect a source.** The patient records a versioned, purpose-scoped
   `ConsentRecord` (consent text version, purposes, timestamp, channel). Consent status **gates**
   patient creation completion, data-source connection, and patient release; withdrawal is
   attributable and triggers defined downstream handling.
3. **Upload or enter laboratory data.** An assistant or clinician uploads a lab file or enters
   observations manually. The original source file is stored before parsing, with a content checksum
   for idempotent re-upload, file-type inspection by content (not extension), and size/page limits
   (`documents`, `imports` modules; planned, Milestone 1).
4. **Extract, map, validate, normalize.** The ingestion pipeline advances explicitly:
   `RECEIVED -> STORED -> EXTRACTED -> MAPPED -> VALIDATED -> REVIEW_REQUIRED | READY ->
PUBLISHED | REJECTED`. Each observation retains **both** the immutable source representation
   (original value, unit, name, reference text) and the normalized representation; conversions are
   deterministic and versioned; date-only source values keep their date-only flag (no invented time).
   Structured feeds (LDT/HL7/FHIR/CSV/API) are preferred over PDF; OCR is a last resort. _(planned,
   Milestone 1; data model exists in the `observations` module.)_
5. **Human review of ambiguous values.** Low-confidence mappings, unit conflicts, impossible values,
   and duplicate/date ambiguity become review items. **No review-required observation is published
   until a human resolves it.** Corrections supersede via `supersedes_observation_id` (new version,
   prior provenance preserved — never silently overwritten); ambiguous correction matches enter
   review rather than auto-superseding. _(planned, Milestone 1.)_
6. **Clinician reviews timeline and context.** The clinician sees longitudinal charts (with an
   accessible table/text alternative), source reference intervals, deterministic deltas/percentages,
   data freshness, missing/stale/duplicate/conflicting flags, and rule matches — each reproducible
   from versioned inputs and rule versions. Measured, normalized, and derived values are visually
   distinguished; a derived value records its input observation IDs, algorithm name, and version.
   _(planned, Milestone 2.)_
7. **System creates a source-grounded report draft.** A draft is generated from a minimized,
   structured evidence payload. Every factual statement references one or more observation and/or
   rule-evaluation IDs; statements unsupported by evidence fail validation or are removed. AI, when
   used, is a constrained `NarrativeProvider` (a deterministic local fake exists for dev/test); it
   performs no calculations, invents no measurements/ranges/causes, and cannot publish or approve.
   _(planned, Milestone 3.)_
8. **Clinician edits and approves.** The clinician edits the draft and performs the
   meaningful approval (§4.3). Approval is attributable to a specific user and timestamp and is
   audited.
9. **Patient receives the approved version.** Only the `RELEASED` version is delivered to the patient
   through the secure patient channel (web view and PDF export). No unapproved content is ever
   patient-visible. _(planned, Milestone 3.)_

---

## 4. Report lifecycle

### 4.1 States and transitions

```text
DRAFT_GENERATED -> DRAFT_EDITED -> APPROVED -> RELEASED
                                  \-> REJECTED
```

| State             | Meaning                                                             | Patient-visible |
| ----------------- | ------------------------------------------------------------------- | --------------- |
| `DRAFT_GENERATED` | System produced a source-grounded draft from the evidence payload.  | No              |
| `DRAFT_EDITED`    | A clinician edited the draft; evidence links revalidated.           | No              |
| `APPROVED`        | A clinician completed meaningful approval (§4.3); attributable.     | No              |
| `RELEASED`        | The approved version was delivered to the patient channel.          | Yes             |
| `REJECTED`        | A clinician rejected the draft/edited version; it does not advance. | No              |

- The lifecycle is owned by the `reports` module (`apps/api/src/hadp_api/modules/reports/`); the data
  model exists, the transition workflow is **planned (Milestone 3)**.
- A report carries one or more `ReportVersion` records; `ReportEvidence` links each statement to its
  source observation(s)/rule evaluation(s).
- Only a **clinician** may move a version to `APPROVED`, `RELEASED`, or `REJECTED`. Each transition
  is audited (actor, tenant, action, target, correlation ID; identifiers/timings only).

### 4.2 Editing after approval invalidates the approval

> **Editing a report after approval creates a new version and invalidates the previous approval for
> the new version.**

Operationally:

- An `APPROVED` version is immutable. Any edit produces a **new** `ReportVersion` starting at
  `DRAFT_EDITED`.
- The prior approval applies only to the version it was granted for; it does **not** carry forward.
  The new version is unapproved and **not patient-visible** until a clinician approves it again.
- If a version was already `RELEASED`, the released content remains the patient-visible artifact
  until a newly-approved version is itself released; the patient is never silently shown edited,
  unapproved text.
- Every version transition (including the approval-invalidating edit) is audited and attributable.

### 4.3 Meaningful approval

Approval is a review of evidence, not a checkbox:

- For **every** drafted statement, the approval interface displays the underlying source
  observation(s) and rule evaluation(s) **inline**, with provenance (source, observed date, unit,
  source reference interval).
- **A statement whose evidence is not viewable cannot be approved.** If evidence for any statement
  is missing or not inspectable, that version cannot reach `APPROVED`.
- Approval is attributable to a specific clinician user and timestamp, and is recorded as an audit
  event.
- Because approval gates patient release, consent status (§3 step 2) must permit release for the
  relevant purpose before a `RELEASED` transition is allowed.

---

## 5. Authorization, tenancy, and audit (cross-cutting)

- **Authentication:** OIDC in production is a **gated vendor decision (pending)** and is currently an
  explicit not-implemented stub; a clearly-labelled dev provider is used in dev/test only and refuses
  to run in production. Sessions are server-side (random token in an httpOnly cookie; only the
  SHA-256 hash stored; revocable).
- **Authorization:** server-side, deny-by-default role matrix; cross-tenant and unauthorized-access
  tests are mandatory for patient-data endpoints.
- **Tenant isolation:** enforced in app code **and** by PostgreSQL row-level security — the app
  connects as non-superuser `hadp_app`; tenant-scoped tables have `ENABLE`+`FORCE` RLS keyed on the
  transaction-local GUC `app.current_tenant`
  (`apps/api/alembic/versions/0002_security_rls.py`). Unset context denies all rows; cross-tenant
  reads return nothing.
- **Audit:** every sensitive transition (login, failed authorization, patient access, import,
  review, edit, approval, release, export, deletion, admin change) writes to the append-only
  `audit_events` table (DB trigger blocks `UPDATE`/`DELETE`; app role lacks those grants).
- **Logging/redaction:** a shared redaction layer scrubs emails, tokens/secrets, and value-shaped
  numbers from logs/traces/errors; covered by tests. Validation errors never echo input.

---

## 6. Preparation-time metric plan

The primary business metric is a **≥ 50% reduction in median appointment-preparation time per
clinic**, measured by the product against a captured baseline — not estimated afterward. It is also a
pilot conversion criterion.

### 6.1 Baseline capture (onboarding)

- At pilot onboarding, the owner/tenant-admin records a per-clinic **baseline** preparation time via
  structured clinic input (current median prep time per appointment).
- The baseline is tenant-scoped, attributable, and audited. It contains **no health data** —
  identifiers and timings only.

### 6.2 Instrumentation (from Milestone 3)

- Preparation time is instrumented from **Milestone 3 onward** via workflow timestamps — for example,
  the elapsed time from _report-prep start_ to _clinician approval_ — supplemented by structured
  clinic self-report.
- Timestamps are derived from the report lifecycle transitions in §4, so the metric is reproducible
  from recorded workflow events rather than manual archaeology.

### 6.3 Metric-event constraints

- **Metric events carry no health data:** identifiers and timings only, tenant-scoped, audited.
- Metric events pass through the same redaction guarantees as all other telemetry; no patient name,
  email, observation value, token, or document content may appear in a metric event.
- The metric is surfaced so a pilot can be evaluated against the success criterion without exposing
  any health data.

---

## 7. Synthetic-data discipline

All dev/test data is synthetic only; every tenant, user, patient, and document carries
`is_synthetic`. Real patient data is never committed, copied into fixtures, pasted into issues, or
sent to unapproved tools. The Milestone 0.5 vertical spike is throwaway and must never release
content to a real patient. Processing real patient data is gated on the pending GDPR Art. 28
DPA/TOMs, §203-compliant safeguards, EU data-residency confirmation, and the formal regulatory
classification determination being on record.
