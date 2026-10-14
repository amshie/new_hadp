# 0017 — One identity: the pages without a signed-in person

Status: implemented (synthetic Alpha). The first of the design review's priorities
(2026-10-14): the sign-in, a patient's report, the two invitations and the 404 were on the
pre-ADR-0005 stylesheet with a second logo; the dashboard was on VitaBahn. One product, one
look.

## What changed

- **One mark.** `apps/web/src/components/vitabahn/BrandMark.tsx` is the teal tile with the
  check and the wordmark; the sidebar, the sign-in and every public page use it. The old
  `.brand` / `.auth-*` rules and their gold-dot mark are gone from `styles/hadp.css`.
- **One scope.** `PublicScope` (`components/vitabahn/PublicScope.tsx`) wraps the pages that
  have no signed-in person in `.vb-scope` with the same tokens as the dashboard. Nobody has
  chosen a theme there, so they follow the device's setting (`prefers-color-scheme`); the
  server renders light and the client switches on hydration, as the dashboard does with its
  stored choice.
- **Sign-in** (`app/login`): the same layout as before (brand panel, card), on the dashboard's
  type, colours and buttons (`.vb-auth-*` in `styles/vitabahn.css`). Light and dark.
- **A patient's report** (`app/patient-view`): the practice that released it as the eyebrow,
  "Ihr Bericht", the day of release, the introduction; then **Ihre Werte** — one row per
  measurement the released statements cite, as the source wrote it (name, value and unit,
  the source's reference text, the day of sampling) — and the statements as the clinician
  approved them; then who released it, the four-part disclaimer, the mark. The table is new
  data on the page: `values` on `POST /api/v1/patient-view`
  (`modules/reports/service.py::_patient_view_values`), the cited observations' source
  fields verbatim, deduplicated, in citation order. Nothing is derived: a statement's own
  text already quotes these numbers; the table lines them up.
- **Invitations and the 404** (`app/einladung`, `app/team-einladung`, `app/not-found.tsx`):
  the same card, fields, buttons and disclaimer (`.vb-pub-*`).

## Boundary

The patient sees exactly what the released version says: the statements, and the source
values those statements cite, with the source's own reference text. No position relative to
the interval, no change, no colour — those stay in the clinic's view, where a clinician
reads them with the observation beside them. Showing a measured value with its provenance
is within the intended use (`docs/regulatory/INTENDED_USE.md`).
