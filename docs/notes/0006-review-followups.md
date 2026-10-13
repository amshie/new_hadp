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
  the limits keyed on a client address (sign-in, the patient-view token surface, invitation
  redemption) counted the web server's address, which is the API's peer for every browser — all
  patients shared one budget, and one client could exhaust it for everyone (found by the review
  of the browser test; closed 2026-10-13, see the entry on address-keyed limits below);
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
- **Container images and a production-shaped stack (go-live plan C, 2026-10-13):** ✅ three
  images, a migrate step that seeds the KPI catalog, `make stack-smoke` (38 checks since the client-address check) and an image
  scan in CI — `infra/docker/README.md`. From the independent review, taken: production mode is
  the API image's default (it would have started in development mode, password-less sign-in
  live, if `APP_ENV` was forgotten); the seeding command no longer reports success on a stale
  catalog and refuses another release before it writes; unfixed scanner findings are shown.
  Still open: **nobody can sign in to a production-mode stack** (no identity provider), so the
  smoke proves boot and posture only; a catalog release cannot be replaced (no upgrade path) and
  the API does not check the catalog at start (ADR-0004 §18); base images are pinned by tag, not
  by digest, and `postgres:16-alpine` / `redis:7-alpine` float; the scanner downloads its
  database at run time, so a new advisory or an outage can turn an unrelated pull request red;
  the job runs on every pull request without a layer cache; the stack's object store is a test
  double that accepts any credentials; everything in workstream C that needs a vendor (TLS,
  managed PostgreSQL, backups and restore, a secret manager, a deploy job, monitoring, runbooks).
- **The address-keyed limits count the client (go-live plan §9.5 step 1, 2026-10-13):** ✅ the
  web server passes on the `X-Forwarded-For` it received on the four calls whose limit counts
  per address (sign-in, patient view, the two invitation redemptions); the API believes it only
  from a peer in `TRUSTED_PROXIES`, and only the entry `TRUSTED_PROXY_HOPS` from the right
  (`security/client_address.py`); anything else leaves the peer. With real client addresses the
  limit per address no longer bounds what a caller without a session writes into a clinic's
  trail (it had, by accident: everyone shared one budget), so the trail now takes 30 refusals
  per surface, clinic and minute and then one entry that says recording stops for that minute
  (`security/rate_limit.py::refusal_recording`, three new audit actions `…_denials_unrecorded`,
  named on the trail page). Verified by `tests/test_client_address.py`,
  `tests/test_refusal_recording.py` and end to end in both smokes (the web route smoke on the
  loopback address, the stack smoke between containers) — the passing-on and the trusted peer,
  that is; that uvicorn leaves the header alone is held by a source scan and by a second
  request in the web route smoke that the two rules count differently.
  From the independent review, taken: one address written with a mask is refused (it named the
  whole network around it); the smoke could not tell the API's rule from uvicorn's, now it can;
  the documents say what a hop count set too high does, and no longer call the production
  sign-in address-limited (it does not exist yet).
  Still open: **`TRUSTED_PROXIES` is empty by default and nothing refuses to start without it** —
  a deployment that forgets it keeps the shared budget (the API warns at start); the compose file
  of the production-shaped stack leaves it empty (Docker assigns the addresses; the smoke names
  the stack's own network for its run), and neither stack has a proxy in front of the web server
  — both smokes play that proxy themselves; the rule depends on the proxy in front of the web
  server setting or appending the header (a proxy that passes a client's own header through lets
  the client pick its counter); **a hop count set too high fails open** (the entry read is one
  the client wrote — to be fixed against the real ingress, a pen-test item); client addresses are
  the limiter's keys in Redis for 60 seconds and appear in no record of processing (before real
  data); a range given in two halves still holds every address; clients behind one NAT64 prefix
  share a budget; an address with a port is not read; a refusal for a clinic that does not exist
  still costs a failed insert and an ERROR log line per request (bounded per address only); the
  number of refusals after recording stopped is not on record; the web's part (four call sites)
  is held by a source scan and the smoke, not by a unit test (the web has no test runner).
