# AGENTS.md — Longevity Health Analytics Platform

> **Product model superseded — see [ADR-0003](docs/adr/0003-adopt-hadp-governance-doctrine.md)
> (founder decision, 2026-06-22).** This file's original **lab-analytics** intended use, prohibited
> list, and forbidden-language bank are **superseded for the product model** by the HADP
> **governance** doctrine: the core artifact is a per-patient, per-axis interpretation (six domains;
> clinician-authored CIS + Actionability closed-enum verdicts + verdict-free tri-state cells;
> append-only). The engine **validates and records; it never derives.** **Retained in force** (not
> dropped): synthetic-data-only, tenant isolation via RLS, append-only audit + provenance, **no
> unified score / no %**, closed vocabularies, and the human gates for real patient data, MDR/SaMD
> qualification, and GDPR/DPIA. The current intended-use statement of record is
> [`docs/regulatory/INTENDED_USE.md`](docs/regulatory/INTENDED_USE.md). Where this file conflicts
> with ADR-0003 on the _product model_, ADR-0003 wins; on _safety/privacy/regulatory invariants_,
> both agree and they remain binding.

## Purpose of this file

This repository contains a greenfield B2B health-data product for longevity and preventive-care clinics in the DACH/EU market. This file is the persistent project contract for Codex.

> **Sync note.** This file is a Codex-targeted mirror of [`CLAUDE.md`](CLAUDE.md); the two are identical except for tool-name deltas (Codex ↔ Claude Code) and **must be kept in sync — edit both together, or regenerate one from the other.**

Code, identifiers, commits, and technical documentation use English. User-facing copy is localization-ready; the initial default locale is `de-DE`.

The priorities, in order, are:

1. Patient safety and truthful data presentation
2. Privacy, tenant isolation, and traceability
3. Legal and regulatory defensibility (GDPR, DACH professional-secrecy law, medical-device boundary)
4. A complete clinic workflow that is usable in a pilot
5. Correctness and maintainability
6. Delivery speed
7. Additional features

When priorities conflict, choose the safer and simpler implementation. A feature that cannot be shipped within the documented regulatory and legal boundary is out of scope until that boundary is formally reassessed — regardless of its commercial appeal.

---

## Product mission

Build a GDPR-first analytics workspace for longevity, functional-medicine, concierge, and preventive-care clinics.

The initial product outcome is:

> Import laboratory and wearable data, normalize it, show longitudinal changes, prepare a source-grounded pre-visit report, and require clinician approval before patient release.

The primary business metric is a reduction of median clinician preparation time per appointment by at least 50%. This metric must be measurable in the product, not estimated — see **Metrics and instrumentation**.

### Primary users

- Clinic owner / tenant administrator
- Clinician
- Clinical assistant or care coordinator
- Patient

### Core workflow

1. A clinic creates or invites a patient.
2. The patient records the required consent and optionally connects a data source.
3. Clinic staff upload or enter laboratory data.
4. The system extracts, maps, validates, and normalizes observations.
5. Ambiguous values enter a human review queue.
6. The clinician sees a longitudinal timeline, source ranges, changes, and data gaps.
7. The system creates a source-grounded report draft.
8. A clinician edits and approves the report.
9. The patient receives only the approved version through a secure channel.

---

## Intended use and safety boundary

> **⚠️ SUPERSEDED for the _product model_ — see [ADR-0003](docs/adr/0003-adopt-hadp-governance-doctrine.md) and the intended-use statement of record [`docs/regulatory/INTENDED_USE.md`](docs/regulatory/INTENDED_USE.md).** The lab-analytics "Allowed / Prohibited MVP behavior" lists in this section describe the pre-ADR-0003 model. The **safety/privacy invariants remain binding**: synthetic-data-only, no unified score / no %, closed vocabularies, clinician-in-the-loop, and the human gates for real data / MDR / GDPR.

The MVP is a data aggregation, visualization, workflow, and documentation-support product. It is not an autonomous medical decision-maker.

### Allowed MVP behavior

- Display measurements and their provenance
- Display laboratory-provided reference intervals
- Calculate deterministic deltas, percentages, aggregates, and data freshness
- Highlight values using explicitly configured clinic rules
- Identify missing, stale, duplicate, or conflicting data
- Draft a factual summary tied to specific source observations
- Require a qualified clinician to approve patient-facing reports

