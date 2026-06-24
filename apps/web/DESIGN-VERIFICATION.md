# Design verification — real frontend vs. HADP-UI-Optimiert-v2 previews

Method: render the build with Playwright (Chromium, deviceScaleFactor 1) at the prototype's
exact widths (desktop 1440px, mobile 390px), full-page, and compare side-by-side with
`HADP-UI-Optimiert-v2/previews/*.png`. Shots are written to `apps/web/.shots/`.

Re-capture: `node apps/web/scripts/screenshot.mjs '<json shots>'` with the web dev server up.

> Note: the small Next.js dev-tools indicator ("N") in the bottom-left of dev screenshots
> is a development overlay, not part of the design; it does not appear in `next build` output.

## Tokens (FE-1)

- [x] `:root` token block lifted verbatim into `src/styles/tokens.css` (brand/ink/surface/status/radius/shadow/layout).
- [x] Recurring component color literals tokenized as derived tokens (identical values) in the ported `src/styles/hadp.css`; audit shows only intentional decorative one-offs remain inline (dark-panel gradient stops, sidebar/auth text colors, `#d4b672` dark-panel gold, auth bg).
- [x] Inter loaded via `next/font` (`--font-inter`), wired into `--font-sans`. Type in shots matches previews (not a system fallback).

## Login + session states (FE-3) — MATCHES

Evidence: `.shots/auth-desktop.png`, `.shots/auth-mobile.png`, `.shots/auth-2fa.png`, `.shots/auth-locked.png`, `.shots/auth-signedout.png`.

- [x] Desktop split layout matches `auth-desktop.png` (teal brand panel + card).
- [x] Mobile stacked layout matches `auth-mobile.png` (brand on top, trust items 1-col, card below).
- [x] All four states render per design: signin, twofactor (6 code boxes), locked, signedout.
- [x] Password toggle (Anzeigen/Ausblenden) with `aria-pressed`.
- [x] 6-digit code inputs: digit-only, auto-advance, Backspace-back, Arrow nav, paste-fill.
- [x] Verbatim cautious/compliance copy preserved (zweckgebunden/protokolliert, EU-Datenresidenz, synthetic framing).
- [x] Wired to API: 2FA "Bestätigen und anmelden" → `dev-login` + select first tenant → `/worklist` (seed adds `s.johnson@meridian-health.eu` so the prototype email logs in for real).
- [x] skip-link, ARIA labels, `:focus-visible` rings, reduced-motion (from ported CSS).
- Deviation: real auth uses a session cookie + dev provider (no real OTP); the 2FA step is the prototype's UX and accepts any 6 digits in dev, exactly as the prototype states.

## AppShell (FE-2) — MATCHES (verified via worklist + review)

- [x] Sidebar: brand, Arbeitsbereich/Verwaltung nav groups with counts (3, 2) and active state, Pilotumgebung synthetic-data card, user block.
- [x] Topbar: mobile-brand (shown < 920px), breadcrumbs, clinic-switch, notifications, user-menu (open/Escape/outside-click).
- [x] skip-link + `#main-content`; sticky sidebar/topbar; content max-width 1260px.

## Worklist (FE-4) — MATCHES

Evidence: `.shots/worklist-desktop.png`, `.shots/worklist-mobile.png`.

