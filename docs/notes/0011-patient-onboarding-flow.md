# 0011 — Patient onboarding: guided wizard, duplicate probe, consent-at-create

Date: 2026-07-05 · Status: shipped (synthetic Alpha) · Register: row added ("Patient
onboarding wizard"), no clinical meaning touched.

The flat "+ Patient hinzufügen" form became a guided, validated, auditable onboarding
flow. This note records the contracts and the deliberate limits so later slices do not
re-litigate them.

## 1. Duplicate probe (`POST /api/v1/patients/duplicate-check`)

- **POST, not GET.** Identity details (name, date of birth, external ref) travel in the
  request body so they never appear in a query string, browser history, or access log —
  the same rule as the patient-view token (P-pre-3).
- **Conservative, documented heuristic — exact matches only, never fuzzy:**
  - `external_ref`: trimmed exact match (case-sensitive; refs are clinic identifiers) —
    **strong**.
  - `name_dob`: normalized name (lowercased, internal whitespace collapsed) equal AND
    date of birth present on both sides and equal — **strong**.
  - `name`: normalized name equal, DOB missing on either side or different — **weak**
    (surfaced, never blocking; same-name/different-person is routine in a clinic).
  - Deliberately NOT transliterated (Müller ≠ Mueller) and NOT similarity-scored: an
    over-eager matcher trains staff to click through the warning.
- Matching runs in Python over the tenant's rows so input and column share one
  normalization code path (no SQL/Python casing drift). Fine at Alpha scale — the
  directory endpoint already loads the same rows. Revisit with an indexed normalized
  column if tenants outgrow this.
- **Tenant isolation:** explicit `tenant_id` filter + RLS; a cross-tenant twin is
  invisible and never blocks creation (covered by
  `tests/test_patient_onboarding.py::test_duplicate_check_never_crosses_tenants`).
- Audited as `patient.duplicate_check` with `{"candidates": n}` only — the audit
  service's forbidden-key guard rejects names outright.
- Requires `Action.PATIENT_READ` (it reveals patient identity rows); creation keeps
  `Action.PATIENT_CREATE`.

## 2. Duplicate guard on create (`allow_duplicate`)

- `POST /api/v1/patients` re-runs the probe server-side. A **strong** candidate without
  `allow_duplicate=true` → **409 `duplicate_patient`** (new `AppError` subclass) and the
  transaction rolls back. The UI surfaces the candidates and requires an explicit
  "Trotzdem neu anlegen — es handelt sich um eine andere Person." confirmation before it
  ever sends the flag. A duplicate can be created deliberately, never silently — for
  every API client, not only the wizard.
- No unique constraint exists (names are not unique). Two concurrent creates can still
  race past the probe; the guard narrows the window, the UI resolves the rest (a 409 at
  submit refreshes the candidate list and asks again).

## 3. Consent at onboarding

- Optional `consents: [{purpose, channel}]` on the create request, recorded **in the
  same transaction** via the existing `consents_service.record_consent` (append-only
  `consent_events`, `recorded_by_user_id` = creating staff member, channel `in_person`),
  each grant audited `consent.granted` with the purpose only. Repeated purposes in one
  request are rejected (422).
- Purposes stay the **existing closed vocabulary** (`report_release`,
  `data_source_connect`, `analytics`). No "data processing"/"communication" purposes were
  invented: the lawful purpose taxonomy is a pending DPO/counsel deliverable, and a new
  enum value would also require a CHECK-constraint migration (0014). The wizard presents
  the three purposes as explicit opt-ins (nothing preselected) and labels them as the
  Pilotumgebung's placeholder catalogue.
- The patient-side path is unchanged: invitation redeem still records the
  `report_release` grant itself (docs/notes/0010). The wizard's success step offers the
  existing one-time invitation link for exactly that.

## 4. Input plausibility (system boundary)

- `date_of_birth`: not in the future, year ≥ 1900 — enforced in the API request model
  (422) and mirrored client-side with German inline messages. `display_name` is trimmed
  and must be non-blank; length caps match the columns (200/120).

## 5. Deliberately NOT in this slice

- **No contact fields (email/phone), referring physician, or intake notes.** The
  `patients` table has no such columns; adding them is an additive migration **and** a
  product/data-minimization decision (GDPR Art. 5(1)(c) — the Alpha has no consumer for
  contact data: invitations are shared manually out-of-band). Gate: founder decision +
  DPO input, then a follow-up slice.
- No fuzzy/phonetic duplicate matching, no merge tooling (surfacing + explicit override
  only), no Idempotency-Key on create (pre-existing gap, shared with invitations).

## 6. Web notes

- The wizard lives in `apps/web/src/components/vitabahn/AddPatientDialog.tsx` (same
  export/trigger contract; also used on `/overview`). Draft state is React-only — no
  client-side persistence beyond the session; closing with entered data asks before
  discarding. The form is `noValidate`: the wizard owns validation so messages are the
  styled German ones, while `required`/`min`/`max` attributes stay for semantics.
- `/patients` gained a route-level `loading.tsx` skeleton and a true-empty state
  (tenant has zero patients → onboarding CTA) distinct from the filtered-empty message.