### Prohibited MVP behavior

- Diagnose or rule out a disease
- Recommend medication, dosage, treatment, or supplements
- Produce autonomous clinical risk predictions
- Claim to detect, prevent, or cure disease
- Present an inferred value as a measured value
- Replace laboratory reference intervals with undocumented "optimal" ranges
- Send an AI-generated report directly to a patient
- Provide emergency triage or crisis guidance
- Hide uncertainty, source conflicts, or missing information

Any feature that changes this boundary requires a documented product decision, clinical review, privacy review, and **regulatory classification review** before implementation **or marketing** — see **Regulatory classification and governance**.

Use neutral terms such as `observation`, `change`, `source reference interval`, `rule match`, and `draft`. Avoid `diagnosis`, `treatment plan`, `disease detected`, `risk score`, `biological age`, and similar claims unless the product scope has formally changed and been re-classified.

---

## Regulatory classification and governance

> **⚠️ SUPERSEDED for the _product model_ — see [ADR-0003](docs/adr/0003-adopt-hadp-governance-doctrine.md).** The current regulatory positioning of record is [`docs/regulatory/INTENDED_USE.md`](docs/regulatory/INTENDED_USE.md) and [`docs/regulatory/CLASSIFICATION_REGISTER.md`](docs/regulatory/CLASSIFICATION_REGISTER.md): the HADP governance model's MDR/MDSW qualification is an **open, pending determination** (never "MDR-compliant"). The governance discipline in this section (named Regulatory Lead, classification register, claims discipline) **remains binding.**

This boundary is the product's most important and most fragile asset. The commercial pull of "longevity / healthspan" is toward biological-age, optimal-range, and risk-score features — all of which are likely to qualify the product as Medical Device Software (MDSW) under EU MDR (Annex VIII, Rule 11), triggering a notified body, clinical evaluation, ISO 13485 QMS, and post-market surveillance. The MVP deliberately stays on the documentation-support side of that line.

### Governance rules

- A named **Regulatory Lead** owns the device-classification position. Assign this role before pilot go-live; record the holder in `docs/regulatory/OWNERSHIP.md`.
- The **current MVP scope** must receive a formal qualification/classification determination **before** real patient data or a paid pilot, not only when the boundary changes later. Do not assume "non-device" by default; document the determination and its rationale.
- Maintain `docs/regulatory/CLASSIFICATION_REGISTER.md`. Every feature that touches clinical meaning (rules, highlighting, narrative, ranges, scores, comparisons) is checked against the register before merge.
- **Claims discipline:** marketing, sales, and onboarding copy are reviewed against the same boundary as the software. The product cannot advertise diagnosis, risk detection, prevention, or "optimal" health targets while the MVP classification depends on not making those claims. Intended purpose, as stated in claims, often drives classification more than the code does.
- A feature appearing on the **Prohibited MVP behavior** list — or any optimal-range, score, or autonomous-risk feature — is blocked until the documented decision plus clinical, privacy, and regulatory reviews are complete.

A repository skill or runbook may automate part of this review (e.g. an MDR/MDSW analysis pass over the intended-use statement), but a human Regulatory Lead owns the determination, and a notified body or competent authority makes the final assessment. Nothing in this file is legal or regulatory advice.

---

## MVP scope

The pilot is delivered in two phases to reach the primary metric quickly, then expand. Phase 1 is the smallest product that can validate the 50% preparation-time reduction with a real clinic. Phase 2 follows only after Phase 1 is validated in real use.

### Pilot Phase 1 — included (validate the metric)

- Multi-tenant clinic accounts
- OIDC authentication and MFA support
- Role-based authorization
- Patient profile, invitation, consent status, export, and deletion workflow
- Laboratory CSV import
- Manual observation entry
- A parser for **exactly one** pilot-lab PDF layout (only if the lab cannot provide a structured feed — see **Ingestion pipeline**)
- Import review queue with confidence and validation reasons
- Patient timeline and biomarker charts
- Source reference intervals and deterministic change calculations
- Configurable clinic rules
- Source-grounded pre-visit report drafts
- Clinician editing, approval, versioning, and patient release
- Secure web delivery and PDF export
- Audit log, retention controls, backups, and restore procedure
- Preparation-time instrumentation (baseline capture + workflow timing)

