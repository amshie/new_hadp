# 0016 — Einstellungen

Status: part 1 implemented (synthetic Alpha). From the mockup the founder approved on
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

## Still to come

- Part 2: Team & Rollen (the members page as a table, an invitation dialog, open invitations,
  what each role may do).
- Part 3: the sections that do not exist yet — Profil, Sicherheit & Sitzungen, Praxisprofil,
  Datenquellen & Import, Einwilligungstexte, Aufbewahrung & Export. Each is added to the
  sub-navigation when it exists, not before.
