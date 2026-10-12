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
- **Web test coverage / Playwright e2e**: ✅ DONE 2026-10-12 for the primary workflow —
  `apps/web/e2e/primary-workflow.spec.ts` walks it through the UI alone, on synthetic data:
  a new patient with consent → a laboratory CSV of which the import publishes one value and
  holds two → the review queue → the interpretation run → the report draft → the clinical
  approval → the medical director's release → the patient's page through the access link.
  `make test-e2e` runs it against the running stack (it starts no server and resets nothing;
  each run adds one synthetic patient); the `web-build-smoke` CI job runs it against the
  production build. Still open: the paths beside the primary one (rejection and rework, a
  laboratory correction, LDT files, the invitation link, the owner's pages) have no browser
  test — the route smoke and the API tests cover them. A patient's attempt before the release
  cannot be made through the UI at all: the access link exists only once the release has
  issued it.
  Found while writing it: the interpretation form's labels were not associated with their
  controls (`AuthorRunContent.tsx` — `<label>` beside `<select>` without `htmlFor`), so the
  selects and text fields of the form had no accessible name — a WCAG 2.2 AA gap in the
  primary clinical workflow. ✅ Fixed 2026-10-13: every label is bound to its control, each
  tri-state cell is a named group, and the suite finds the fields by name.
  Found by its first run against the production build: **a form whose submit is handled in
  script submits natively when it is used before React has hydrated it.** The forms have no
  `method` and no `action`, so the browser sends a GET to the same address: the page reloads,
  what was entered is gone without a message — **and it is in the address bar, the history
  and the web server's access log**: the e-mail address as `/login?email=…`, the laboratory
  file's name as `?file=…`. The laboratory upload form and the sign-in form are such forms
  (`LabDocumentsCard.tsx`, `SignInForm.tsx`). ✅ Fixed 2026-10-13: both keep their submit
  button disabled until the page is hydrated (`lib/useHydrated.ts`) — a disabled default
  button also stops the Enter key — and the suite tries both on pages whose scripts are kept
  from loading. The third script-handled form (the patient wizard) only exists once the page
  is hydrated.
  From the independent review of the suite, taken: the step that claimed to show "before the
  release" is named for what it shows (a browser without a link), and a link that is not the
  issued one is tried after the release; every context fails its step on an uncaught page
  error (the suite was blind to them — the review predicted a hydration error on every run
  from dates formatted in the server's zone; fixed in its own change). Still open from it:
  the interpretation step gives all six axes the same values and asserts one field, so
  swapped or dropped verdicts would pass (CIS is rendered on no reading page — its storage is
  proven by API tests only); the statements are checked by their beginning, not in full; the
  roles are shown by a control being absent, the refusals themselves are API tests; nothing
  crosses a clinic boundary in the browser; one green run in three is not yet stability — and it was not: a later run created the
  patient under its name with the reference appended, because the dialog moves focus to its
  first field 30 ms after opening (`components/vitabahn/Dialog.tsx`) and the test was already
  typing into the second. The step waits for that focus now.
  Also found: **the MinIO images `docker-compose.yml` names can no longer be pulled** — Docker
  Hub answers 404 for `minio/minio` and `minio/mc` (checked 2026-10-12). A machine that
  already holds them keeps working; a new machine, or one that lost its image cache, cannot
  start local object storage. CI therefore gives the browser test an S3 test double (moto, in
  a process). Local development needs another S3-compatible image — a choice to make, not
  made here.
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
  rework at the edit guard. **Gaps the review found, not fixed here:** every import path carries a
  text result as a numeric observation without a value (see
  `docs/product/LAB_IMPORT_FORMATS.md`, "Known limits"); a manual-entry time without an
  offset is stored as UTC, while file readers read the same time in the laboratory zone; a
  number written with a thousands separator ("1,234") is read as 1.234; the day-only fix in
  the interpretation evidence has no test under a database session west of UTC;
  `LAB_LOCAL_TIMEZONE` is not validated at startup.
- **The import looks names up in the catalog; a value keeps its number (go-live plan A2,
  2026-10-12):** ✅ `norm-2` (ADR-0004 §18). A name is looked up in the KPI catalog and the KPI
  recorded on the row. **What the import normalizes — and may publish without a human — is
  unchanged: norm-1's six names**, bound in code to their KPI and unit, and only while the
  catalog agrees. A value that is not normalized keeps its number and its reference bounds in
  the source's unit: the tables, the interpretation evidence and the report statement show it
  as written (they showed "—" and no interval), with its review status, and a position against
  the interval only once a clinician has published it. It stays out of change calculations. A
  number that reads two ways ("4.000", "1,250") is not read — also for the six names, where
  norm-1 read "4.000" as 4 — and a reference interval is held whole or not at all: an
  unreadable bound, or a pair with the lower bound above the upper, leaves none held. The
  review queue shows the bounds publishing puts into effect. The data export is format
  version 2 (bounds for values that are not normalized; plain decimals).
  - **What an independent review refused, and why it matters beyond this slice:** the first
    version normalized, and so published unseen, every KPI whose comparison policy is
    `method_aware` — 57 KPIs under 62 names, where norm-1 had six. An assistant, who may enter
    values and may not resolve the queue, could put a urine creatinine, a research assay or a
    body weight of 820 kg into a released report with no clinician having looked at the value.
    Which names publish unseen is a clinical decision per name (ADR-0004 §18); the next step
    is a signed import mode on `kpi_alias` and a specimen on the observation — not more aliases.
  - **What this does not do:** it adds no alias, no conversion and no unit notation. A German
    laboratory file sends every row but the six names to the review queue. Closing that needs
    the pilot laboratory's test list (plan item A1) and a named clinician's sign-off.
  - **Decisions:** (1) which names may publish unseen; (2) the six names themselves — nobody
    signed them either, and `glucose` is published as fasting plasma glucose whatever the
    specimen (a file's "Material" column and LDT fields 8428–8431 are not read); (3) the LOINC
    codes still stamped on new rows and exported — four mass-concentration terms on values held
    in mmol/L, none of them in the verified set; (4) whether "Referenzintervall der Quelle" may
    stand for an interval a person typed or a device reported (register row "Source
    reference-interval display"); (5) whether a change may be computed between two values of
    one KPI held in the same source unit (today: no — only between normalized values).
  - **Gaps:** a number that reads two ways has no way back to being a number — a clinician can
    publish or reject the value, not say which reading is meant; **a laboratory that writes
    three decimals** loses the number of every value of 1 or more ("1.250") and the interval
    beside it, until a reader states the decimal mark of its format (LDT defines one; CSV and
    manual entry do not); once published, such a value of one of the six names is skipped by
    later change calculations without a word; **the import depends on a seeded catalog and
    nothing seeds one in production** (ADR-0004 §18 — an error line in the log is all that
    says so); a value imported before `norm-2` without a normalized form has its number back
    (migration 0018) but not its bounds, and a stored row is never re-normalized — a row
    norm-1 normalized from "1.050 mg/dL" still stands as 1.05; a six-name value is not checked
    for plausibility (`LDL 820 mmol/L` publishes unseen, as before); a name typed with a tab
    or a line break is matched, and the statement repeats it as typed; migrations have to be
    run by a superuser or a role with BYPASSRLS (0018 refuses any other, also on an empty
    table); `reference_text` is still synthesized as
    "None-120 …" for a one-sided interval; a converted value and its bounds show every computed
    digit, and a statement restates a bound without its trailing zeros; the glucose factor has
    three significant digits; the web has no tests of its own; property-based tests for the
    conversions are still missing (the register claimed them); the clinician tables show the
    catalog code where no source code exists; the web ties a value to a domain's cited value
    by the catalog code first, so a stored value that has a source code and no catalog code
    is not listed beside a cited value that has both; a drafting provider other than the
    deterministic one would receive the source's unit text unfiltered (`EvidenceItem.unit`);
    nothing enforces that a stored alias is lower-case, and one that is not never resolves.
- **The clinic reads its own audit trail (go-live plan A9, 2026-10-12):** ✅ Einstellungen →
  Audit-Protokoll (owner): newest first, paged by a cursor, filtered by a closed set of areas,
  by day (on the clinic's wall clock) and by record; reads are shown unless the reader hides
  them. The read filters by tenant explicitly — row-level security also passes tenant-less
  events (sign-ins of every user), which are no clinic's. The response leaves out the request's
  correlation id, and the correlation id is now generated by the API and never taken from the
  caller: before, a caller without a session could write text of its choosing into any
  clinic's trail through the invitation surfaces (an id-shaped value still carries sixteen
  bytes of it), and a header longer than the column failed every audited request. The read is
  throttled (120 per minute, account and clinic) — every read writes an event.
  - **What the trail does not hold** (found in the independent review; points 1, 2, 3 and 5
    are stated on the page, and `tests/test_audit_read.py` holds point 1 and the vocabulary
    against the source): (1) reading a report
    (`GET /reports/{id}`) and the administrative lists (members, staff invitations, deletion
    requests, export history) write no event; (2) an event is filed under the record it was
    written for and carries no patient id of its own — report, document, import, review-item,
    invitation and deletion-request events are not found by a search for the patient record,
    and a refused export or import keeps the record id in `detail` only; (3) events without a
    tenant never reach a clinic: sign-in and sign-out, failed sign-ins, `rate_limited`,
    `csrf.denied`, and `authz.denied` before a clinic is selected or after a membership ended
    — a removed member's continued attempts are invisible to the owner; (4) `member.removed`
    and `staff_invite.redeemed` point at the membership, not at the person; (5) events of one
    request share a timestamp (`now()` is the transaction's start) and have no order among
    themselves, and an event committed after a page was read can be missed by a reader who
    pages on — an export of the trail must not be built on this cursor as it is; (6) the
    guard on `detail` is a set of top-level key names, not a schema.
  - **Still open:** no index for the query (measured in review: about 140 ms for the first
    page at 400 000 events of one clinic in one run straight after a bulk load, 17 ms warm at
    300 000 — it grows with the clinic's events; the keyset is a row-value comparison, so
    `(tenant_id, created_at DESC, id DESC)` will serve it: 0.07 ms with that index in review);
    no export of the trail; no retention rule; a caller who knows a clinic's id can still add
    refused entries to its trail (30 per minute and address on each of three surfaces, a
    closed reason code, nothing of the caller's), and a signed-in member's refused attempts
    are not throttled at all; a throttled read leaves a `rate_limited` event without tenant or
    actor, which tells nobody whose reading was throttled; not every refusal leaves an entry
    (a release without consent, a request for an unknown id); the page's time zone is a
    constant in the web (`lib/clinicTime.ts`) while the API reads its zone from a setting
    (`lab_local_timezone`) — one zone today, to be changed together; the
    "Letzte Aktivität" panel on the Übersicht stays gated — a feed for every role is a
    different decision than an owner's audit view.
  - **For the DPO, before real data:** the trail is a record of each colleague's activity
    (purpose limitation, retention, a works council where there is one); an account's name and
    e-mail stay attached to its entries after the member has left — a `users` row with audit
    events cannot be deleted at all (the foreign key's SET NULL is an UPDATE, which the
    append-only trigger refuses; the same holds for a `tenants` row); entries of an erased
    record keep its id (`docs/notes/0012`); OWNER-only means a sole owner is the only reader
    of their own actions; reads are shown by default, so a reader's own reading and every
    opened record push changes off the first page (hiding reads is one click) — which view is
    the default is a product decision.
  - **Before real data:** "no names in the trail" is held by review, a key-name guard and a
    suite-wide check after every test (`tests/conftest.py`) — not by a schema per action.
- **Security items that need no vendor (go-live plan B, 2026-10-12):** the RLS role guard
  holds now — every environment, at startup, and a refused engine is never kept
  ([[0005-rls-fail-open-production-guard]], which records what was wrong); sign-out removes
  both cookies with the attributes they were set with; report drafting is rate limited
  (30/min/user, generating and re-drafting together).
  Found on the way, not changed: (1) the web app stores the two cookies under fixed names
  (`hadp_session`, `hadp_csrf`) and without `Secure` (`apps/web/src/lib/api.ts`) — harmless
  while the only sign-in is the development one, which production does not have, but the
  production sign-in (OIDC) must not inherit it: the API's production names carry
  `__Host-`; (2) a failed security-event write is still an ERROR log line and nothing
  else (a 403 must not become a 500) — it needs an alert on that line once monitoring
  exists (workstream C); (3) no malware-scan step on upload, no nonce-based CSP.
  From the independent review of that slice, taken: the draft button shows the throttling
  message (it had its own error mapping); a limit records its first refusal per window, not
  every one (a hammering client wrote one append-only row per refused request, on a second
  pooled connection); a counter that lost its expiry is re-armed (it would have refused that
  user for good); a refused configuration no longer quotes the values it was given (the error
  text ended in the tail of a secret); one engine initialisation at a time; a test that every
  tenant table enables and forces RLS.
  From that review, open: the role guard does not refuse a table **owner**, and an unset
  `APP_DATABASE_URL` still falls back to the admin DSN ([[0005-rls-fail-open-production-guard]]);
  `rate_limited` events carry neither user nor clinic, so a breach cannot be tied to anyone and
  reaches no clinic's trail; editing a report has no size limit and no rate limit, and each
  edit of an approved or rejected version adds a version; a failed sign-out call is swallowed
  by the web app (the session then stays valid server-side until it expires); a 503 from the
  limiter is shown as the generic failure; uvicorn's own startup log does not pass the
  redaction filter. (The erasure function — SECURITY DEFINER, owned by the migrating superuser,
  with unqualified table names — had no `search_path` of its own, so a session of the
  application role could place a temporary table in front of a real one and have its code run
  as the owner: fixed by migration 0020, `tests/test_security_definer_functions.py`.)
- **Preparation-time metric (go-live plan A6, 2026-10-12): PART 1 — A6 stays open.**
  Einstellungen → Vorbereitungszeit holds the clinic's own statements (baseline, follow-ups;
  append-only) and one measured interval, draft to first standing approval
  (`draft-to-approval-1`); `docs/product/WORKFLOW.md` §6.4. **Not built: a measure that can be
  set against the baseline.** The interval starts at the draft, so it leaves out the work
  before it; a comparable measure needs a recorded "preparation started" moment, and which
  moment that is has to be decided first (founder).
  From the independent review, taken: the standing baseline is looked up on its own (a long
  history hid it); an approval that was refused no longer ends the interval; both routes are
  rate limited; integers are strict; the report-timing query lives in the reports module; a
  negative interval (two clocks) counts as zero; the page no longer calls the minimum of five a
  protection of persons.
  Still open: a double submit records twice (no idempotency key) and a lost answer is reported
  as "not confirmed"; no chart or history of the measured value; no export; fixed windows; the
  figure cannot be reproduced after an erasure; `elapsed()` and the page have no tests of their
  own (the web has no test runner); the form loses its input on a refused submission.
- **Patient-view Beta hardening**: per-page boundary note added; a fuller
  patient-appropriate presentation is gated for the real-data Beta.
