# 0019 — Form controls and phones

Status: implemented (synthetic Alpha). The fourth of the design review's priorities
(2026-10-14): the browser's own form controls and two pages that did not fit a phone.

## Form controls

- **One class, `vb-control`** (`styles/vitabahn.css`): every select, date and number field in
  the dashboard is 36px high, on the tokens, with the same border, focus ring and, for a
  select, the same chevron (the native menu stays; only the closed control is ours). Dark
  follows the theme, `color-scheme` included, so a date picker is dark on a dark page. Used
  by the audit filters, the preparation-time form, the deletion-request reason, the
  interpretation form (its 54 fields) and, through their own classes, the role selects of
  Team & Rollen. The inline style objects those pages carried for this are gone.
- **A file field is a button** (`vb-file`): the native control's wording ("Choose File / No
  file chosen") is the browser's and follows neither language nor theme. The input is kept,
  visually hidden, for the keyboard and the file dialog; the page shows its own button
  ("Labordatei wählen") and the chosen file's name, or "Keine Datei gewählt".
- A date field's placeholder (`tt.mm.jjjj` or `mm/dd/yyyy`) is the browser's, from its own
  locale, not the page's; a German browser shows the German order. Not changed.

## Phones

- **Team & Rollen** overflowed the page by 187px at 390px: the members table and the role
  matrix now scroll inside their card (`vb-team-scroll`), and the matrix's first column stays
  in view while the role columns scroll. The "Inhaber" column and the "⋯" buttons are
  reachable again.
- **Übersicht**: the stat "Freigegeben · 30 T" kept its number and unit on one line.
- **Guard**: `apps/web/e2e/layout.spec.ts` opens every page of the demo clinic at 390px and
  fails when the document is wider than the viewport. A table may scroll in its card; the page
  may not.
