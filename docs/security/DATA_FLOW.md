# Data Flow

This document describes how data moves through the Longevity Health Analytics Platform end to end, from a clinic creating a patient to a clinician releasing an approved report. It names the ingestion pipeline states, identifies the trust boundaries, states where health data lives, records the EU/EEA residency requirement, and states the rule that logs, traces, and error reports contain no health data.

It reflects the **as-built** system at Milestone 0 + 0.5. Anything not yet built — or held behind a founder/counsel/regulatory gate — is labeled **pending/gated**, not done.

> The platform is a data aggregation, visualization, longitudinal-change, workflow, and documentation-support product. It is **not** an autonomous medical decision-maker. No diagnosis, treatment, risk score, biological age, or "optimal" range is produced anywhere in this flow. Patient-facing release of any draft always requires a clinician approval event.
>
> _Nothing in this document is legal or regulatory advice. The device-classification position is owned by a named Regulatory Lead; a notified body / competent authority makes the final determination (pending/gated)._

---

## 1. Actors and trust zones

| Zone                     | Who / what                                                                                                        | Trust                                      |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Untrusted / external** | Clinic staff browser, patient browser, uploaded lab files, optional AI narrative provider, OIDC identity provider | Untrusted input; validated at the boundary |
| **Application zone**     | `apps/web` (Next.js), `apps/api` (FastAPI), `apps/worker` (Redis-backed jobs)                                     | Trusted code; deny-by-default authZ        |
| **Data zone**            | PostgreSQL (RLS-enforced), S3-compatible object storage (private bucket), Redis queue                             | Health data at rest; EU/EEA only           |

Trust boundaries are marked `===║===` in the diagrams below. Every crossing into the application zone re-resolves the authenticated principal and active tenant, and re-applies server-side authorization. Client-side UI hiding is never an authorization control.

---

## 2. End-to-end clinical flow

```
                          UNTRUSTED                ║   APPLICATION ZONE        ║   DATA ZONE (EU/EEA)
                                                   ║                           ║
 Clinic staff ── create patient ──────────────────╫─▶ patients service ───────╫─▶ Postgres (RLS)
                                                   ║      │                     ║     patients
                                                   ║      ▼                     ║
 Patient/staff ─ record consent ──────────────────╫─▶ consents service ───────╫─▶ consent_records
                                                   ║   (versioned, scoped)     ║   (gates creation,
                                                   ║                           ║    source connect,
                                                   ║                           ║    release)
                                                   ║                           ║
 Clinic staff ─ upload CSV/PDF  ───────────────────╫─▶ documents service ──────╫─▶ object storage
              ─ or manual entry                    ║   (store original first)  ║   (private bucket)
                                                   ║      │                     ║   + source_documents
                                                   ║      ▼                     ║
                                                   ║   imports service ────────╫─▶ import_jobs / rows
                                                   ║      │  enqueue            ║   ║
                                                   ║      ▼                     ║   ▼
                                                   ║   worker: ingestion ──────╫─▶ Redis queue
                                                   ║   pipeline (§3)           ║   observations
                                                   ║      │                     ║   review_items
                                                   ║      ▼                     ║
 Clinician ── timeline / charts ──────────────────╫─▶ observations service ───╫─▶ observations
              review queue                         ║   (published only)        ║   (provenance kept)
                                                   ║      │                     ║
                                                   ║      ▼                     ║
 Clinician ── report draft ───────────────────────╫─▶ reports service ────────╫─▶ reports /
              edit / approve                       ║   evidence builder        ║   report_versions /
                                                   ║      │  (draft-only AI)    ║   report_evidence
                                                   ║      ▼                     ║
 Patient ──── view approved report ───────────────╫─▶ reports service ────────╫─▶ (RELEASED only)
                                                   ║   (approval gate)         ║
═══════════════════════════════════════════════════╩═══════════════════════════╩══════════════════
                                              ║                              ║
                                              ▼ (every sensitive transition) ▼
                                        audit_events  (append-only; UPDATE/DELETE blocked)
```

### Step-by-step

