# 0020 — Contrast

Status: implemented (synthetic Alpha). The sixth of the design review's priorities
(2026-10-14): the faintest text in the dashboard read at 3.07:1 on white, and four status
colours were used as words at 2.2–3.0:1. WCAG 2.2 AA asks 4.5:1 for text.

## What changed

- **Text tokens** (`styles/tokens.css`): `--text-muted` and `--text-faint` hold 4.5:1 on
  the card, the page and the sunken surface of their theme — light (#5a6b70, #5f7075) and
  dark (slate-400, #808f94). The slate steps stay what they are; they colour borders, icons
  and tracks, not words.
- **Status colours as words**: `--status-positive-text`, `--status-warning-text`,
  `--status-danger-text`, `--status-info-text`, one per theme, hold 4.5:1 on the same
  surfaces. A status colour (`--status-warning`, `--amber-500`, `--rose-500`, `--sky-400`,
  `--vital-*`) tints a dot, a bar, a border or a background; text in that colour takes the
  text token. Changed where it was text: the "wartet auf Sie" and "neue Werte" tags, the
  draft badge, the markers outside their interval on the patient page, the team page's
  errors and its "remove" menu entry, the sign-in's error notice.
- **No type under 11px**: 38 declarations at 9–10.5px (uppercase mono labels, table heads,
  meta lines, the mark's sub-line) are 11px. The scale's smallest step is `--text-2xs`
  (11px).

## The guard

`apps/web/e2e/tokens.spec.ts` parses `tokens.css` and holds, per theme, every text token
against every surface at 4.5:1, the button's text against the brand colour, and that no
stylesheet or component of the app sets a size under 11px. It renders nothing, so it runs
in a second; a token that drifts fails it before a page does.