### Pilot Phase 2 — fast-follow (expand after Phase 1 is validated)

- A second pilot-lab PDF parser
- One wearable integration behind a provider interface
- OCR fallback hardening for unsupported PDF layouts
- Import monitoring and retry tooling for pilot staff

Wearables and the second parser are deliberately deferred: lab data carries the pilot value, and a wearable integration adds a full asynchronous integration surface for comparatively low first-pilot benefit. Do not start Phase 2 work until Phase 1 has imported real synthetic-equivalent volume and the preparation-time metric is being measured.

### Explicitly excluded from the pilot (both phases)

- Native mobile apps
- Full EHR or practice-management functionality
- Billing and insurance claims
- Arbitrary global laboratory PDF support
- Multiple simultaneous wearable providers
- Population-level predictive modeling
- Biological-age or disease-risk scores in the clinical product
- Patient-facing open-ended AI chat
- Autonomous coaching
- Medication or supplement recommendation engines
- Microservices, Kubernetes, or event-sourcing architecture

A research-only prototype may explore public longevity datasets, but it must remain isolated from the clinical application and cannot be exposed as a production medical feature.

---

## Legal basis, data protection, and DACH requirements

Health data is special-category personal data (GDPR Art. 9). In the DACH market it is additionally protected by professional-secrecy law. The following are engineering-relevant constraints; the binding contracts and legal determinations belong to qualified counsel (Fachanwalt IT-/Medizinrecht) and a data protection officer, not to this file.

### Roles and contracts

- The **clinic is the controller**; the platform operator is a **processor** (Auftragsverarbeiter). A signed Art. 28 data processing agreement (AVV) with documented technical and organizational measures (TOMs) is required **before** any real patient data is processed for a clinic.
- Maintain a record of processing activities (Art. 30) and a per-purpose lawful basis (Art. 9(2)) — typically explicit consent and/or the healthcare-provision basis exercised through the clinic.
- Maintain a published **sub-processor list**. No sub-processor receives health data without compliant safeguards.

### Professional secrecy (DACH-specific)

- Patient data processed on behalf of physicians is subject to professional secrecy (e.g. German §203 StGB). Processing it as an external service provider requires §203-compliant contractual safeguards and access controls, and the same applies to every sub-processor. This is criminal-law exposure, not only GDPR exposure — treat it as a hard gate, not a nice-to-have.

### Data residency and transfers

- All patient and health data, derived artifacts, search indexes, and backups are stored and processed in the EU/EEA.
- No transfer to a third country without an adequacy decision, or SCCs plus a transfer impact assessment (Schrems II). No US sub-processor receives health data without compliant safeguards.
- Production cloud region, OIDC provider, and optional AI provider are chosen to satisfy this constraint (see **Decisions intentionally left configurable**).

### Consent

- `ConsentRecord` is versioned and purpose-scoped, not a single boolean. It records the consent text version, purposes, timestamp, and channel.
- Withdrawal is supported, attributable, and has defined downstream handling (stop processing for the withdrawn purpose; trigger deletion/retention per policy).
- Consent status gates patient creation, data-source connection, and patient release.

---

## Architecture

The MVP is a modular monolith with asynchronous workers. Do not split it into microservices without measured operational need.

### Technology choices

- Frontend: Next.js, React, TypeScript in strict mode
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic
- Database: PostgreSQL
- Background jobs: Redis-backed queue with explicit retries and idempotency
- File storage: private S3-compatible object storage (EU region); MinIO for local development
- Identity: standards-based OIDC; local development may use a local provider
- API contract: OpenAPI generated by the backend; frontend client generated from it
- Local runtime: Docker Compose
- Observability: structured logs, metrics, traces, and correlation IDs with enforced health-data redaction

The split Python (FastAPI) / TypeScript (Next.js) stack is a **deliberate decision recorded in `docs/adr/0001-stack.md`**, justified by laboratory data normalization, exact-decimal and unit-conversion work, and future analytics that benefit from Python. The trade-off is two languages, type systems, and dependency ecosystems for a small team. If team depth or velocity does not support two ecosystems, the documented fallback is a single-TypeScript stack (Next.js with a typed server layer). Do not change the stack without superseding ADR-0001.

Use dependency versions pinned by lockfiles. Never perform an unrequested major-version upgrade.

### Target repository layout

