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

- **DB-level CHECK constraints for enum columns (found 2026-07-03):** ✅ DONE.
  SQLAlchemy 2.x creates NO CHECK for `native_enum=False` enum columns by default, so the
  closed vocabularies were enforced at the Python layer only. Migration `0009` added the CHECK
  for `memberships.role` and `0013` for `staff_invitations.role`; migration **`0014`** now
  covers the remaining 28 enum columns, so **every** `native_enum=False` enum column is
  DB-enforced. `apps/api/tests/test_enum_check_constraints.py` asserts completeness (a future
  enum column shipped without a CHECK fails the test) and that a bogus value is rejected at the
  DB. The `pg_enum` docstring was corrected to match.
- **Supersession / corrected-report matching** (CLAUDE.md Ingestion → Corrected reports):
  ✅ DONE 2026-10-12 — `modules/imports/matching.py`, `tests/test_supersession.py`; rule and
  remaining limits in `docs/product/LAB_IMPORT_FORMATS.md` ("Repeated and corrected values").
  Still open: a released report is not withdrawn automatically when a cited value is replaced
  (a clinician withdraws it with a new draft; automatic retraction is a governance decision),
  and a reviewer cannot declare an unmarked value the replacement of another.
- **`generate_draft` idempotency**: each call creates a new draft Report. Acceptable
  multi-draft behavior for the spike; add a patient-scoped report list + "open draft"
  reuse when the report UI is built out. **UI guard (2026-10-11):** the patient detail offers
  "Berichtsentwurf erstellen" only while the patient has no report and otherwise links to the
  existing one ("Bericht öffnen"), so the UI cannot stack drafts; the API itself is unchanged.
  A rejected report is reworked on the review page ("Überarbeiten", clinician): the existing
  edit endpoint opens a new version and the rejected one stays a preserved record.
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
- **Report statements: German, and the value as the source wrote it (go-live plan A10,
  2026-10-12):** ✅ the deterministic provider writes German (`narr-2`) and states name, value
  and unit verbatim; a unit conversion is named beside the source value. Before, a published
  value the terminology does not know (six terms are mapped today) read "… was unknown", and a
  converted value stood alone with seven computed digits under "source reference interval".
  Still open: reports generated earlier keep their English text until a new draft (a version
  is never rewritten). **Decisions:** German prose with a decimal point ("3.885 mmol/L" can be
  read as 3885) — the number format is one decision for the whole product; how many digits a
  converted value shows; the write-time term list for human edits is English-stem based —
  extending it to German is the founder decision in the go-live plan (§6.6). **Gaps the review
  found, not fixed here:** a value the terminology does not know gets no reference interval in
  its statement and shows as "—" in the tables (bounds are parsed only for mapped analytes —
  plan item A2); a manual-entry time without an offset is stored as UTC, while file readers
  read the same time in the laboratory zone; source-supplied analyte names are not checked
  against the restricted terms when a draft is generated; `LAB_LOCAL_TIMEZONE` is not validated
  at startup.
- **Patient-view Beta hardening**: per-page boundary note added; a fuller
  patient-appropriate presentation is gated for the real-data Beta.