- [x] Desktop matches `worklist-desktop.png` (page header, 4 stat cards, filter tabs + search, table, activity + data-quality cards).
- [x] Mobile matches `worklist-mobile.png` (worklist rows → labeled cards, stats stack, tabs scroll horizontally).
- [x] Filter tabs (`aria-selected`) + search filter the rows; empty-state when none.
- [x] Row click and keyboard (Enter/Space) open the synthetic review for open rows; closed rows toast.
- [x] Verbatim copy: "keine automatische Diagnose oder Therapieempfehlung", Datenqualität, "quellengebunden, nicht freigegeben".
- Wiring note: rows come from the typed synthetic module (mirrors the preview); they map to a future worklist/assessments API. Open rows route to the one implemented synthetic assessment (Amelia Hart #2), as in the prototype.

## Patient assessment review (FE-5) — MATCHES

Evidence: `.shots/review-desktop.png`, `.shots/review-mobile.png`, `.shots/review-dialog.png`, `.shots/review-signed.png`.

- [x] Desktop matches `patient-review-desktop.png` (patient heading + badge, review tabs, draft banner, overview = summary/coverage-ring/checklist, domain table, evidence summary + sparkline + marker table, audit steps, action bar).
- [x] Mobile matches `patient-review-mobile.png` (domain table → cards with Herz-Kreislauf selected; marker table horizontally scrollable; overview stacks).
- [x] Domain selection (click + Enter/Space) updates evidence: title, badges, generated draft, source links, data-quality sparkline, marker table. Default selection = Herz-Kreislauf.
- [x] Signature dialog: opens from "Review signieren", closes on backdrop/Escape/X/Abbrechen, confirm disabled until checkbox; on sign → audit advances (Klinischer Review → "Signiert" ✓, Ärztliche Freigabe → "In Prüfung"), header badge → "An ärztliche Prüfung weitergeleitet", button → "Review signiert" (disabled), success toast.
- [x] Clinician approval gate preserved: signing forwards to physician review and does NOT release to the patient ("veröffentlicht den Bericht noch nicht an die Patientin").
- [x] Raw observations / derived values / generated narrative are SEPARATE types (`RawObservation` with per-observation `source` provenance, `DerivedChange`/`DerivedTrend`/`DerivedRules`, `GeneratedNarrative`).
- [x] Verbatim copy: "Quellengebundener Entwurf" + "Nicht freigegeben", "Systementwurf – nicht freigegeben", "Datenabdeckung", "Deterministische Zusammenfassung".
- Wiring note: review content is the typed synthetic assessment (mirrors the preview). The signature interaction mirrors the prototype (advances the audit UI); binding it to the live report approve/release endpoints is the next slice once a real assessment id flows from the worklist.

## Quality gates

- [x] `tsc --noEmit` clean (web + api-client). `next build` succeeds (all 6 routes compile).
- [x] Prettier clean across the repo.
- [x] Real login wiring verified: `POST /api/v1/auth/dev-login {s.johnson@meridian-health.eu}` → 200 (seeded persona).

## §5 — Wired to the real backend (ADR-0002)
Evidence: `.shots/worklist-live-{desktop,mobile}.png`, `.shots/review-live-{desktop,mobile}.png`
(captured by `scripts/shoot-live.mjs`, which performs the real UI login first).
- [x] Login flow wired end-to-end: UI login (dev-login + 2FA) → session cookie → `/worklist`;
      `app/login/actions.ts` no longer swallows failures (returns an error toast); pages map
      `ApiError` 401/403 → redirect `/login` (verified: `/worklist` without session → 307).
- [x] Worklist reads `GET /api/v1/worklist` (tenant-scoped). Real row renders (Synthetic
      Patient One, "Bericht · v1", live status badge, real "vor 2 h"); stats + tab counts are
      live; gated columns (Aufmerksamkeit, Datenqualität) show "—". Mobile card transform
      survives real data.
- [x] Review reads `GET /patients/{id}` + `GET /reports/{id}` + `GET /patients/{id}/observations`.
      Real source-grounded draft statements with evidence chips; real marker table; audit steps
      derived from the real report status; UUID-guarded params (bad id → notFound).
- [x] Raw / derived / generated-narrative kept separate through the API + presenter; the API
      returns structured fields (value/unit/reference/delta), the frontend formats (de-DE).
- [x] `lib/synthetic.ts` deleted (nothing imports it).
- [x] Negative tests (api) green: `test_worklist.py` — worklist tenant-scoped (tenant B sees
      none of A), worklist requires auth (401), cross-tenant `GET /patients/{id}` → 404.
- [x] Approval gate already enforced + tested server-side (`test_report_invariants.py`):
      approve without complete evidence refused; release before approval refused.
- [x] Gates honored (NOT built): domain rollup / data-quality (G1) render an explicit gated
      notice; the review signature stays UI-only with a G2 note (no lifecycle write yet).
- [x] `next build` clean: worklist + review are now `ƒ` (dynamic). 49 api tests pass.
- Deviation from preview (intended): worklist Aufmerksamkeit/Datenqualität columns + the
  review's six-domain rollup/coverage are empty/gated, so those areas no longer pixel-match
  the prototype previews — by design, pending G1.
