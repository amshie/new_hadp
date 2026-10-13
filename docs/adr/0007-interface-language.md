# ADR-0007: Interface language — German or English, chosen by the person

- Status: **Accepted** — founder request, 2026-10-13 ("in English or German; the change is made
  under Einstellungen, where the physician or user chooses between the two").
- Decides: how the web interface is offered in more than one language, what "language" covers
  and what it does not, and the rules the remaining pages are translated by.
- Relates: ADR-0003 (the closed vocabularies and their terms), ADR-0004 §0 ("DE/EN labels
  through the language scan before any UI ships") and its catalog of English names,
  [CLASSIFICATION_REGISTER](../regulatory/CLASSIFICATION_REGISTER.md) (row "Interface language"),
  `docs/notes/0006-review-followups.md` (what is done, page by page).

## Context

All interface wording was written in German inside the components (55 of 75 source files), and
some of it in places of its own (`auditCopy.ts`, `lageCopy.ts`, `comparabilityCopy.ts`,
`consentCopy.ts`). The pilot's clinics work in German; partners and reviewers who are shown the
product do not all read it.

## Decision

1. **Two languages, German the default.** `de` and `en` (`apps/web/src/lib/i18n/locales.ts`).
   A device without a choice gets German.
2. **The person chooses, per device.** Under Einstellungen, and on the sign-in page (an English
   reader's first screen). The choice is a cookie (`hadp_locale`, one year, `HttpOnly`,
   `SameSite=Lax`): no account setting, no database column, nothing recorded. It holds no secret
   and decides nothing but wording; a value that names no offered language counts as no choice.
   Two people who share a browser share the choice.
3. **No translation library.** `messages/de.ts` is the source of the keys; `messages/en.ts` is
   typed against it, so a missing or an extra key does not compile. Server components and
   server actions ask `getMessages()`; the root layout hands the wording of the chosen language
   to `I18nProvider`, and client components ask `useI18n()`. Only the chosen language reaches
   the browser. A component outside the provider fails — it does not fall back to German.
4. **Wording with a value in it** is a string with named places (`"{count} Einträge"`) filled by
   one helper, and a plural is two keys chosen by the code. Messages stay strings: the type
   that holds the two languages together cannot check a function. (The helper comes with the
   first page that needs it.)
5. **Interface, not content.** What was recorded stays in the language it was recorded in:
   report statements, the names a laboratory wrote, the names of people. A report approved in
   German is a German report whatever the reader's interface shows.
6. **A page says which language it is in.** `<html lang>` follows the choice. A page that is not
   translated yet marks its content `lang="de"` (the shells do it unless told `translated`), and
   recorded content will keep its own `lang` when the page around it is translated.
7. **The same intended-use rules for both languages.** The web copy scan
   (`apps/api/tests/test_web_copy_language.py`) reads the dictionaries; English uses the
   project's own English terms where they exist ("source-grounded", "two-person approval").

## What is NOT decided here, and needs its owner before the pages that touch it

- **The English names of the closed vocabularies** — CIS, Actionability, the tri-state cells,
  rejection reasons, comparability notes, position against a reference interval. They carry
  clinical meaning in any language: the doctrine's own terms (ADR-0003), the catalog's English
  names (ADR-0004) and the pairs that `lageCopy.ts` / `comparabilityCopy.ts` already hold are
  the terms to use, confirmed by the medical director. Not a fresh translation.
- **Numbers and dates.** A decimal comma against a decimal point is on the project's list of
  high-risk cases. Whether a value's FORMAT follows the reader's interface is a decision of its
  own, with a register line — until then every number and date stays as it is shown today.
- **Consent wording** is versioned text written by counsel (`consentCopy.ts`,
  `consent_text_version`): an English rendering is a new text version, not an interface
  translation.
- **The patient-facing pages** (the released report, the invitation): whose language they
  follow — the device's, or one the clinic records for the patient.
- **Generating reports in another language** is a product decision about content, outside this
  record.

## Consequences

- Until the last page is translated the interface is mixed for someone who chose English; the
  settings page says which parts are done, and that sentence is kept true with every part.
- Tests that pin German wording by file (`apps/api/tests/test_audit_read.py` reads
  `auditCopy.ts` and a sentence of the audit page) have to move with the wording when those
  pages are translated, and the English needs the same guard.
- Role names still have a second German source (`MitgliederContent.tsx`) until that page is
  translated.
