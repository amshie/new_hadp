# 0021 — One of each

Status: implemented (synthetic Alpha). The seventh of the design review's priorities
(2026-10-14): three settings pages headed themselves with a bare 22px `h1`, the audit stepper
was drawn twice (one way on the patient page, another on the report page), every list wrote
its own "nothing here", and five components each held a copy of the card's style.

## What changed

- **One page header.** Audit-Protokoll, Vorbereitungszeit and Löschanträge, and the reserved
  states of those and of Team & Rollen, head themselves like every other settings page: the group's name as eyebrow
  (`sectionEyebrow`, from `lib/settingsSections`), the title as `.vb-ov-h1`, the lead as
  `.vb-ov-lead`. Patientinnen und Patienten and the Review-Queue use the same classes in the
  page head (`.vb-ov-pagehead`).
- **One stepper.** `components/vitabahn/AuditSteps` (`.vb-audit-steps`) renders the
  presenter's audit steps (`lib/presenters/review`) on the patient page and on the report
  page: an ordered list, the active step marked `aria-current="step"`, a check for a done
  step, the step's line in the page's language; it scrolls sideways on a phone. The report
  page's `.audit-*` rules left `hadp.css`.
- **One empty state.** `components/vitabahn/EmptyState` (`.vb-empty`): a title where the
  page has one and a line that says why. Centred for a list that is the page (patients,
  review queue, audit, deletion requests, the worklist), `quiet` inside a card (a domain's
  table, a tier, the pending invitations, the consents, the activity feed). The two older
  classes (`.vb-ov-wlempty`, `.vb-ov-tier-empty`) are gone.
- **Classes, not constants.** `cardStyle` is `.vb-ov-card` in nine components, dialogs
  included (`dialogClassName`). The domain panel's `heading`, `note`, `chip`, `warnChip` and
  `colLabel` are `.vb-ov-h2`, `.vb-ov-note`, `.vb-ov-tag`, `.vb-ov-tag-now` and the new
  `.vb-collabel`.

## The guard

`apps/web/e2e/patterns.spec.ts` reads the sources and holds that every settings page's `h1`
carries `.vb-ov-h1`, that no component defines a `cardStyle`, and that stepper and
empty-state markup live only in their components. Pure, like the token test (0020).
