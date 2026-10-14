# HADP — technical due diligence, one page

Status as of 2026-10-14. Written for a reader outside the team: what exists, what it is
held to, what is missing, and what that costs. Every figure here is from the repository on
that date; nothing is projected. Synthetic data only: no real patient data has entered any
environment of this product.

## What it is

A physician-governed analytics workspace for longevity and preventive-care clinics in the
DACH market. A clinic imports laboratory results (CSV, LDT 2, LDT 3), the system validates
and records them, and a clinician writes a per-patient, per-domain interpretation from a
closed vocabulary; a medical director approves; the patient sees only the approved version.
The product model is a governance doctrine (ADR-0003): **the engine validates and records;
it never derives.** No score, no percentage, no diagnosis, no "optimal range" — by design
and by test. The current intended-use statement is `docs/regulatory/INTENDED_USE.md`.

## Architecture

| Layer    | Choice                                                    | Size                                 |
| -------- | --------------------------------------------------------- | ------------------------------------ |
| Web      | Next.js 15, React 19, TypeScript strict, German / English | ~15,500 lines, 10 browser test files |
| API      | Python 3.13, FastAPI, SQLAlchemy 2, Alembic               | ~15,300 lines, 63 routes, 536 tests  |
| Data     | PostgreSQL 16, Redis, S3-compatible object store          | 23 migrations, 22 RLS policies       |
| Delivery | Docker images, Compose; one demo server (Hetzner, DE)     | 5 CI jobs                            |

A modular monolith (`identity`, `tenancy`, `patients`, `consents`, `documents`, `imports`,
`observations`, `kpi`, `interpretation`, `reports`, `audit`, `privacy`, `metrics`), one
database, one worker seam. Decisions with lasting effect are recorded in seven ADRs.

## What it is held to

- **Tenant isolation twice.** Every patient-scoped query carries the clinic, and PostgreSQL
  row-level security enforces it again underneath the application role, which is not a
  superuser. Cross-tenant tests exist for every patient-data endpoint.
- **Append-only audit.** Every sensitive transition (sign-in, patient access, import,
  decision, approval, release, export, deletion) writes an audit event that is never
  updated or deleted; a settings page shows the clinic its own trail.
- **No health data in logs.** A redaction layer sits under all logging, and a test asserts
  that no name, e-mail, value or token reaches a log line.
- **Supply chain.** Dependencies from lockfiles only; images built in CI from those
  lockfiles, run as non-root with a read-only file system, and scanned (grype: a fixable
  HIGH or CRITICAL fails the build). Secret scanning (gitleaks) and dependency advisories
  on every push.
- **Consent and erasure.** Versioned, purpose-scoped consent records; a four-eyes erasure
  request flow (owner requests, medical director decides); data export per GDPR Art. 15/20.
- **Backups.** Nightly age-encrypted dumps to an EU bucket, the private key off the server,
  a restore test that runs weekly in CI. RPO 24 h, RTO one business day
  (`docs/security/BACKUP_RESTORE.md`).
- **Claims discipline.** A forbidden-language scan keeps diagnosis, risk and "optimal"
  wording out of the interface; every feature touching clinical meaning is checked against
  `docs/regulatory/CLASSIFICATION_REGISTER.md` before merge.

## Regulatory position — stated plainly

The MDR / MDSW qualification of the governance model is an **open determination**, owned by
a named Regulatory Lead, due before any real patient data or paid pilot. The product does
not claim to be a medical device and does not claim not to be one. The legal gates before a
pilot — Art. 28 DPA with TOMs, §203 StGB safeguards for every sub-processor, record of
processing, DPIA — are listed in `docs/security/THREAT_MODEL.md` and are not yet executed.

## What is missing before a real clinic

| Gap                                   | Why it matters                                        | Effort    |
| ------------------------------------- | ----------------------------------------------------- | --------- |
| Production sign-in (OIDC + MFA)       | today only a password-less development sign-in        | 1.5 weeks |
| Background worker                     | imports and drafts run inside the request             | 1 week    |
| Monitoring and alerting               | logs exist; no metrics, no alert                      | 3 days    |
| Object-store backup                   | the demo's store is a test double in memory           | 2 days    |
| Independent penetration test          | required by the threat model before real data         | external  |
| DPA / TOMs / DPIA / MDR determination | legal gates, owned by counsel and the Regulatory Lead | external  |

Four weeks of one engineer for the first four rows; the last two run in parallel and are
bought, not built. The order and the design of each are in the team's plan; none changes
the architecture.

## Known technical debt

- The web app's four largest components are over 1,100 lines each and carry 570 inline
  style blocks; two stylesheets coexist. Being reduced page by page (eight design PRs in
  the last week); no runtime effect.
- No unit tests on the web presenters; coverage there is through 72 browser tests.
- The demo server builds its images on the server; a deployment would pull scanned,
  pinned images from a registry.

## What the metric says today

The product's commercial claim is a 50% reduction in median clinician preparation time per
appointment. The platform measures lead time from first draft to first approval and records
the clinic's own baseline; the comparison is not yet shown as one number on screen, and no
clinic has yet supplied a baseline. That is the first thing a pilot produces.
