# Threat Model

> Scope: the as-built Milestone 0 + 0.5 modular monolith of the Longevity Health Analytics Platform (FastAPI/PostgreSQL backend in `apps/api`, Next.js frontend in `apps/web`, Redis queue, S3-compatible object storage). Dev/test runs on synthetic data only. This document is an engineering threat model, not legal or regulatory advice; the formal device-classification determination and the GDPR/§203 contractual gates are owned by the Regulatory Lead and qualified counsel.

## 1. Method and conventions

- Framework: STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege), assessed per asset and per trust boundary.
- "Mitigation" lists **as-built** controls only — what exists in the repository today. Controls that are future work or external gates are not listed as mitigations; they appear in **§5 Residual risks and pending controls** and are labelled pending/gated.
- The single most important asset and the most damaging failure mode is **cross-tenant disclosure of special-category health data**; controls are weighted accordingly.

## 2. Assets

| #   | Asset                                                                                  | Sensitivity                                                       | Why it matters                                                                                                                                 |
| --- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| A1  | Special-category health data (observations, source documents, reference text, reports) | Highest — GDPR Art. 9, DACH professional secrecy (e.g. §203 StGB) | Disclosure is both a GDPR breach and potential criminal-law exposure; integrity errors are a patient-safety risk (wrong value/unit/reference). |
| A2  | Tenant data partition (one clinic's entire dataset)                                    | Highest                                                           | Tenant isolation is the core security property; one cross-tenant leak compromises the controller relationship for every affected clinic.       |
| A3  | Credentials and sessions (session tokens, future OIDC tokens)                          | High                                                              | Compromise enables impersonation and direct access to A1/A2.                                                                                   |
| A4  | Audit trail (`audit_events`)                                                           | High                                                              | The evidence of who did what; must be tamper-evident for non-repudiation, breach forensics, and regulatory defensibility.                      |
| A5  | Consent records (versioned, purpose-scoped)                                            | High                                                              | Gate the lawful basis for processing; tampering or bypass undermines GDPR Art. 9 compliance.                                                   |
| A6  | Report approval/release integrity                                                      | High — patient safety + intended-use boundary                     | Only a clinician may approve/release; an unapproved or AI-direct release to a patient breaks the intended-use boundary.                        |
| A7  | Object storage (original source files, PDF export)                                     | High                                                              | Holds raw, un-normalized health data; signed-URL or bucket misconfiguration leaks A1 directly.                                                 |
| A8  | Application/infra credentials (DB DSN, S3 keys, secrets)                               | High                                                              | Compromise bypasses application-layer controls entirely.                                                                                       |
| A9  | Service availability                                                                   | Medium                                                            | A pilot clinic cannot prepare for appointments if the workspace is down; not life-critical (not a triage system).                              |

## 3. Trust boundaries

```text
                  ┌────────────────────────────────────────────────────────┐
                  │                     Untrusted                           │
   Browser ──────►│  (B1) Public HTTP edge: cookies, CSP, security headers  │
   (clinic user)  └───────────────────────────┬────────────────────────────┘
                                               │  authenticated principal + tenant context
                  ┌────────────────────────────▼────────────────────────────┐
                  │  (B2) FastAPI app: deny-by-default authz, validation     │
                  │       resolves principal → active tenant → set GUC       │
                  └───────┬───────────────────────────┬─────────────────────┘
                          │ connects as hadp_app        │ enqueue
                          │ (non-superuser)             ▼
          ┌───────────────▼──────────────┐   ┌─────────────────────────────┐
          │ (B3) PostgreSQL: RLS FORCE on │   │ (B4) Redis queue + workers  │
          │  app.current_tenant GUC       │   │  (import/report jobs)       │
          └───────────────────────────────┘   └──────────────┬──────────────┘
                                                              │ signed access
                                               ┌──────────────▼──────────────┐
                                               │ (B5) S3-compatible storage   │
                                               │  (MinIO local / EU bucket)   │
                                               └──────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
   │ (B6) External/gated: OIDC IdP (gated stub), optional AI provider,      │
   │       malware scanner (integration point), lab feeds — all untrusted   │
   └──────────────────────────────────────────────────────────────────────┘
```

- **B1 Internet ↔ edge** — anonymous traffic crosses here; everything beyond requires an authenticated principal.
- **B2 Edge ↔ application** — where a request is bound to a principal and an _active tenant context_. The crucial in-process boundary: tenant context must be set before any tenant-scoped DB access.
- **B3 Application ↔ PostgreSQL** — the app connects as the non-superuser role `hadp_app`; RLS is the defence-in-depth boundary that holds even if an app-layer query forgets its tenant filter.
- **B4 Application ↔ queue/workers** — async jobs must re-establish tenant context and carry correlation IDs; they are a second code path to the same data.
- **B5 Application ↔ object storage** — raw health files; only short-lived signed access should cross this line.
- **B6 Application ↔ external/gated services** — OIDC IdP (currently a not-implemented stub), optional AI provider, malware scanner integration point, and lab feeds. All inputs from this boundary are untrusted.

## 4. STRIDE threat table

### A1/A2 — Health data and tenant isolation

| STRIDE                 | Threat                                                                             | As-built mitigation                                                                                                                                                                                                                                                                                                                                             |
| ---------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tampering              | An app-layer query omits its tenant filter and reads/writes another clinic's rows. | PostgreSQL **RLS ENABLE + FORCE** on every tenant-scoped table, keyed on transaction-local GUC `app.current_tenant` set via `set_config(...,true)`; app connects as non-superuser `hadp_app` so RLS is not bypassed (`apps/api/alembic/versions/0002_security_rls.py`, `apps/api/src/hadp_api/db/engine.py`). Repositories do not expose unscoped list methods. |
| Information disclosure | Cross-tenant read returns another clinic's observations/reports.                   | Same RLS policy; **unset tenant context denies all rows** (no default-allow). Tests prove cross-tenant reads return nothing and an unset GUC yields zero rows. Deny-by-default authz at B2 in addition.                                                                                                                                                         |
| Information disclosure | Health values leak through logs, traces, or error responses.                       | Shared **redaction layer** scrubs emails, tokens/secrets, and value-shaped numbers, with tests (`apps/api/src/hadp_api/logging.py`); validation errors never echo input; `Cache-Control: no-store` prevents caching of health responses.                                                                                                                        |
| Tampering              | A normalized/derived value silently overwrites the immutable source.               | Source representation (original value/unit/name/reference text) is **immutable**; corrections create a new version via `supersedes_observation_id`; date-only values keep a `date_only` flag — no silent overwrite.                                                                                                                                             |
| Information disclosure | Raw source files in object storage are read directly.                              | Private S3-compatible bucket (EU region in prod); access is via short-lived signed URLs only (B5). _Bucket-policy hardening and signed-URL TTL belong in §5._                                                                                                                                                                                                   |

### A3 — Credentials and sessions

| STRIDE                 | Threat                                                      | As-built mitigation                                                                                                                                                                                                                                 |
| ---------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Spoofing               | Attacker forges or replays a session to impersonate a user. | Server-side sessions: random token in an **httpOnly** cookie; only the **SHA-256 hash** is stored, never the raw token; sessions are revocable (`apps/api/src/hadp_api/auth/sessions.py`). Every request resolves an authenticated principal at B2. |
| Spoofing               | No real identity assurance in production.                   | Dev provider is **clearly labelled, no real auth, and refuses to run in production**; production OIDC is an explicit not-implemented stub (gated). _This is a gate, not a control — see §5._                                                        |
| Information disclosure | Session cookie stolen via XSS or transport sniffing.        | httpOnly cookie (not script-readable) + restrictive CSP + security headers; stored hash means a DB read does not yield usable tokens. _`Secure`/`SameSite` flag enforcement and HSTS in prod to be confirmed in §5._                                |
| Elevation of privilege | CSRF on a cookie-authenticated state-changing request.      | Listed as a required control for cookie auth; _CSRF token/double-submit enforcement to be verified — tracked in §5._                                                                                                                                |

### A4/A5 — Audit trail and consent

| STRIDE                 | Threat                                                                 | As-built mitigation                                                                                                                                                                                                                          |
| ---------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repudiation            | A user denies an action (access, approval, release, export, deletion). | **Append-only `audit_events`**: DB trigger blocks UPDATE/DELETE and the app role lacks those grants (`apps/api/src/hadp_api/modules/audit/models.py`). Every sensitive transition is audited with actor/tenant/action/target/correlation_id. |
| Tampering              | An attacker edits or deletes audit history to hide activity.           | Same trigger + grant model makes the table tamper-evident at the DB layer; the application path cannot mutate it.                                                                                                                            |
| Information disclosure | Audit detail itself leaks health data.                                 | Audit `detail` carries identifiers/codes/timings only and **rejects sensitive keys**; correlation IDs (not payloads) propagate.                                                                                                              |
| Tampering              | Consent is bypassed so processing proceeds without lawful basis.       | `ConsentRecord` is **versioned and purpose-scoped** (records text version, purposes, timestamp, channel); consent status gates patient creation, source connection, and patient release.                                                     |

### A6 — Report approval / intended-use boundary

| STRIDE                 | Threat                                                           | As-built mitigation                                                                                                                                                                             |
| ---------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Elevation of privilege | A non-clinician approves or releases a patient-facing report.    | Deny-by-default role matrix (owner/clinician/assistant); **only a clinician may approve/release** a patient-facing report, enforced server-side at B2.                                          |
| Tampering              | An AI draft is released to a patient without clinician approval. | Lifecycle requires a clinician approval event before release; patient-facing pages show only approved content; AI is draft-only. _Evidence-link completeness is a Milestone 3 acceptance test._ |

### A7/A8 — Object storage and infra credentials

| STRIDE                 | Threat                                                                         | As-built mitigation                                                                                                                                                                                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Information disclosure | Malicious or malformed upload bypasses validation and reaches storage/parsing. | Upload validation **intent** is established: content-type inspection (not extension), file-size/page-count limits, reject password-protected/unsupported with a clear status, store original before parse, content checksum + idempotent re-upload. _Full enforcement and the malware-scan integration point are in §5._ |
| Information disclosure | Secrets committed or leaked.                                                   | Secrets live in env/secret manager; `.env` is gitignored; `.env.example` holds placeholders only; redaction layer keeps tokens out of logs.                                                                                                                                                                              |
| Spoofing               | Compromised infra credential connects with elevated DB rights.                 | App connects as **non-superuser `hadp_app`** which is subject to FORCE RLS and lacks audit UPDATE/DELETE grants — limiting blast radius even with a stolen app DSN.                                                                                                                                                      |

### A9 / cross-cutting — Denial of service and headers

| STRIDE                             | Threat                                                                  | As-built mitigation                                                                                                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Denial of service                  | Brute-force login, mass invitations, upload/export/report-gen flooding. | _Rate limiting on auth, invitations, uploads, exports, and report generation is required but not yet built — see §5._ Correlation IDs aid detection.                         |
| Information disclosure / Tampering | Clickjacking, MIME sniffing, mixed content, referrer leakage.           | Security headers in place: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a **restrictive CSP**. |
| Spoofing                           | Forged/poisoned input in error responses or correlation.                | Correlation IDs propagate through logs/audit; validation errors never echo input.                                                                                            |

## 5. Residual risks and pending controls

These are **not yet implemented or are external gates**. They are the highest-priority hardening backlog before any real patient data or paid pilot.

- **Production identity (gated):** real OIDC + MFA is an explicit not-implemented stub pending the IdP vendor decision (must satisfy EU data-residency). Until then there is **no production-grade identity assurance**; the dev provider is non-production and refuses to run in prod.
- **Rate limiting (to add):** no rate limiting yet on authentication, invitations, uploads, exports, or report generation — brute-force and resource-exhaustion DoS are currently unmitigated.
- **Malware scanning (integration point only):** an integration point exists for upload malware scanning but no scanner is wired in; uploaded files are not yet scanned for malicious content.
- **Upload validation (partial):** content-inspection, size/page limits, and rejection paths are intended/established but full enforcement and golden-fixture coverage are pending parser work (Milestone 1/4). Budget PDF parsing at 2–3× and prefer structured feeds.
- **Cookie transport flags / HSTS / CSRF (verify):** `Secure`/`SameSite` cookie attributes, HSTS, and CSRF protection for cookie-auth state changes must be confirmed and tested before pilot.
- **Object-storage hardening (to confirm):** bucket policy least-privilege, signed-URL TTL bounds, and EU-region enforcement to be validated.
- **Backups, restore, deletion completeness (pending):** encrypted EU backups with a tested restore (RTO/RPO targets) and deletion that also reaches derived artifacts, indexes, and object storage are required before pilot (Milestone 5).
- **Dependency/container scanning in CI (to confirm wired).**
- **Penetration test (pending):** an independent pen-test and authorization/cross-tenant review are required as a pilot-hardening gate (Milestone 5) before processing real patient data.
- **Legal/regulatory gates (owned externally, pending):** Art. 28 DPA + TOMs, §203-compliant safeguards for every sub-processor, record of processing (Art. 30), sub-processor list, and the formal MDR/MDSW classification determination must be on record before real data or a paid pilot. Not legal or regulatory advice.

## 6. Summary

The as-built foundation is strong on the two properties that matter most for this product: **tenant isolation** (defence-in-depth via deny-by-default app authz _and_ FORCE RLS that denies on unset context) and **non-repudiation** (DB-enforced append-only audit). Health-data confidentiality is reinforced by log redaction, `no-store`, restrictive headers, and immutable source provenance. The dominant residual exposures are the **gated production identity stack**, **missing rate limiting**, **the unwired malware scanner**, and the **external legal/regulatory and pen-test gates** — all of which must close before any real patient data is processed.