1. **Clinic creates a patient** — `patients` service writes a `tenant_id`-scoped, `is_synthetic`-flagged patient row. Creation itself is **not** consent-gated (the patient starts in an invited/inactive state); the enforced consent gate is on patient-facing **release** (step 8).
2. **Consent is recorded (append-only)** — `consents` service appends a `ConsentEvent` (one closed `ConsentPurpose` per row, versioned text + channel + timestamp + actor). Current state for a (patient, purpose) is the latest event. **Enforced today:** patient-facing report **release** is fail-closed on an ACTIVE `report_release` consent (step 8). **Withdrawal is a NEW attributable event** (never an in-place overwrite) and immediately **revokes any live patient access link** for that patient in the same transaction. Gating of data-source connection and full retention/deletion-on-withdrawal automation are **PENDING** (the data-source-connection feature does not exist yet; the real purpose taxonomy + per-purpose Art. 9(2) lawful basis is a DPO/counsel deliverable). The legacy mutable `ConsentRecord` table is retained inert; the gate reads `ConsentEvent`.
3. **Lab data enters** — either a CSV/PDF upload or manual observation entry. For uploads, the `documents` service **stores the original file first** (private object-storage bucket, `storage_key`), computes a SHA-256 checksum (`checksum_sha256`, unique per `(tenant_id, checksum)` for idempotent re-upload), validates type by content inspection, and applies size/page limits. (CSV importer + manual entry are the Milestone 1 happy path; the single pilot-lab PDF parser is Milestone 4 / Phase 2 — pending.)
4. **Extract / map / validate / normalize** — the `worker` runs the ingestion pipeline (§3). Both source representation (immutable original value/unit/name/reference text) and normalized representation are retained; corrections supersede via `supersedes_observation_id` rather than overwriting; date-only values keep their date-only flag.
5. **Review queue** — low-confidence mappings, unit conflicts, impossible values, duplicate ambiguity, and date ambiguity create `review_items`. **Nothing review-required is published until a human resolves it.**
6. **Timeline / charts** — the clinician sees longitudinal observations, source reference intervals, deterministic changes/freshness, and data gaps. Only `published` observations are displayed.
7. **Source-grounded draft** — the `reports` service builds an evidence payload and produces a draft. AI is a constrained, **draft-only** narrative component: it converts verified facts to readable text, references observation/rule-evaluation IDs for every statement, and cannot publish or invent values. A deterministic fake provider is used locally/in tests; any real provider is a gated EU-residency vendor decision.
8. **Clinician approval** — a clinician reviews evidence inline; a statement whose evidence is not viewable cannot be approved. Approval is attributable (user + timestamp). Report lifecycle: `DRAFT_GENERATED → DRAFT_EDITED → APPROVED → RELEASED` (or `REJECTED`). Editing after approval creates a new version and invalidates the prior approval.
9. **Patient release** — the patient sees **only** the `RELEASED` version. No AI-generated report reaches a patient without a clinician approval event.

---

## 3. Ingestion pipeline states

The pipeline is explicit and observable. State is stored on `import_jobs` / `import_rows` as `ImportStatus` (`apps/api/src/hadp_api/modules/enums.py`, lowercased string values under a CHECK constraint), driven by the worker (`apps/api/src/hadp_api/modules/imports/models.py`).

```
 RECEIVED ──▶ STORED ──▶ EXTRACTED ──▶ MAPPED ──▶ VALIDATED ──┬──▶ REVIEW_REQUIRED ──▶ (human) ──┐
                                                              │                                  │
                                                              └──▶ READY ────────────────────────┤
                                                                                                 ▼
                                                                                    PUBLISHED  |  REJECTED
```

| State             | Meaning                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `RECEIVED`        | Upload/entry accepted; idempotency key checked.                                                                           |
| `STORED`          | Original file persisted to private object storage; checksum computed; type validated by content.                          |
| `EXTRACTED`       | Rows/values extracted; page number and source locator preserved. Parser name + version recorded.                          |
| `MAPPED`          | Terminology mapping attempted (LOINC/UCUM where verified); source term preserved; codes never guessed at high confidence. |
| `VALIDATED`       | Deterministic checks: unit compatibility, impossible/duplicate values, date ambiguity, one-sided reference intervals.     |
| `REVIEW_REQUIRED` | One or more checks need a human; a `review_item` carries the reason and identifiers/codes only. **Blocks publication.**   |
| `READY`           | All checks passed with no human action needed.                                                                            |
| `PUBLISHED`       | Observation(s) visible on the timeline; provenance intact.                                                                |
| `REJECTED`        | Unsupported/invalid (e.g. password-protected, wrong type) or human-rejected, with a clear status.                         |

Observations carry their own `ReviewStatus` (`pending` → `published` | `rejected`), and a `pending` observation is never displayed or used as report evidence.

Idempotency: re-uploading the same file (same `(tenant_id, checksum_sha256)`) does not create a duplicate import. Worker jobs are retried with explicit idempotency.

---

## 4. Where health data lives