```text
.
├── apps/
│   ├── web/                 # Next.js + TypeScript clinic and patient web app
│   ├── api/                 # FastAPI application and domain modules
│   └── worker/              # Asynchronous import/report jobs
├── packages/
│   ├── api-client/          # Generated TypeScript client from OpenAPI
│   ├── ui/                  # Shared accessible UI components
│   └── config/              # Shared lint/type/build configuration
├── infra/
│   ├── docker/              # Local infrastructure
│   └── migrations/          # Infrastructure migrations when required
├── docs/
│   ├── adr/                 # Architecture Decision Records
│   ├── product/             # Product and workflow specifications
│   ├── security/            # Threat model, runbooks, control notes
│   ├── regulatory/          # Classification register, ownership, intended use
│   └── data-governance/     # Data inventory, licenses, retention, DPA/TOMs
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   └── security/
├── Makefile
├── docker-compose.yml
└── AGENTS.md
```

Do not create empty abstraction layers merely to match this tree. Add directories when the first real implementation requires them.

### Module boundaries

Backend modules should follow business capabilities rather than technical layers:

- `identity`
- `tenancy`
- `patients`
- `consents`
- `documents`
- `imports`
- `observations`
- `terminology`
- `rules`
- `reports`
- `wearables`
- `audit`
- `privacy_requests`
- `metrics`

Modules may call public application services from another module. They must not reach into another module's internal repositories or database implementation.

---

## Domain model and invariants

### Core entities

- `Tenant`
- `User`
- `Membership`
- `Patient`
- `ConsentRecord`
- `SourceDocument`
- `ImportJob`
- `ImportRow`
- `ReviewItem`
- `Observation`
- `TerminologyMapping`
- `RuleDefinition`
- `RuleEvaluation`
- `Report`
- `ReportVersion`
- `ReportEvidence`
- `WearableConnection`
- `AuditEvent`
- `DataExportRequest`
- `DeletionRequest`

### Observation fields

An observation must retain both the source representation and normalized representation.

```text
id
tenant_id
patient_id
source_document_id | source_connection_id
source_record_locator
original_name
metric_code
code_system
value_type
numeric_value | text_value | coded_value
original_value
original_unit
normalized_value
normalized_unit
reference_low
reference_high
reference_text
observed_at
received_at
mapping_confidence
review_status
normalization_version
supersedes_observation_id        # set when this observation corrects a prior one
created_at
```

Additional rules:

- Decimal values use exact decimal types, not binary floating point.
- Timestamps are stored in UTC and rendered in the user's locale/time zone.
- Date-only source values remain date-only; do not invent a time.
- Original values, units, names, and reference text are immutable.
- Corrections create a new version or explicit correction record; they do not silently overwrite provenance.
- A displayed normalized value always exposes the original value and conversion method.
- A derived value records all input observation IDs, algorithm name, and algorithm version.
- Every patient-scoped entity contains `tenant_id` and is protected by tenant authorization.

Use FHIR-inspired concepts where useful, especially Observation and DocumentReference semantics. Do not implement a complete FHIR server for the MVP.

Terminology mappings may use standards such as LOINC and UCUM when verified. Preserve the source term even when a standard mapping exists. Never guess a terminology code with high confidence.

---

## Ingestion pipeline

The ingestion pipeline is explicit and observable:

```text
RECEIVED -> STORED -> EXTRACTED -> MAPPED -> VALIDATED ->
REVIEW_REQUIRED | READY -> PUBLISHED | REJECTED
```

### Prefer structured feeds over PDF

PDF parsing is the most fragile and time-consuming part of this product and the most likely source of patient-safety bugs (wrong value, wrong unit, wrong reference interval). Therefore:

- **Prefer structured laboratory data** (LDT, HL7, FHIR, CSV, or a lab API) over PDF wherever a pilot laboratory can provide it. This is a procurement lever as much as an engineering one — secure structured feeds with pilot labs before committing to a PDF parser.
- PDF parsing is the fallback for labs that cannot deliver structured data.
- OCR is the last resort, never a default.
- Budget PDF-parser work at two to three times the naive estimate.

### Required behavior

