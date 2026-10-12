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
- **Prototype remnants in the web app (go-live plan A10, 2026-10-12):** ✅ removed — the
  password / second-factor / lock-screen mock and the "Prototyp-Zustände" switcher on the
  sign-in page, navigation entries and tabs with no page behind them, controls that only raised
  a notice, and the "nicht freigegeben" wording on approved and released reports. The sign-in
  page now shows the sign-in the deployment has: the development sign-in outside production, and
  a plain "not set up" notice in production until an identity provider is connected (workstream
  B). The review page says only what a status proves: "freigegeben" names the condition for
  access (a valid link, standing consent) instead of claiming the patient sees the report, and
  the audit strip no longer shows "Vollständig" or a clinical sign-off for a version that was
  rejected. `scripts/smoke_web.py` fails if mock UI returns and, in CI, checks the wording in
  every status (draft, approved, released, rejected, reworked) and opens the patient view with
  the issued link. Still open, deliberately: the two Übersicht panels that say why they are
  empty (ADR-0006 — activity feed, imports) use engineering wording; the legal links
  (Datenschutz, Nutzungsbedingungen) return when those pages exist (workstream D); the report
  review page keeps the legacy shell (on a narrow screen its only way out is the brand link).
  The report statements themselves are the next entry. Found by the review
  and not fixed here: reading a report (`GET /reports/{id}`) writes no audit event, while the
  sign-in page says access is logged; the staff-invitation page tells a new colleague to sign
  in, which a production deployment cannot offer yet; "Einstellungen" is an empty page for
  clinician and assistant; whether a released report is still reachable (link valid, consent
  standing) is not exposed by the API, so the UI can only name the condition; the web app has
  no unit-test runner, so the sign-in mode and the presenters are covered by the smoke only.
- **Report statements: German, and the result as the source wrote it (go-live plan A10,
  2026-10-12):** ✅ the deterministic provider writes German (`narr-2`) and states a numeric
  result verbatim; a unit conversion is named beside the source value. Before, a published
  value the terminology does not know (six terms are mapped today) read "… was unknown", and a
  converted value stood alone with seven computed digits under "source reference interval".
  A result is quoted only if it is a plain number (optionally with a comparator) whose unit is
  one token; anything else — a text result, a flagged value, free text typed into the value or
  unit field — is mentioned and never quoted: those fields are free text, and a statement is
  patient-facing. Still open: reports generated earlier keep their English text until a new
  draft (a version is never rewritten). **The price of the rule:** numeric results whose unit
  is not one token are not quoted either — `92 mL/min/1.73 m²` (eGFR), `38 mmol/mol Hb`,
  `30 mg/g Krea`, `1,2 g/24 h`, `95 % der Norm` — nor are `1.234,5`, titers (`1:160`), ranges
  (`0-1`), `neg.` or `++`. Quoting by a verified unit catalog instead of by shape belongs to
  plan item A2. **Decisions:** whether a text result may appear in a patient statement at all
  (today: no), and the wording of the sentence that stands in for it; units with a space; the
  decimal mark of numbers the platform writes when neither the value nor its reference text
  has one ("130 mg/dL (umgerechnet: 3.361774 mmol/L)" — otherwise they follow the source); how
  many digits a converted value shows; the write-time term list for human edits is
  English-stem based — extending it to German is the founder decision in the go-live plan
  (§6.6). **What a source can still put into a statement unchecked:** the analyte name (up to
  200 characters, as on `main`) and a unit token of up to 20 characters without whitespace,
  refused only when it carries an English restricted stem ("Therapie-empfohlen" passes); both
  have been published by a clinician from the review queue, and either can block a later
  rework at the edit guard. **Gaps the review found, not fixed here:** a value the terminology
  does not know gets no reference interval in its statement and shows as "—" in the tables
  (bounds are parsed only for mapped analytes — plan item A2); every import path carries a
  text result as a numeric observation without a value (see
  `docs/product/LAB_IMPORT_FORMATS.md`, "Known limits"); a manual-entry time without an
  offset is stored as UTC, while file readers read the same time in the laboratory zone; a
  number written with a thousands separator ("1,234") is read as 1.234; the day-only fix in
  the interpretation evidence has no test under a database session west of UTC;
  `LAB_LOCAL_TIMEZONE` is not validated at startup.
- **The clinic reads its own audit trail (go-live plan A9, 2026-10-12):** ✅ Einstellungen →
  Audit-Protokoll (owner): newest first, paged by a cursor, filtered by area, day and record.
  The read filters by tenant explicitly — row-level security also passes tenant-less events
  (sign-ins of every user), which are no clinic's. Still open: no index for the query yet
  (`tenant_id` alone; fine at pilot volume — add `(tenant_id, created_at DESC, id DESC)` when
  the trail grows); no export of the trail and no retention rule; sign-ins are tenant-less and
  so not part of any clinic's trail (the entry into the clinic is); reading a report still
  writes no event (separate task); the "Letzte Aktivität" panel on the Übersicht stays gated —
  a feed for every role is a different decision than an owner's audit view.
- **Patient-view Beta hardening**: per-page boundary note added; a fuller
  patient-appropriate presentation is gated for the real-data Beta.
