# 0010 — Patient-invitation workflow (plan)

> **Status: PLAN ONLY — not implemented.** Forward-looking design for the full patient-invitation
> workflow (staff invite endpoint → patient-side consent capture → secure delivery). Drafted
> 2026-06-26. **Synthetic identities only.** Pointing any part of this at a real patient stays
> **BLOCKED** behind the go-live gates in §6. This note is engineering planning, **not legal or
> regulatory advice.**

Every claim below was ground-truthed against the codebase by the relevant specialist agents
(security, backend-data, regulatory, fullstack) before drafting; file:line citations are theirs.

---

## 1. Why this exists / what already shipped

The P0 consent gate is **shipped** (merged PR #16, `23f09cd`):

- Consent is an **append-only** `consent_events` stream — one closed `ConsentPurpose` per row; a grant
  and a withdrawal are each a NEW row (RLS ENABLE+FORCE, REVOKE UPDATE/DELETE + BEFORE UPDATE/DELETE
  trigger, FKs `ON DELETE RESTRICT`) — `apps/api/.../modules/consents/{models,service}.py`,
  `alembic/versions/0008_consent_events.py`.
- `consents.service.has_active_consent` is **fail-closed** (no event ⇒ not active) and gates
  patient-facing **report release** (`reports/service.py:251-267`, checked *after* the approval
  invariant). `withdraw_consent` appends a WITHDRAWN event **and** revokes all live
  `PatientAccessLink`s in the same transaction.
- `ConsentPurpose` values (`report_release`, `analytics`, `data_source_connect`) are **synthetic
  placeholders**; the real taxonomy + per-purpose Art. 9(2) lawful basis + consent text are a
  **DPO/counsel deliverable (PENDING)** — `modules/enums.py:77-89`.

What this plan adds is the **front half** of the gate: how a consent grant gets *created* — a staff
member invites a (synthetic) patient, the patient redeems a one-time link, and that redemption
writes the `report_release` GRANT the P0 release path already consumes. `DATA_FLOW.md` step 1 already
says "the patient starts in an invited/inactive state," but **nothing writes an invitation today** —
this plan closes that gap.

The mechanics are buildable now on synthetic identities. The real-patient cutover is **not** an
engineering toggle (§6).

---

## 2. Slice map (one branch + PR each; run the relevant agents first; CI green; squash-merge)

```
P-pre  Security prerequisites (land BEFORE any new token surface)
        P-pre-1  Redis-backed rate limiting + abuse audit signal
        P-pre-2  CSRF guard (Origin/Referer + double-submit) + cookie hardening (__Host-, HSTS)
        P-pre-3  Token-in-URL redaction / transport fix (uvicorn.access + query-string scrub)
P1     Staff invite entity + endpoint   (POST /api/v1/patients/{id}/invitations)
P2     Patient-side consent capture     (POST /api/v1/invitations/redeem — no staff session)
P3     Web                              (staff "Patient einladen" link surfacing + /einladung page)
```

Hard sequencing: **P-pre lands before P1/P2**, because a public, brute-forceable token surface
already exists today (`GET /patient-view?tenant=&token=`, `patient_view_routes.py:25-51`) and the
invite/redeem endpoints inherit exactly that exposure.

---

## 3. P-pre — security prerequisites (the red-team gaps)

### What exists today (grounded)
- **One** inline middleware only — `main.py:67-81` `context_and_security` (correlation-id + security
  headers + restrictive CSP). **No rate-limit, no CSRF.**
- **No rate-limiting** anywhere (no `slowapi`/`limits`; grep-clean). **Redis is already a dependency**
  (`pyproject.toml`), so a token-bucket backend is available with no new heavy dep.
- Session cookie (`auth_routes.py:44-54`): `httponly`, `samesite=lax`, `secure` in prod. **SameSite=Lax
  is the only CSRF mitigation** — no token, no Origin/Referer check. Forgeable cookie-auth POSTs
  already exist (logout, select-tenant, report create/edit/approve/release, upload, patient create).
- **Log redaction EXISTS and is tested** — `logging.py:25-59` `redact()`/`RedactingFilter` (emails,
  bearer/token/secret, decimals, long digit runs) on the **root logger only**; tests in
  `test_logging_redaction.py`. **But** `uvicorn.access` is **not** covered, and the patient token
  travels in a **query string** (`?token=`), so the raw token can leak to access logs / Referer.

### Build
- **P-pre-1 — rate limiting.** A small Redis-backed `rate_limit(key, limit, window)` FastAPI
  dependency (mirror the `Depends(get_db)` DI pattern), keyed **per-IP and per-credential/token**.
  Apply to: dev-login, the new invite-create + token-redeem + consent-capture endpoints, uploads,
  exports, report generation/release. Emit a `rate_limited` security event (mirror
  `record_security_event`). **Fail-closed if Redis is unreachable in production** (a missing backend
  must not silently disable throttling — add a config guard like `config.py`/`engine.py`).
- **P-pre-2 — CSRF + cookie hardening.** A second app middleware: Origin/Referer allowlist
  (`web_base_url`) for unsafe methods on cookie-auth routes, plus a double-submit token issued at
  login. Switch session/CSRF cookies to the `__Host-` prefix; emit HSTS. The CSRF token is a
  **separate, non-httpOnly** cookie/header pair (must not become an XSS-readable session equivalent);
  update `apps/web/src/lib/api.ts` to send it.
- **P-pre-3 — token-in-URL fix (highest severity).** Prefer a **POST-body or path** token over
  `?token=` for redeem so it never enters access logs; attach `RedactingFilter` to `uvicorn.access`
  and extend `redact()` to scrub `token=`/`code=` query params (target token params specifically —
  the generic digit patterns deliberately can't scrub bare ids; see `0006-review-followups`).

### Tests
Negative rate-limit (N+1 → 429 + `rate_limited` event, per-IP **and** per-token); brute-force
resistance (wrong tokens stay 404, no timing oracle); CSRF negatives (cross-origin POST → 403; valid
double-submit → ok) across logout/select-tenant/release/upload/invite/consent; cookie/transport
(prod: `Secure`+`HttpOnly`+`SameSite`+`__Host-`+HSTS — extend `test_config_guard.py`); redaction for
the new surfaces incl. `uvicorn.access`. **All negatives must run on the real unauthenticated /
`hadp_app` path** — a pass under a privileged/bypass test client proves nothing.

### Register / DATA_FLOW
Three new register rows (rate-limiting, CSRF/cookie hardening, token-in-URL redaction), each
*Touches clinical meaning? = No* (security/governance controls), *stays within
documentation-support*, *Shipped (synthetic Alpha)*. Flip `THREAT_MODEL.md` §5 rate-limiting + CSRF
bullets from pending → shipped in the same PRs. These are **prerequisites** for the row-52
patient-invitation gate — they harden the surface but **do not unblock real-patient use**.

---

## 4. P1 — staff invite entity + endpoint

`POST /api/v1/patients/{patient_id}/invitations` — role-gated, audited, rate-limited, idempotent;
returns a one-time token **in the HTTP response for the synthetic demo only** (like `ReleaseOut`).

### Build (mirror the shipped patterns)
- **Migration `0009_patient_invitations.py`** (`down_revision='0008_consent_events'`) mirroring 0008
  verbatim: RLS ENABLE+FORCE + `tenant_isolation` policy on `_TENANT_PREDICATE`; FKs `tenant_id` /
  `patient_id` `ON DELETE RESTRICT`, `created_by_user_id` `ON DELETE SET NULL`; additive + fully
  reversible downgrade.
- **Token hygiene** = reuse `PatientAccessLink`'s shape exactly (`reports/models.py:97`,
  `reports/service.py:275`): raw `secrets.token_urlsafe(32)`, store **only** `hash_token(...)`
  (SHA-256), short TTL, **single-use** (consume-on-redeem — the key delta vs the multi-use access
  link), revocable.
- **Append-only decision (design choice — recommend the split):** the invitation is a *credential*
  with lifecycle state (accept/revoke/expire), so the **row must stay operationally mutable**
  (`accepted_at`/`revoked_at`/`redeemed_at`). Putting the row itself under an append-only trigger
  would abort accept/revoke. **Recommended:** mutable `patient_invitation` row **+** a separate
  append-only `patient_invitation_event` ledger (RLS, RESTRICT-FK, BEFORE UPDATE/DELETE trigger +
  REVOKE) recording `created/accepted/revoked/expired` — immutable audit-of-record, mutable live
  credential. (Audit events alone are an acceptable lighter alternative.)
- **Module** `modules/invitations/{__init__,models,service}.py` (mirror `consents/` + `reports/`):
  `create_invitation(...) -> (row, raw_token)`, `revoke_invitation(...)`, `record_invitation_event(...)`.
- **Authz** — add `Action.INVITATION_CREATE = "invitation.create"` to `authz.py` and map it to
  **all staff** (invite is staff-wide, *not* the clinician-only release gate). Endpoint resolves the
  patient via the RLS-bound `ctx.db` (404 on cross-tenant), `record_audit(action="invitation.create",
  …)` with **non-sensitive detail only — never the token**. Register the router in `main.py`.
- **Closed vocab** — add `InvitationStatus` (`pending/accepted/revoked/expired`) and, if the ledger
  is chosen, `InvitationEventType` as closed `pg_enum`s. **Reuse `ConsentPurpose`; never invent a
  purpose value.**
- **Idempotency** — an `Idempotency-Key` (mirror `import_jobs.idempotency_key`) so a retried invite
  returns the same row without minting a second token.

### Tests
Append-only ledger under `hadp_app` (UPDATE/DELETE → permission denied + trigger raise); RLS
fail-closed (0 rows without bound tenant); cross-tenant 404; authz matrix (staff ok / wrong-role 403 /
unauth 401); token-hygiene (DB stores only the hash; raw token never in `audit_events.detail` or
logs); idempotency (same key → same id, no second token); rate-limit 429; migration up/down
round-trip leaves no orphan trigger/function/policy. **RLS tested under `hadp_app`, not superuser.**

### Register / DATA_FLOW
Update the row-52 gate: *Staff patient-invitation endpoint* — *Touches clinical meaning? = No*
(governance/provisioning control), *stays within boundary*, *Shipped (synthetic Alpha)* for the staff
endpoint; real-patient cutover stays BLOCKED. Realize `DATA_FLOW.md` step 1 ("invited/inactive") by
actually writing the invitation row + ledger event.

---

## 5. P2 — patient-side consent capture

`POST /api/v1/invitations/redeem` — **no staff session** (parity with `/patient-view`). This is the
patient-side half of the gate the P0 release path already enforces; **no change to `release_report`
is needed.**

### Build (mirror `patient_view_routes.py:25-51` exactly)
- Body `{tenant: uuid (Pydantic-validated), token: str}`. Bind RLS via `set_tenant_context(db, tenant)`
  (tenant is non-secret; the **token is the credential**). Resolve by `hash_token(token)`.
- **Fail-closed to `NotFound` with an identical body** when the token is unknown / revoked / expired /
  **already redeemed** (single-use) — no oracle distinguishing them. Audit each failure via
  `record_security_event(action="invitation.redeem_denied", …)` on an independent transaction.
- On success, in **one transaction**: `record_consent(db, tenant_id=…, patient_id=<from invitation>,
  purpose=ConsentPurpose.REPORT_RELEASE, channel="synthetic_invite_redeem", recorded_by_user_id=None,
  consent_text_version=SYNTHETIC_CONSENT_TEXT_VERSION)` → a GRANTED event; then mark the invitation
  `redeemed_at`. `has_active_consent(...REPORT_RELEASE)` then returns True and a subsequent
  `release_report` succeeds where it previously raised `Conflict`.
- **Patient-principal gap (write it down):** there is no patient principal — `recorded_by_user_id`
  stays NULL; attribution rests on the single-use **token identity + channel + `recorded_at`**.
  Counsel must confirm this is sufficiently attributable before any real-patient use.
- **Closed vocab / honesty:** do **not** add a `ConsentPurpose` value; reuse only the enforced
  `report_release`. `channel` and `consent_text_version` are synthetic placeholders. Purpose
  multiplicity (`analytics`/`data_source_connect`) stays out until the DPO taxonomy lands.

### Tests
RLS/tenant isolation (token minted under A unusable under B); fail-closed negatives (unknown/expired/
revoked/redeemed → identical `NotFound` + `redeem_denied` event); consent-write correctness (exactly
one GRANTED event, `recorded_by_user_id IS NULL`, then release succeeds); append-only (redeem never
UPDATE/DELETEs a consent row; re-redeem appends no duplicate grant); withdrawal interaction (reuse the
P0 test: WITHDRAWN revokes links → `/patient-view` 404s); redaction; language scan on any patient copy.

### Doctrine / register
Planning note only — adds no register row itself, but directs any real slice to split/extend row 52
(staff-invite / patient-redeem / delivery) keeping real patients Pending(gated), and to reaffirm the
**named (not fixed) divergence**: `REPORT_RELEASE` is enforceable by `Role.CLINICIAN` while
INTENDED_USE/ADR-0003 reserve lock/release for a **medical director**, and `Role` has no
`medical_director` member (tracked for a future role slice). DATA_FLOW: adds the missing
invite→redeem→consent edge across the UNTRUSTED→APPLICATION boundary into the append-only stream.

---

## 6. P3 — web

### Build (mirror `apps/web/.../patient-view/page.tsx`)
- **Staff "Patient einladen" action** — add `createInvitation(patientId)` to `lib/api.ts`
  (cookie-auth) returning the raw link; a button in `ReviewContent.tsx` page-actions opens a dialog
  (reuse the existing dialog pattern) showing the **one-time URL with a copy button** and an explicit
  *"manuell und sicher außerhalb des Systems teilen — kein automatischer Versand"* note. URL preserves
  tenant context: `/einladung?tenant={tenantId}&token=…`. **Never** wire email/SMS in the Alpha.
- **Patient route** `apps/web/src/app/einladung/page.tsx` — unauthenticated RSC. **`isUuid(tenant)`
  before any fetch** (the guard `/patient-view` currently lacks — `lib/uuid.ts`); single try/catch
  that hides wrong/expired/redeemed; **not** wrapped in `AppShell` (no staff nav for a patient).
- **Consent capture** — a small client component: explicit consent checkbox + disabled-submit (reuse
  the confirm pattern), posts `recordConsent(token)`. de-DE, only approved governance copy; **no report
  / clinical content shown pre-consent**; success / already-redeemed / error states designed
  explicitly.
- **Reusable four-part disclaimer** — add `components/Disclaimer.tsx` (none exists today) and render it
  on `/einladung` and retrofit `/patient-view`.
- **Copy-lock scanner** — `scripts/check-forbidden-language.mjs` **does not exist** today (CLAUDE.md
  references it; only the Python `test_forbidden_language.py` over the narrative provider exists).
  Create it to scan `apps/web` + `packages` user-facing strings against the FORBIDDEN list (strip the
  two sanctioned disclaimer phrases, allowlist closed-vocab files) and wire it into the quality gate —
  otherwise the new German consent/disclaimer copy ships unscanned.
- **JSON-in-script** — if consent metadata is serialized into an inline `<script>`, add a tiny
  `escapeJsonForScript()` (`/</g → <`) and use it.

### Tests
Web UUID guard (`/einladung` with non-UUID tenant renders the neutral invalid shell, issues **no**
fetch); patient-side no-info-leak (bad/expired/redeemed → 404, no patient identity in body);
one-time semantics (second redeem fails closed); consent-gate wiring (grant ⇒ `has_active_consent`
True but **does not auto-release** — release still needs the staff approve→release lifecycle);
copy-lock flags a planted term and passes the shipped copy; four-part disclaimer renders on both
patient pages; e2e (synthetic): mint → manual link → `/einladung` → grant → staff release succeeds,
with no unapproved/clinical content shown pre-consent.

---

## 7. Real-patient go-live gates — engineering MUST NOT satisfy or imply satisfied

All are licensed-human / founder / counsel / DPO decisions, all currently **OPEN** (register row 52):

1. **Regulatory Lead assignment** (currently UNASSIGNED).
2. **MDR/MDSW qualification & classification** determination on record.
3. **DPIA** completed.
4. **ROPA / Art. 30** record entry for the invitation + consent purpose.
5. **Per-purpose Art. 9(2) lawful basis + counsel-authored consent text & versioning** (replaces
   `synthetic-v1`).
6. **AVV/Art. 28 DPA + TOMs + §203 StGB** professional-secrecy safeguards with each pilot clinic.
7. **EU/EEA-residency out-of-band delivery sub-processor** (email/SMS/portal; SCC/TIA if non-EU) —
   the synthetic Alpha does **no** real delivery; staff copies the link manually.
8. **Pen-test** of the public redeem endpoint.

"Rate limiting shipped" must never read as "pen-test passed." Surfacing the raw token in an API
response/URL is acceptable for **synthetic Alpha only** and must be labelled as such. Every
invitation row carries `is_synthetic`.

---

## 8. Cadence & dependencies

- **Order:** P-pre-1/2/3 → P1 → P2 → P3. P-pre is load-bearing because the brute-forceable
  token-in-URL surface (`/patient-view`) already exists; do not add invite/redeem endpoints on top of
  an unthrottled, log-leaking surface.
- **P2 depends on** the DPO/counsel consent-text + lawful-basis deliverable for *real* use — the
  synthetic redeem path can be authored/tested against a directly-seeded synthetic invitation first,
  but real patient-authored consent stays gated.
- **Per slice:** run the relevant agents first (security / backend-data / clinical-regulatory /
  fullstack), add the CLASSIFICATION_REGISTER row(s) + DATA_FLOW update, language-scan any
  user-facing copy, CI green, squash-merge.

## 9. Related follow-up (already filed)

`observation_derivation` (migration 0007) carries the **same** `ON DELETE CASCADE` + append-only-trigger
conflict that was fixed for `consent_events` in 0008 — a new forward migration should change its FKs to
`RESTRICT`. Any new append-only ledger added by P1 (`patient_invitation_event`) must use `RESTRICT`
FKs from the start. The RESTRICT posture also extends the unbuilt **retain-then-erase
(right-to-be-forgotten)** design surface, itself a DPO/counsel Pending gate.