- Store the original source file before parsing.
- Compute a content checksum and support idempotent re-upload.
- Record parser name and parser version.
- Validate file type using content inspection, not only file extension.
- Apply file-size and page-count limits.
- Reject password-protected or unsupported documents with a clear status.
- Treat OCR as an explicit fallback, not a default.
- Preserve page number and source locator for extracted values.
- Create review items for low-confidence mappings, unit conflicts, impossible values, duplicate ambiguity, and date ambiguity.
- Do not publish review-required observations until a human resolves them.
- Keep parser fixtures free of real patient data.

### Corrected reports

Matching a corrected report to a previously published observation is an explicit, tested case:

- Supersession creates a new version (`supersedes_observation_id`) and preserves the prior version and its provenance. Nothing is silently overwritten.
- The matching heuristic is conservative and documented (e.g. patient + metric + specimen type + observed_at window + lab order identifiers).
- Ambiguous matches enter the review queue rather than auto-superseding.

### Unit normalization

- Conversions are deterministic, versioned, and covered by tests.
- A conversion occurs only for an approved metric/unit pair.
- Unsupported units remain unnormalized and enter review.
- Reference intervals are converted with the same exact conversion as the associated value.
- No unit is inferred solely from the magnitude of a value.

---

## Rules and analytics

The rules engine is deterministic and explainable.

Supported MVP rule categories:

- Above or below the source reference interval
- Absolute change since the previous comparable observation
- Percentage change since the previous comparable observation
- Missing expected metric
- Data older than a configured duration
- Configured clinic threshold

Each evaluation records:

- Rule ID and version
- Input observation IDs
- Evaluation timestamp
- Result and reason
- Thresholds and units used

Rules do not generate diagnoses. UI labels use `rule match` or `attention item`, not `disease alert`.

Do not compare measurements across incompatible methods, specimen types, fasting states, or units unless compatibility is explicitly modeled.

---

## AI use

AI is a constrained drafting component, never the source of numerical truth.

### AI may

- Convert verified structured facts into a readable draft
- Group related observations
- Describe direction and timing of deterministic changes
- Identify questions a clinician may wish to review, using neutral wording

### AI may not

- Perform calculations that normal application code can perform
- Invent measurements, ranges, causes, diagnoses, or recommendations
- Use facts that are not present in the supplied evidence payload
- Publish or approve a report
- Receive more patient data than the task requires

### AI implementation contract

- All providers implement a `NarrativeProvider` interface.
- A deterministic fake provider exists for local development and tests.
- Inputs are structured, minimized, and explicitly permitted for processing.
- Outputs use a strict schema and are validated before persistence.
- Every generated statement references one or more observation or rule-evaluation IDs.
- Unsupported statements fail validation or are removed.
- Prompt template, provider, model identifier, and generation configuration are versioned.
- Patient-facing release always requires a clinician approval event.
- Production contracts must prohibit use of customer data for general model training.
- Prompts, traces, logs, and error reports must not leak health data.

### Meaningful approval

Clinician approval must be a review of evidence, not a checkbox:

- The approval interface displays, for every AI-drafted statement, the underlying source observation(s) and rule evaluation(s) inline.
- A statement whose evidence is not viewable cannot be approved.
- Approval is attributable to a specific user and timestamp.

A report lifecycle is:

```text
DRAFT_GENERATED -> DRAFT_EDITED -> APPROVED -> RELEASED
                                  -> REJECTED
```

Editing after approval creates a new version and invalidates the previous approval for the new version.

---

## Privacy and security requirements

Health data is highly sensitive. Development defaults must minimize exposure.

### Data handling

- Local development and automated tests use synthetic data only.
- Real patient data must never be committed to Git, copied into fixtures, pasted into issues, or sent to unapproved tools.
- Secrets live in environment variables or a secret manager; `.env` files are ignored.
- `.env.example` contains names and safe placeholders only.
- Application logs exclude names, email addresses, document contents, observation values, access tokens, and full request bodies.
- Health-data redaction is enforced by a shared logging/telemetry redaction layer and covered by tests that assert no name, email, value, token, or document content appears in logs, traces, or error reports. Policy alone is insufficient — the redaction must be tested.
- Analytics tools receive no patient or health data.
- Backups are encrypted, stored in the EU/EEA, and restore-tested. Define and document RTO and RPO targets appropriate to a pilot (for example RPO ≤ 24h, RTO ≤ 1 business day) and validate them with the restore test.
- Deletion includes database records, derived artifacts, search indexes, and object storage according to the approved retention policy.

