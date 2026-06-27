# ADR-0006: VitaBahn dashboard — governed real-data path

- Status: **Accepted** — founder decision, 2026-06-27.
- Decides: migrating the three VitaBahn screens (`/overview`, `/patients`, `/patients/[id]`)
  off the hardcoded synthetic module (`lib/demo/dashboard.ts`) onto the **governed real-data
  path**, and how each contested surface from [ADR-0005](0005-dashboard-product-surfaces.md)
  resolves once it must read real API data.
- Relates: ADR-0005 (the contested surfaces), ADR-0003 (governance doctrine), ADR-0002 §6 /
  Gate G1 (domain rollup & data-quality coverage intentionally absent). Touches the
  [CLASSIFICATION_REGISTER](../regulatory/CLASSIFICATION_REGISTER.md).

## Context

ADR-0005 shipped the three screens as a client-side **synthetic** demo. The founder directed a
rebuild onto the governed path: **server-side API load via `page.tsx`, authenticated principal +
active tenant, deny-by-default, tenant isolation / RLS, presenters over real API responses** — no
direct demo-data imports. A pre-build API/schema map (5-agent workflow) established exactly what
the real `/api/v1` surface provides.

**Two realities shaped the result, both surfaced to the founder before building:**

1. **Synthetic-data-only stays mechanically enforced** (ADR-0003 retained invariant). So
   "real-data path" means the **governed production architecture**, exercised on the existing
   **synthetic seed** data. Admitting real patients stays BLOCKED behind the pre-existing human
   gates (MDR/SaMD, DPIA/ROPA, AVV/TOMs + §203, production OIDC, pen-test, EU residency). When
   those clear, the _same_ path serves real patients with no rearchitecting.
2. **The contested surfaces have no compliant real source.** The API exposes patient identity,
   worklist/report status, the observation timeline (value + lab `reference_low/high` +
   review_status + deltas + KPI/domain codes), and the full interpretation matrix (CIS +
   Actionability + adequacy + tri-state). It exposes **no** data-quality engine, **no** patient
   risk field, **no** observation normal/abnormal verdict, and **no** throughput/activity/imports
   read endpoints.

## Decision

1. **Migrate to the governed path.** Each screen is a server component that loads tenant-scoped
   data through `api.ts`, redirects to `/login` on `ApiError 401/403`, `notFound()` on 404, and
   UUID-guards the `[id]` segment — mirroring the existing assessment-review page. The Detail screen
   **reuses `presentReview`** (the authoritative interpretation + observation + report mapping).
   `lib/demo/dashboard.ts` is deleted.

2. **Contested-surface resolution in the governed path:**

   - **Data-quality %** → a **real, deterministic data-completeness stat** ("Datenlage": observation
     count, % published, % with a lab reference interval, freshness of the latest), computed over
     the real timeline on the Detail screen — labeled data-completeness, **not** clinical quality.
     The tenant-wide gauge / Ø are **gated** (no coverage engine — Gate G1). No fabricated 94 %.
   - **Normal / Grenzwertig / Auffällig** → replaced by the **compliant positional Lage**
     (Über/Unter Referenz · Im Intervall · Keine Referenz) via `referencePosition` over the lab
     `reference_low/high`. Real, verdict-free, register-approved. A real normal/abnormal **verdict**
     has no source and crosses the MDR boundary — **not** implemented as real.
   - **Patient Risiko (Hoch/Mittel/Niedrig)** → kept **visible** as a directory column (honoring the
     founder's acceptance of the surface) but **honestly gated** ("n. v."), never fabricated. A
     derived/autonomous patient risk score is the register's BLOCKED MDSW trigger (Annex VIII Rule 11) and is **beyond founder authority** to ship as real; it needs documented clinical +
     privacy + MDR review.
   - **Review-throughput / activity feed / imports panels** → **honest gated empty states**. Each
     needs a new tenant-scoped, RLS-scoped, PII-free read endpoint (report-version throughput, an
     audit-events read, an import_jobs rollup) — **deferred, register-gated backend slices**.

3. **The marker modal** uses the compliant lab **reference bar** (band reflects the lab interval
   only) + the positional Lage pill — **not** the comp's heuristic good/warn/bad severity gauge
   (ADR-0005 "corrected, not carried over").

4. **A–E grade** stays deleted. The founder noted it "must be implemented later"; this is recorded
   as a **future decision to reconcile** — a merged A–E grade is a rolled-up domain score and
   **conflicts with the no-unified-score doctrine** (ADR-0003), so it cannot simply be added.

## Named divergences & residual gates

- The founder accepted the three surfaces (ADR-0005). For the **real-data** path, two of them
  (Risiko, Normal/Abnormal) cannot be made _real_ without classifiers that are BLOCKED / beyond
  founder authority — so they are gated/substituted here, **not** removed from the product
  direction. Making them real remains gated behind documented clinical + privacy + MDR review and a
  notified-body call. Data-quality % is now a **real** completeness stat (within the
  documentation-support boundary), not a clinical-quality score.
- **Real patients stay BLOCKED** behind the pre-existing human gates; this slice runs on synthetic
  seed data only.

## Consequences

- New presenters (`presenters/dashboard.ts`, `presenters/patientDetail.ts`), governed `page.tsx`
  loaders, rewritten client components consuming view shapes; `worklist()` re-added to `api.ts`;
  `lib/demo/dashboard.ts` removed. No backend/schema change.
- **Follow-ups (each its own register-gated slice):** the three deferred read endpoints
  (throughput / audit-feed / imports), a copy-language re-point covering the new German strings
  (ADR-0003 consequence), and web route-smoke tests (the repo has none today).

## Addendum (2026-06-27) — two Übersicht panels made real

Two of the four gated Übersicht panels are now backed by **real, tenant-scoped data**; the other
two (activity feed, imports) stay gated.

- **Datenlage (was the gated "Datenqualität" gauge)** → a new tenant-scoped read endpoint
  `GET /api/v1/worklist/coverage` (`CoverageOut`: `total`, `published`, `with_reference`,
  `latest_observed_at`) aggregates **observation coverage** in one query under `OBSERVATION_READ`,
  audited (`worklist.coverage.read`), tenant-filtered with RLS as defense-in-depth. The tile shows
  the **published share** + reference-interval coverage + freshness. These are **plain counts /
  ratios over real observations — explicitly NOT a clinical data-quality score.** The quality/rules
  model the comp's "94 %" gauge implied still does **not** exist (**Gate G1 remains open**); the UI
  caption says "keine Qualitätsbewertung". This is the same data-completeness idea already shown
  per-patient on the Detail screen, now aggregated tenant-wide.
- **Berichtsstatus (was the gated "Review-Durchsatz" chart)** → a **real status snapshot**
  (Momentaufnahme) of the latest report status across the worklist we already load — no new data.
  It is deliberately **not** a throughput time series; a true rate-over-time still needs a
  `report_versions`-by-status endpoint and **remains deferred**. The heading + subtitle say
  "Momentaufnahme", not "Durchsatz", to avoid implying a rate we do not have.
- **Unchanged:** synthetic-seed-only; no schema/migration; the activity-feed and imports panels
  stay honestly gated (their read endpoints are still deferred slices); A–E grade stays deleted;
  Risiko + normal/abnormal verdicts remain gated/substituted (beyond founder authority to ship real).
- **Tests:** `apps/api/tests/test_coverage.py` pins the counts and proves cross-tenant isolation
  (a fresh tenant sees all-zero coverage). OpenAPI re-exported + client regenerated (contract, not
  a hand-typed shape).
