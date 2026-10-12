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

| STRIDE                             | Threat                                                                  | As-built mitigation                                                                                                                                                                                              |
| ---------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Denial of service                  | Brute-force login, mass invitations, upload/export/report-gen flooding. | Redis-backed fail-closed rate limiting on login, the patient-view token surface, uploads, and release (shipped 2026-07-03 — see §5); breaches emit audited `rate_limited` events. Correlation IDs aid detection. |
| Information disclosure / Tampering | Clickjacking, MIME sniffing, mixed content, referrer leakage.           | Security headers in place: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a **restrictive CSP**.                                     |
| Spoofing                           | Forged/poisoned input in error responses or correlation.                | Correlation IDs propagate through logs/audit; validation errors never echo input.                                                                                                                                |

## 5. Residual risks and pending controls

These are **not yet implemented or are external gates**. They are the highest-priority hardening backlog before any real patient data or paid pilot.

- **Production identity (gated):** real OIDC + MFA is an explicit not-implemented stub pending the IdP vendor decision (must satisfy EU data-residency). Until then there is **no production-grade identity assurance**; the dev provider is non-production and refuses to run in prod.
- **Rate limiting (shipped 2026-07-03, P-pre-1):** Redis-backed fixed-window throttling on login (10/min/IP), the public patient-view token surface (30/min/IP), document upload and report release (30/min/user) — **fail-closed** when Redis is unreachable (503; a missing backend never silently disables throttling), with an audited `rate_limited` security event on breach. Invitation/redeem surfaces inherit the same dependency when they ship.
- **Staff invitations (shipped 2026-07-03):** a clinic OWNER invites a colleague who self-onboards via a single-use link. Create/list/revoke are **owner-only** (`STAFF_INVITE_CREATE`, deny-by-default); the redeem surface is anonymous (token in the POST body, rate-limited 30/min/IP, fail-closed on Redis). The granted **role is fixed by the owner** on the invitation — the redeemer cannot choose it (the redeem body has no role field). Redemption is a single-use compare-and-swap under a `SELECT … FOR UPDATE` row lock, so concurrent redeems cannot double-provision access; every non-redeemable state (unknown/expired/revoked/redeemed/taken-email) is the same neutral 404 (no oracle). The `staff_invitations` table is RLS ENABLE+FORCE tenant-scoped; the created `Membership` is bound to the invitation's own tenant, never a caller value. Audit carries role codes only (no name/email). Created users are `is_synthetic=True` (Alpha).
- **Member administration (shipped 2026-07-04):** an OWNER lists the clinic team, changes a member's role, and removes members (`MEMBER_LIST` / `MEMBER_ROLE_CHANGE` / `MEMBER_REMOVE` — owner-only, deny-by-default). `memberships` is a non-RLS table, so every query scopes by tenant_id **explicitly**; a cross-tenant membership id is the same 404 as an unknown one. Guards: **no self-target** (an owner cannot change/remove their own membership — every change is attributable to another owner and prevents accidental lock-out) and the tenant must **retain ≥1 owner** (defense-in-depth; unreachable via the API given self-target, enforced at the service for non-API callers). Role assignment is orthogonal to the two-tier Physician Gate. Audit (`member.role_changed` / `member.removed`) carries role codes only.
- **Malware scanning (integration point only):** an integration point exists for upload malware scanning but no scanner is wired in; uploaded files are not yet scanned for malicious content.
- **Upload validation (partial):** content-inspection, size/page limits, and rejection paths are intended/established but full enforcement and golden-fixture coverage are pending parser work (Milestone 1/4). **Update 2026-10-12:** the structured readers (CSV, LDT 2, LDT 3) choose the format by content inspection, refuse a structurally unreadable file as a whole (LDT 3 additionally by its SHA-1 trailer checksum — an integrity check against damage, not an authenticity control), and are covered by synthetic fixtures (`docs/product/LAB_IMPORT_FORMATS.md`); an LDT file is accepted at upload by its line format regardless of the declared content type. PDF page limits and password-protected-document handling remain pending (no PDF reader exists). Budget PDF parsing at 2–3× and prefer structured feeds.
- **CSRF / cookie hardening (shipped 2026-07-03, P-pre-2):** unsafe methods on cookie-authenticated requests require an allow-listed Origin/Referer OR the double-submit token (`x-csrf-token` header matching the non-httpOnly csrf cookie issued at login); rejections are 403 + audited `csrf.denied`. HSTS is emitted in production; the production config guard refuses cookie names without the `__Host-` prefix. `Secure` stays production-conditional; `SameSite=lax` unchanged.
- **Patient token out of the URL (shipped 2026-07-03):** the patient bearer token no longer travels in a query string. The API `/patient-view` endpoint takes the tenant + token in the **POST body** (not the URL), and the minted link points at a web cookie-exchange entry (`/patient-view/oeffnen`) that stashes the token in an **httpOnly** cookie and 303-redirects to a clean, tokenless `/patient-view` — so the token never persists in the address bar, browser history, or a referrer. Access-log redaction (P-pre-3: `RedactingFilter` on `uvicorn.access`; `token=`/`code=` scrubbed) remains as defense-in-depth for any residual query token (e.g. the transient `/oeffnen` entry URL).
- **Object-storage hardening (to confirm):** bucket policy least-privilege, signed-URL TTL bounds, and EU-region enforcement to be validated.
- **Backups, restore, deletion completeness (pending):** encrypted EU backups with a tested restore (RTO/RPO targets) and deletion that also reaches derived artifacts, indexes, and object storage are required before pilot (Milestone 5).
- **Dependency/container scanning in CI (to confirm wired).**
- **Penetration test (pending):** an independent pen-test and authorization/cross-tenant review are required as a pilot-hardening gate (Milestone 5) before processing real patient data.
- **Legal/regulatory gates (owned externally, pending):** Art. 28 DPA + TOMs, §203-compliant safeguards for every sub-processor, record of processing (Art. 30), sub-processor list, and the formal MDR/MDSW classification determination must be on record before real data or a paid pilot. Not legal or regulatory advice.

## 6. Summary

The as-built foundation is strong on the two properties that matter most for this product: **tenant isolation** (defence-in-depth via deny-by-default app authz _and_ FORCE RLS that denies on unset context) and **non-repudiation** (DB-enforced append-only audit). Health-data confidentiality is reinforced by log redaction, `no-store`, restrictive headers, and immutable source provenance. The dominant residual exposures are the **gated production identity stack**, **missing rate limiting**, **the unwired malware scanner**, and the **external legal/regulatory and pen-test gates** — all of which must close before any real patient data is processed.