### Tenant isolation and authorization

- Every request resolves an authenticated principal and active tenant context.
- Authorization is server-side and deny-by-default.
- Client-side UI hiding is never an authorization control.
- PostgreSQL row-level security is used as defense in depth for tenant-scoped tables where practical.
- Queries for tenant-scoped data require tenant context; repositories do not expose unscoped list methods.
- Cross-tenant access tests are mandatory for every patient-data endpoint.
- Support access is explicit, time-limited, audited, and disabled by default.

### Security controls

- MFA support for clinic users
- Secure, short-lived sessions and token validation
- CSRF protection where cookie authentication is used
- Rate limiting on authentication, invitations, uploads, exports, and report generation
- Strict upload validation and malware-scanning integration point
- Private object storage with short-lived signed access
- Security headers and a restrictive content security policy
- Dependency and container scanning in CI
- Audit events for login, failed authorization, patient access, import, review, edit, approval, release, export, deletion, and administrative changes

Never weaken a security control merely to make a test pass. Fix the design or test setup.

---

## Metrics and instrumentation

The 50% reduction in median appointment-preparation time is the primary business metric and a pilot conversion criterion. It must be measured by the product, not estimated afterward.

- Capture a per-clinic **baseline** at pilot onboarding (current preparation time, by structured clinic input).
- Instrument preparation time from **Milestone 3** onward via workflow timestamps — for example, time from report-prep start to clinician approval — supplemented by structured clinic self-report.
- Metric events carry no health data: identifiers and timings only, tenant-scoped, audited.
- Surface the metric so the pilot can be evaluated against the success criteria without manual data archaeology.

---

## API conventions

- Base path: `/api/v1`
- Resource-oriented routes and explicit action endpoints only when a state transition is involved
- JSON field names use `snake_case` in the Python API contract unless the generated client establishes a documented alternative
- Timestamps use ISO 8601 and include a timezone
- Pagination is cursor-based for patient and audit collections
- Import creation supports idempotency keys
- Errors use a stable machine-readable code plus safe human-readable detail
- Validation errors never echo document contents or secrets
- Request and job correlation IDs propagate through logs and audit events
- Breaking API changes require a versioning decision and migration plan

The OpenAPI document is the contract. Generate the TypeScript client; do not manually duplicate API types in the frontend.

---

## Frontend and UX requirements

The interface is a clinical workspace, not a consumer wellness game.

- Display source, observation date, unit, and reference interval near each value.
- Distinguish measured, normalized, and derived values.
- Show uncertainty and review status visibly.
- Do not encode meaning with color alone.
- Charts include an accessible table or textual alternative.
- Values in charts and tables use the same formatting and units.
- Avoid false precision; preserve meaningful decimal places from the source.
- Destructive actions require clear confirmation and authorization.
- Empty, loading, error, stale-data, and partial-data states are designed explicitly.
- Patient-facing pages show only approved content.
- Copy avoids fear-inducing language and unsupported promises, and never implies diagnosis, risk detection, or "optimal" targets.
- Components meet WCAG 2.2 AA for the primary clinical workflow; best-effort elsewhere for the MVP.

Use server components and server-side data access where appropriate, but keep authorization in the API/backend domain rather than relying on the frontend runtime.

---

## Coding standards

### General

- Prefer straightforward code over clever abstractions.
- Keep changes focused; avoid unrelated refactors.
- Do not introduce a dependency when a small, well-tested standard-library solution is sufficient.
- New dependencies require a clear reason, compatible license, maintenance check, and security consideration.
- Do not edit generated code manually.
- No dead feature flags, placeholder production behavior, or fake success responses.
- Use feature flags only when there is a removal plan.
- All database schema changes use Alembic migrations.
- Architecture decisions with lasting impact receive a concise ADR.

### TypeScript

- TypeScript strict mode stays enabled.
- Avoid `any`; use `unknown` plus validation at boundaries.
- Validate external data at runtime.
- React components remain small and focused.
- Business rules do not live only in UI components.
- Generated API types are the source for network payloads.

### Python

- Python code is fully type-annotated at public boundaries.
- Pydantic models validate API and external-provider data.
- SQLAlchemy 2-style APIs are used.
- Database transactions are explicit at application-service boundaries.
- Domain logic is not embedded in route handlers.
- Broad `except Exception` blocks are prohibited unless they re-raise after safe logging or form a documented job boundary.
- Monetary and laboratory decimal values use `Decimal` where exactness matters.

