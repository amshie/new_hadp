# Adversarial review — fixed vs. deferred

A 4-dimension adversarial review (doctrine, security, architecture, QA) with per-finding
verification produced 19 confirmed findings. Fixed in this build:

- **P0** Production fail-open to superuser DSN (RLS bypass) → production config guard +
  engine role assertion. See [[0005-rls-fail-open-production-guard]].
- Dev-default `SESSION_SECRET` / S3 creds accepted in production → same guard.
- Failed-authorization and denied patient-view attempts were not audited → independent,
  commit-on-its-own-connection `record_security_event` (survives request rollback);
  wired into authz denials and patient-view denials; tested.
- Re-release / edit-after-release left stale patient links valid → `release_report` and
  `edit_report` now revoke outstanding `PatientAccessLink` rows; tested end-to-end.
- Edit-after-approval invariant unreachable via API → `POST /reports/{id}/edit` wired.
- `assemble_report_view` silently dropped unresolved evidence → now surfaced as `missing`.
- Dead released-branch in `edit_report` removed.
- Tests added: production guard; glucose-vs-cholesterol factor (anti-swap), HbA1c `%`
  passthrough, µmol/L & ng/mL → review, one-sided interval, large value; cross-tenant
  access by resource id (404); cross-tenant token replay (404); clinician-only
  approve/release matrix; assistant-cannot-approve via API; failed-authz is audited;
  narrative forbidden-language guard; api-client OpenAPI contract test (CI `pnpm test`
  is no longer vacuous).

Deferred (out of scope for M0/M0.5 — tracked here, not silently dropped):

- **Supersession / corrected-report matching** (CLAUDE.md Ingestion → Corrected reports):
  the `supersedes_observation_id` column exists, but conservative matching + its tests
  are **Milestone 1** ingestion work, not the spike. Implement with M1.
- **`generate_draft` idempotency**: each call creates a new draft Report. Acceptable
  multi-draft behavior for the spike; add a patient-scoped report list + "open draft"
  reuse when the report UI is built out.
- **Log redaction of short/integer values**: the redactor catches emails, tokens, and
  value-shaped/long numbers, but cannot redact every bare integer without nuking ids.
  The real control is "application code never logs observation values" — enforce by
  review and add structured-logging field allow-listing if/when structured logs land.
- **Web test coverage / Playwright e2e**: the api-client now has real tests; a Playwright
  happy-path e2e for the upload→approve→patient-view workflow is the documented
  follow-up (the live `make smoke` covers the API path today).
- **Broad static forbidden-language scan over all UI copy**: ✅ DONE — `apps/api/tests/
  test_web_copy_language.py` scans every `.ts/.tsx` under `apps/web/src` for restricted
  intended-use terms (stem-matched to catch plurals + German inflections), strips comments
  and the two sanctioned negated disclaimers, and runs in `make check` / `make test-db`.
  Closes the ADR-0004 §0 "DE/EN labels through the language scan before any UI ships" gate.
- **Patient-view Beta hardening**: per-page boundary note added; a fuller
  patient-appropriate presentation is gated for the real-data Beta.