| Location           | Data                                                                                                         | Protection                                                                                                                                                                                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PostgreSQL**     | patients, consents, observations (source + normalized), import rows, review items, reports/versions/evidence | Per-tenant RLS: app connects as non-superuser `hadp_app`; every tenant-scoped table has `ENABLE` + `FORCE ROW LEVEL SECURITY` with a policy keyed on transaction-local GUC `app.current_tenant` (`apps/api/alembic/versions/0002_security_rls.py`). Unset context denies all rows. |
| **Object storage** | original uploaded lab files (PDF/CSV)                                                                        | Private S3-compatible bucket (MinIO local). Access only via short-lived signed URLs; never public.                                                                                                                                                                                 |
| **Redis queue**    | job references / identifiers for ingestion work                                                              | Identifiers and job state only; not a health-data store of record.                                                                                                                                                                                                                 |
| **`audit_events`** | actor / tenant / action / target / correlation ID                                                            | Append-only: a DB trigger blocks `UPDATE`/`DELETE` and the app role lacks those grants. `detail` carries identifiers, codes, and timings only and rejects sensitive keys.                                                                                                          |

Health data does **not** live in: application logs, traces, error reports, metric events, analytics tools, or AI prompts beyond the minimized evidence payload explicitly permitted for processing.

---

## 5. EU/EEA data residency

All patient and health data, derived artifacts, search indexes, and backups are stored and processed in the **EU/EEA**. Specifically:

- PostgreSQL, object storage, and the Redis queue run in an EU region (MinIO local for dev; EU bucket in prod).
- No transfer to a third country without an adequacy decision, or SCCs plus a transfer impact assessment (Schrems II). No US sub-processor receives health data without compliant safeguards.
- Backups are encrypted, stored in the EU/EEA, and restore-tested (RTO/RPO targets and the restore test are Milestone 5 — pending).
- Production cloud region, OIDC provider, and any optional AI provider are chosen to satisfy this constraint and are currently **gated** vendor decisions; in production the OIDC integration is an explicit not-implemented stub and the dev provider refuses to run in production.
- Published sub-processor list, Art. 28 DPA, and TOMs must be in place **before** real patient data — currently **pending/gated**. Dev and test use **synthetic data only**; every tenant/user/patient/document carries `is_synthetic`.

---

## 6. No health data in logs, traces, or errors

This is a hard rule, enforced in code and tested — not a policy statement:

- A shared redaction layer (`apps/api/src/hadp_api/logging.py`) scrubs emails, tokens/secrets, and value-shaped numbers before anything is logged. Application logs exclude names, email addresses, document contents, observation values, access tokens, and full request bodies.
- Correlation IDs propagate through logs and audit events so a request/job can be traced **without** carrying its health payload.
- Validation errors never echo input; HTTP error detail is safe and machine-readable (stable code + safe human-readable detail).
- `audit_events.detail` rejects sensitive keys and stores identifiers/codes/timings only.
- Metric events (preparation-time instrumentation, Milestone 3 — pending) carry identifiers and timings only, tenant-scoped and audited; no health data.
- AI prompts, traces, and error reports must not leak health data; the provider receives only the minimized evidence payload.

Redaction is covered by tests asserting no name, email, value, token, or document content appears in logs, traces, or error reports.

---

## 7. Cross-cutting controls on every flow

- **Authentication** — server-side sessions: a random token in an httpOnly cookie; only its SHA-256 hash is stored; revocable. OIDC in production is gated.
- **Authorization** — deny-by-default role matrix (`owner`, `clinician`, `assistant`) in `apps/api/src/hadp_api/auth/authz.py`; only a clinician may approve/release a patient-facing report.
- **Tenant isolation** — enforced in app code **and** by PostgreSQL RLS; cross-tenant reads return nothing and an unset tenant context denies all rows (tested).
- **Audit** — every sensitive transition (login, failed authZ, patient access, import, review, edit, approval, release, export, deletion, admin change) is appended to `audit_events`.
- **HTTP hardening** — `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a restrictive CSP on responses.

---

## 8. Pending / gated items referenced above

- Single pilot-lab PDF parser and OCR fallback (Milestone 4 / Phase 2).
- Production OIDC vendor; production cloud region; optional AI narrative provider — all EU-residency vendor decisions.
- Preparation-time metric instrumentation + baseline (Milestone 3).
- Backup/restore RTO/RPO validation (Milestone 5).
- Published sub-processor list, Art. 28 DPA, TOMs, and the formal device-classification determination — required before real patient data / paid pilot (Milestone 5; counsel + Regulatory Lead gate).

_Not legal or regulatory advice._