### Database

- Foreign keys and meaningful constraints enforce invariants.
- Indexes are based on real query patterns.
- Tenant ID participates in relevant unique constraints.
- Migrations are forward-safe and include data migration logic when necessary.
- Destructive migrations require an explicit rollout and backup plan.

---

## Test strategy

A feature is incomplete without tests appropriate to its risk.

### Required test layers

- Unit tests for normalization, mapping, rules, permissions, and report evidence validation
- Property-based tests for approved unit conversions and numerical invariants
- Parser golden tests using synthetic/redacted fixture documents
- API integration tests against PostgreSQL and object storage
- Authorization matrix tests
- Cross-tenant isolation tests
- Background-job idempotency and retry tests
- Log/telemetry redaction tests (no health data in logs, traces, or errors)
- Playwright end-to-end tests for the primary clinic workflow
- Backup/restore smoke test before pilot

### High-risk cases

Always test:

- Decimal separators and locale formatting
- Confusable units such as `mg/dL`, `mmol/L`, `µmol/L`, and `ng/mL`
- Missing or one-sided reference intervals
- Duplicate observations
- Corrected lab reports and supersession matching
- Date-only values and timezone boundaries
- Very large or impossible values
- Ambiguous patient matching
- Unauthorized and cross-tenant access
- Report statements without valid evidence IDs
- Editing a report after approval
- Re-uploading the same file

### Quality gates

The repository should expose these stable commands through `make`:

```bash
make bootstrap      # install pinned dependencies and prepare local config
make dev            # run app dependencies and development servers
make format         # format all supported languages
make lint           # static linting
make typecheck      # TypeScript and Python type checks
make test           # unit and integration tests
make test-e2e       # browser workflow tests
make check          # format check + lint + typecheck + test
```

Create and maintain these commands during foundation work. CI uses the same commands as local development.

---

## Codex working protocol

For each implementation task:

1. Inspect the relevant files, tests, migrations, and current git diff before editing.
2. State a concise implementation plan when the change spans multiple modules.
3. Implement the smallest complete vertical slice.
4. Add or update tests with the implementation.
5. Run the narrowest relevant checks, then `make check` when practical.
6. Review the diff for privacy leaks, tenant-scope mistakes, migration risk, and unrelated changes.
7. Summarize changed files, validation performed, assumptions, and remaining risks.

Additional rules:

- Do not claim a command passed unless it was actually run successfully.
- Do not delete, reset, force-push, rewrite history, or run production commands unless explicitly requested.
- Do not create commits unless explicitly requested.
- Do not modify unrelated user changes in the working tree.
- When requirements are ambiguous, choose the safest reversible implementation and document the assumption.
- A temporary stub must fail visibly or be clearly labeled; it must not impersonate a real integration.
- External APIs are wrapped behind an interface and covered by contract tests or recorded synthetic fixtures.
- A feature that would cross the intended-use boundary is not implemented; it is raised for the documented review process instead.
- Update this file only for durable project-wide facts. Put detailed procedures in `docs/` or a future `.Codex/skills/` entry.

---

## Implementation sequence

Follow this order unless a documented dependency requires a change.

### Milestone 0 — Foundation

- Monorepo and developer commands
- Local PostgreSQL, Redis, and object storage
- CI with lint, types, tests, and secret scanning
- OIDC integration skeleton
- Tenant, user, membership, role, patient, and audit models
- Synthetic data generator
- Threat-model, data-flow, and intended-use documents; classification register initialized

Exit criteria: a clinic user can authenticate, select an authorized tenant, create a synthetic patient, and all access is audited and tenant-tested.

### Milestone 0.5 — Vertical spike (de-risk before depth)

Before fully building Milestone 1, implement a deliberately thin end-to-end spike: one synthetic laboratory value travels upload → normalized observation → clinician timeline → source-grounded draft → clinician approval → patient view, even if rough and unstyled.

Purpose: surface the module-integration seams and confirm the preparation-time workflow is coherent before investing in depth. The spike is throwaway-acceptable, must never ship to a real patient, and is replaced by the proper milestones.

