# 0016 — Einstellungen

Status: parts 1, 2 and 3 implemented (synthetic Alpha). From the mockup the founder approved on
2026-10-14, with all of its options.

## Part 1: the frame, language and appearance, the state of each section

- **A sub-navigation in three groups** — Persönlich, Praxis, Governance — beside every settings
  page (`apps/web/src/app/einstellungen/SettingsFrame.tsx`). Before, each section was a card that
  led to a page with no way back but the breadcrumb.
- **Locked, not hidden.** A section the reader's role may not open is listed with a lock and the
  roles it is for ("Nur für Inhaber und Ärztliche Leitung"); it is not a link. The list of
  sections and who may open them is one table (`apps/web/src/lib/settingsSections.ts`). It is
  navigation only: every page and every API route authorizes on its own.
- **Sprache & Darstellung** as rows: the interface language (the existing server action),
  the appearance (light, dark, or as the device's system is set — kept on the device; the
  topbar's switch stays an explicit light or dark), how numbers and dates are written, and the
  state of the translation behind a disclosure.
- **"Alle Bereiche"**: one card per section with what it holds now — members and open
  invitations, whether the baseline is recorded and the measured median, open deletion
  requests, denied accesses in the last 7 days. Each state is read only for a role that may
  open the section; a read the role may not make would be refused and recorded as a denied
  access. The preparation-time and audit states are themselves audited reads, as on their pages.

## Part 2: Team & Rollen

- **Members as a table**: person (name, e-mail, "Sie" for oneself), role, when they last acted,
  and a "⋯" button with "Im Protokoll anzeigen" (the audit trail filtered to that person — the
  audit page gained an `actor` filter) and "Aus dem Team entfernen …". One's own row has no
  actions. Changing a role and removing a member ask first; the API records both, as before.
- **Zuletzt aktiv** is the date of the member's latest event in this clinic's trail (any event,
  reads too; `last_active_at` on `GET /api/v1/members`). The owner reads the trail itself; this
  is its latest date per person, nothing more.
- **Inviting** is a dialog: whom the link is for (optional), the role, then the link — shown
  once, as before. The note of whom it is for is a new column (`staff_invitations.label`,
  migration 0021): at most 200 characters, shown to owners only, never sent anywhere and never in
  an audit event. It is the only personal data the dialog adds, and it is optional.
- **Offene Einladungen** with who created the link and when, its expiry, and "Widerrufen" (asks
  first).
- **Was eine Rolle darf**: the authorization matrix itself (`GET /api/v1/roles`, owners; the
  matrix of `auth/authz.py`, not restated). The page groups its actions into lines a clinic reads
  (`apps/web/src/lib/roleCapabilities.ts`); the API's tests hold that every action is in exactly
  one line and that each line's actions are granted to the same roles.

Not taken from the mockup: a status column and invited people as rows of the members table.
An open invitation stands in its own list with its details and its one action; the members
table lists members.

## Part 3: the sections that did not exist

Each section joined the sub-navigation when it existed. What is in place is shown as it is;
what is not is said plainly.

- **Profil** (every role): name, e-mail address, role and clinic, and the clinics the person
  belongs to. Read only: name and address come from the sign-in.
- **Sicherheit & Sitzungen** (every role, own account): how the platform signs people in
  (`dev` or `oidc`), what that means for a second factor, the latest ten sessions — start,
  state, end, the clinic last chosen; no device and no address, because none is recorded — and
  "Alle anderen Sitzungen beenden" (asks first; `POST /auth/sessions/end-others`, recorded
  without a clinic as `auth.sessions_ended`, like signing in and out). The page claims nothing
  about a second factor it cannot see.
- **Praxisprofil** (every role reads; the owner changes — new actions `TENANT_PROFILE_READ` and
  `TENANT_PROFILE_EDIT`): the clinic's name and an optional address (`tenants.address`,
  migration 0022, at most 300 characters), and the laboratory time zone, which is a platform
  setting shown, not changed. A change is recorded with the names of the fields that changed,
  never their values. The address appears beneath the released report in the patient view
  ("Freigegeben von …"), so a patient knows which practice released it. No logo: the pilot
  accepts no images.
- **Datenquellen & Import** (every role): the three laboratory file readers, when each was last
  used here, values entered by hand or through the API, and what happens after a file is read
  in — stored unchanged, unambiguous values published, every other value held for a clinician
  (the import's own review reasons), originals kept. PDF reports are not read; wearables are not
  connected in pilot phase 1. Nothing is configured here yet.
- **Einwilligungstexte** (every role): the consent purposes with their wording (German, as
  recorded), the text version a consent recorded now refers to, and how many consents the
  clinic recorded and withdrawn per purpose and version (`GET /consent-texts`, counts only,
  audited). The wording is a placeholder of the pilot; the final texts are the data protection
  advisers' and arrive as a new version, never as an edit.
- **Aufbewahrung & Export** (owner): retention periods — no policy yet, and the platform
  deletes nothing on its own; the data export per patient (Art. 15/20); deletion by two-person
  approval with its open and executed requests; backup and restore — not set up in the pilot,
  and a condition before real patient data (Milestone 5).

## For the data protection officer and the Regulatory Lead

- Einwilligungstexte and Aufbewahrung & Export state where the clinic stands without deciding
  anything: the consent wording, the retention periods and the backup obligation are theirs to
  set. The pages say so.
- The clinic's address under a released report is the only change to what a patient sees. It
  is the clinic's own data, not clinical content.