- **Demo stack (2026-10-13):** `infra/docker/compose.demo.yml` + `scripts/demo_stack.sh` put
  HADP on one server behind a gate (TLS and a shared user name and password at a proxy), for
  showing the product on synthetic data; `scripts/smoke_demo.sh` runs in CI. It is the first
  stack with a real proxy in front of the web server: `TRUSTED_PROXIES` is the web server's one
  fixed address there, and the smoke checks that a visitor is counted under the address the
  proxy saw. `infra/docker/README.md` says what it is not.
  Still open: one shared gate password, no per-person access; the API runs in development mode
  there (the only sign-in that exists), so it must stay synthetic; uploaded files are lost on a
  restart (the object store is the test double — decision 14 of the go-live plan); the images
  are built on the server, not pulled from a registry; `caddy:2-alpine` floats; a public
  certificate is not part of any automated check (the smoke uses the proxy's own).
  **First server, 2026-10-13** (one rented machine, Ubuntu 26.04, 2 vCPU / 4 GB): the packages
  the README names exist there; both images built on it; `scripts/smoke_demo.sh` passed on it
  (20 checks) with those images; after `init` and `up` the proxy obtained a public certificate
  (Let's Encrypt) for a name of the form `<address>.sslip.io` within seconds, and from outside
  every path answers 401 without the gate and plain HTTP is sent to HTTPS. **Not confirmed in
  the repository:** a sign-in through the gate in a browser (the gate password is the
  operator's; the smoke does not make the form's own request). The provider's firewall was
  created but not attached to the server when this was written — closed ports answered from
  the server itself.
  From the independent review, taken: the gate's block is in the committed proxy configuration
  and nothing starts without a password hash (an import of an empty generated file would have
  been no gate); `up` creates the proxy again and waits for it; the project name is fixed in
  the script; the smoke covers every path and method, a foreign host name, a new gate password
  and the logs. Found by CI, not by the local run: the proxy could not read a gate file owned by
  another user (it has no capability for that) — the gate now reaches it through its
  environment. Open from that review: no lockout on the gate; visitors who arrive over IPv6
  share one limiter budget; the stack is open from the server itself; the role posture of the
  database is checked by the production-shaped smoke only; nothing tells visitors apart.
- **Interface language, German or English (2026-10-13): PARTS 1–3b of several; ADR-0007.** A person
  chooses under Einstellungen or on the sign-in page; the choice is a cookie on the device
  (`hadp_locale`), German without one (`apps/web/src/lib/i18n`: `messages/de.ts` is the source of
  the keys, `messages/en.ts` is typed against it; server components ask `getMessages()`, client
  components `useI18n()`, and only the chosen language reaches the browser).
  Done: both navigation shells (`VitaShell`, `AppShell`), sign-in with its two messages, the
  settings overview, the not-found page; `apps/web/e2e/language.spec.ts`, and browserless
  checks in `scripts/smoke_web.py`.
  Part 2: the overview (work list, report status, data coverage, review throughput, the two
  switched-off tiles and the two notes shown when throughput or coverage cannot be loaded) and
  the patients list with its loading placeholder. The wording with a value in it goes through
  `lib/i18n/fill.ts` (`fill`, `byCount`); the presenters of `lib/presenters/dashboard.ts` take
  the wording of the page's language and hand every row a `group` (review / approved /
  released / rejected / none) — the tabs and counts read that, no longer the German label.
  The five English names of where a report stands: "Approved", "Released" and "Rejected" are
  the words of the `ReportStatus` values; "In review" (the two draft values together) and "No
  draft" (a patient without a report) render "In Prüfung" and "Kein Entwurf". It is a workflow
  state; no closed vocabulary of the review is named on either page.
  **No number or date format changed**, so an English reader sees the German ones on the
  overview until that is decided (ADR-0007): the day-first dates under the throughput chart
  ("3.10."), the ISO dates of its table, the one-decimal average, the shares of the coverage.
  From the independent review of part 2, taken: the web smoke read the raw HTML of a page, and
  since part 1 the dictionary of the chosen language travels in a script of EVERY page — so
  "the page says X" could not fail (the synthetic banner and the disclaimer among them), and
  "a rejected version is not shown as signed" failed in CI the moment the German dictionary
  held the word. The smoke now reads a page's markup without its scripts (`shown`), and checks
  the two pages in both directions; the dialog to add a patient says itself that it is German
  (the wrapper at the call sites missed the dialog opened from the empty list); the browser
  test holds the five report states in English, the same tab counts in both languages and the
  rows of a tab; `fill` no longer takes a name every object has (`{constructor}`) for a value;
  three English entries that said more than the German, or "Ø", were made plain.
  Known and left: the language of headings and tabs is fixed when the layout renders, the
  wording from the presenters with each request — after a change of language in another tab, a
  link of the shell shows the two mixed until the page is loaded again (the tabs and counts do
  not depend on it). The overview's search also reads the assessment text as shown. And for
  an owner to read before outside readers do: "real observations", "real-data view" and "real
  timestamps" stand next to "synthetic sample data" on these pages, as "echte …" does in
  German (meant: read from the database, not mocked).
  Part 3a: the dialog to add a patient (its button on both pages, the three steps, the
  duplicate check, the invitation link) and what its server actions answer
  (`app/patients/actions.ts`: creating, the duplicate check, the invitation — in the language
  of the request). **The wording of the consent purposes is not translated** and is marked
  `lang="de"` inside the English dialog: `lib/consentCopy.ts` is versioned text (ADR-0007), and
  what a person consents to in the practice is the text that is recorded. Dates in the dialog
  keep the German form. One German sentence of the dialog changed: a patient one year old is
  "1 Jahr", no longer "1 Jahre" (and, as with every part, the sentence on the settings page
  that says what is done). The request to delete a record (same file) is used by the patient page
  only and stays German until that page is translated; until then the patient page marks the
  one message it shows from the invitation action with the interface language (`lang={locale}`)
  — the language the action answers in, unless the choice was changed in another tab since the
  page was loaded: then a server message arrives in the new language inside a page or dialog
  still rendered in the old one, until the page is loaded again (the class already recorded for
  part 2; an action that returned a code, with the wording chosen on the page, could not
  differ — to weigh for part 3b).
  **Found while reading the patient page for part 3b, and decisive for it:** that page shows
  the position against the reference interval and the comparability notes — closed
  vocabularies ADR-0007 named as German until the medical director has confirmed their
  English terms — and two more that ADR-0003 closes and ADR-0007 had not named: the six domain
  axes and follow-up adequacy (added to ADR-0007 and the register with this part). CIS,
  Actionability and the tri-state cells are NOT shown there (they are in the page's view, and
  rendered on the report review page only) — corrected: the first writing of this note, and
  of the pull request, said they were. The notes on how a shown value relates to the source's
  writing (converted, in the source's unit, as written) are sentences about the data, to be
  translated with the same care. Closed sets on that page whose English has no named owner yet:
  the reasons of a deletion request, and the state of a run on a domain card (reviewed /
  draft / no run). Part 3b therefore translates the page AROUND them (header and actions, data
  coverage, laboratory files, consent, data export, the invitation and deletion dialogs) and
  leaves those labels German and marked, until that confirmation is on record.
  Seen and not fixed here (chip filed): Escape in this dialog discards what was entered
  without asking — the shared `Dialog` calls the close handler of its first render; the Cancel
  button asks.
  Part 3b: the patient page — header and actions, data coverage, the consent card, the
  laboratory-files card, the data-export card, the audit steps, the dialogs (invitation,
  marker detail, deletion request, consent, data export) and what its server actions answer
  (deletion request, consent, laboratory upload and import with its twenty reasons for not
  reading a file).
  **German on that page whatever the choice, each marked `lang="de"`:** the names of the six
  domain axes, the line "Follow-up-Adäquanz: …", the position against the reference interval
  (pill, screen-reader sentence, the sentence in the marker dialog), the comparability note,
  the wording of the consent purposes — and a message of the report-draft action
  (`app/reports/actions.ts` belongs to the report pages, not translated yet). The headings of
  the two position columns and the sentence "position relative to the source reference
  interval" are English, in the words `lageCopy.ts` already holds; the VALUES are not.
  How it is built: `lib/presenters/review.ts` keeps its German wording for the report review
  page and additionally hands out keys and values (`ageYears`, an audit step's `key` and
  `subKey`, a source note's `source` and `unit`); the patient page words the report's state,
  the age, the audit steps, a value's review state and the three notes on how a value relates
  to the source's writing from the dictionary. So these few German strings have two sources
  until the review page is translated.
  English names given here to sets with a fixed list behind them, none clinical, none with a
  named owner yet: the report's state on this page (five), the state of a run on a domain
  card (reviewed / draft / no run), a value's review state (published / in review / rejected
  in review), the three reasons of a deletion request (GDPR's own English: data subject
  request, consent withdrawn, data minimisation), the twenty reasons a laboratory file is
  not read.
  One German sentence changed, as in the dialog: an age of one is "1 Jahr". Number and date
  formats are unchanged — the consent day, upload times, file sizes and "489 T" keep the
  German form inside English sentences. `scripts/smoke_web.py` checks the page in both
  directions and that a consent purpose and a domain name read the same in both;
  `e2e/fill.spec.ts` pins every German sentence that is put together.
  Known and left: an `aria-label` that names a domain ("Select domain Metabolisch") cannot
  mark the German word inside it; what a laboratory wrote (analyte names) and people's names
  carry no language mark of their own — the language of recorded content is not recorded.
  **Still German** (each marks its content `lang="de"`): review queue,
  interpretation, report review, the four settings sub-pages (members, deletion requests, the
  audit trail with its ~60 event labels, preparation time), the patient-facing pages, the
  colleague's onboarding page (`/team-einladung`), the error page, the disclaimer, the toasts,
  and every message a server action returns except those of sign-in, of the dialog to add a
  patient and of the patient page. All date and number
  formats are `de-DE`, written out in about twenty places. The settings page says what is done
  while that is true — widen that sentence (`language.progress`) with every part and remove it
  with the last page.
  From the independent review, taken: a page that is still German says so (the document's
  language followed the choice while the content did not — a screen reader would have read
  German with English sounds); the second shell is translated and the on-screen sentence says
  exactly what is done; only the chosen language is sent to the browser, and a component
  outside the provider fails instead of showing German; one `Locale` type; the role's name has
  one German source less; the tests use the one role whose name differs between the languages,
  both the scripted and the script-less submit, a link of the shell, and the cookie's
  attributes; the language can be chosen on the sign-in page.
  Decisions this raises (ADR-0007, register row): the English names of the closed vocabularies
  (CIS, Actionability, tri-state, rejection reasons) must be the doctrine's own terms and need
  the medical director's confirmation before the review pages are translated; whether numbers
  and dates follow the interface; consent wording is versioned text, not interface; whether the
  patient-facing pages follow a patient's language; the choice is per device, not per account.
  Known and left: the cookie is not renewed (after a year the interface is German again); a
  dark-theme reader's first paint shows the wrong icon of the theme switch for an instant
  (older than this change).
- **Patient-view Beta hardening**: per-page boundary note added; a fuller
  patient-appropriate presentation is gated for the real-data Beta.