Exit criteria: the full happy-path crosses every module once, on synthetic data, with no patient release of unapproved content.

### Milestone 1 — Laboratory vertical slice

- Secure upload and source-document storage
- CSV importer
- Manual observation entry
- Observation model and terminology mapping
- Validation and review queue
- Patient observation table with provenance

Exit criteria: a synthetic lab file can move from upload to reviewed, published observations without direct database edits.

### Milestone 2 — Timeline and analytics

- Longitudinal charts and accessible tables
- Reference intervals
- Deterministic change calculations
- Data freshness and missing-data rules
- Rule explanation UI

Exit criteria: every displayed flag is reproducible from versioned inputs and rules.

### Milestone 3 — Reports

- Evidence payload builder
- Deterministic local narrative provider
- Optional approved AI provider adapter
- Draft editor, evidence links, approval, versioning, release
- Secure patient view and PDF export
- Preparation-time instrumentation and baseline capture

Exit criteria: no patient can view an unapproved report, every generated factual statement has evidence, and preparation time is being measured.

### Milestone 4 — Pilot integrations (Phase 2 begins here)

- One specific lab PDF parser for Phase 1; the second parser is fast-follow
- One wearable provider (fast-follow)
- Import monitoring and retry tools
- Pilot clinic configuration

Exit criteria: pilot staff can complete normal imports without developer intervention, except documented unsupported cases.

### Milestone 5 — Pilot hardening

- Authorization review
- Security review
- Restore test
- Export and deletion test
- Performance test for expected pilot volume
- Operational runbooks and incident workflow
- Regulatory classification determination on record; DPA/TOMs in place for pilot clinics

Exit criteria: no critical security issue remains open, the full primary workflow passes end to end, and the legal/regulatory gates for processing real patient data are satisfied.

---

## Data-source governance

Public and research datasets may be useful for synthetic examples, offline analytics experiments, and an investor demo. They are not the commercial data moat and must not be mixed casually with clinical patient data.

Potential research sources include NHANES, SHARE, HRS, NACDA resources, Gateway to Global Aging Data, and restricted sources such as MIMIC-IV. Access terms vary by dataset.

Rules:

- Maintain `docs/data-governance/THIRD_PARTY_DATA.md` with source, version, purpose, license/DUA, access owner, permitted use, retention, and redistribution limits.
- Do not commit downloaded raw datasets to Git.
- Do not use a dataset commercially unless its terms explicitly allow the intended use.
- Restricted datasets remain in a separate approved environment.
- Never attempt re-identification.
- Demo fixtures are synthetic or demonstrably permitted and de-identified.
- Research models and notebooks are not production clinical features without separate validation and review.

Long-term product defensibility should come from consented longitudinal data partnerships with clinics and laboratories, not from repackaging public datasets.

---

## Definition of done

A change is done only when:

- The user-visible workflow is complete, not merely scaffolded.
- Acceptance criteria are met.
- Authorization and tenant scope are enforced server-side.
- Relevant tests pass.
- Migrations and generated clients are included when required.
- Logs and error paths contain no health data or secrets, verified by redaction tests.
- Audit events exist for sensitive state transitions.
- Accessibility and error states were considered.
- The change stays within the intended-use boundary, or the documented review process was followed.
- Documentation reflects new durable behavior.
- No known critical patient-safety, security, or data-integrity issue remains.

---

## MVP success criteria

The pilot is successful when:

- Three clinics use the product in real workflows.
- At least 50 patient records are imported successfully.
- The Phase 1 lab format works without developer assistance for normal cases (Phase 2 formats and the wearable follow).
- Every published value is traceable to its source.
- No low-confidence value is published without human resolution.
- Median appointment-preparation time falls by at least 50%, measured by the instrumented metric against the captured baseline.
- At least two pilot clinics convert to paid continuation.
- The regulatory classification is determined and on record, and DPAs/TOMs are in place for pilot clinics.
- No critical security or privacy issue remains unresolved.

---

## Decisions intentionally left configurable

The first wearable provider, the pilot-lab formats, production cloud (EU region), production OIDC provider, and optional AI provider depend on pilot customers and contractual review.

Implement stable interfaces and local fakes for these boundaries. Do not select or deeply integrate a vendor merely to fill an undecided field. Any vendor that processes health data must satisfy the EU data-residency and sub-processor requirements before integration.
