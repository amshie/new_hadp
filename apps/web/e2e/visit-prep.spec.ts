import { expect, test } from "@playwright/test";

import type { CoreKpi, DomainMatrixView, TimelinePoint } from "../src/lib/api";
import { presentDomainOverview } from "../src/lib/presenters/domainOverview";
import {
  presentVisitPrep,
  STALE_AFTER_DAYS,
} from "../src/lib/presenters/visitPrep";
import { asStaff, hydrated } from "./support/staff";

// The page before a visit (apps/web/src/lib/presenters/visitPrep.ts, docs/notes/0022): the
// facts since the latest interpretation run, from synthetic timeline points. No browser for
// the presenter; one browser pass over the seeded patient for the card and its page.

let seq = 0;
function point(over: Partial<TimelinePoint>): TimelinePoint {
  seq += 1;
  return {
    observation_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    metric_code: null,
    original_name: "Synthetic value",
    original_value: "1",
    original_unit: "mmol/L",
    value: "1",
    unit: "mmol/L",
    normalized: true,
    converted: false,
    reference_low: null,
    reference_high: null,
    observed_at: "2025-06-10T00:00:00Z",
    observed_at_is_date_only: true,
    received_at: "2025-06-12T08:00:00Z",
    review_status: "published",
    delta_vs_previous: null,
    previous_observation_id: null,
    kpi_code: null,
    kpi_primary_domain: null,
    kpi_secondary_domains: [],
    comparability: null,
    comparability_reason: null,
    supersedes_observation_id: null,
    superseded_by_observation_id: null,
    input_replaced: false,
    derived: false,
    formula_id: null,
    derived_from: [],
    ...over,
  };
}

const CATALOG: CoreKpi[] = [
  {
    code: "cardio.ldl_c",
    display_name: "LDL cholesterol",
    primary_domain_axis: "cardiovascular",
    measurement_class: "laboratory",
  },
  {
    code: "metabolic.hba1c",
    display_name: "HbA1c",
    primary_domain_axis: "metabolic",
    measurement_class: "laboratory",
  },
];

function ldl(over: Partial<TimelinePoint>): TimelinePoint {
  return point({
    original_name: "LDL-Cholesterin",
    kpi_code: "cardio.ldl_c",
    kpi_primary_domain: "cardiovascular",
    reference_low: "0",
    reference_high: "3.0",
    ...over,
  });
}

function hba1c(over: Partial<TimelinePoint>): TimelinePoint {
  return point({
    original_name: "HbA1c",
    kpi_code: "metabolic.hba1c",
    kpi_primary_domain: "metabolic",
    unit: "%",
    original_unit: "%",
    reference_low: "4.0",
    reference_high: "6.0",
    ...over,
  });
}

// The page is put together on 2026-03-20; the run was recorded eight days before.
const NOW = Date.parse("2026-03-20T09:00:00Z");
const RUN: DomainMatrixView = {
  run_id: "run-2",
  run_number: 2,
  recorded_at: "2026-03-12T10:00:00Z",
  domains: [
    {
      domain_axis: "cardiovascular",
      cis_status: "CIS_3_RISK_DOMINANT_OR_CONFLICTING",
      actionability_class: "D_ACTIONABLE_UNDER_GOVERNANCE",
      followup_adequacy: "adequate",
      review_status: "clinician_reviewed",
      rationale: null,
      cells: [],
    },
  ],
};

const BEFORE_RUN = {
  observed_at: "2025-12-01T00:00:00Z",
  received_at: "2025-12-02T08:00:00Z",
};
const AFTER_RUN = {
  observed_at: "2026-03-15T00:00:00Z",
  received_at: "2026-03-16T08:00:00Z",
};

test("without a run there is no 'since': only what stands today", () => {
  const prep = presentVisitPrep(
    presentDomainOverview(
      [ldl({ value: "2.8", ...BEFORE_RUN })],
      CATALOG,
      null,
      NOW,
    ),
  );
  expect(prep.run).toBeNull();
  expect(prep.newValues).toEqual([]);
  expect(prep.moved).toEqual([]);
  expect(prep.domainsWithoutVerdict).toEqual([]);
  // HbA1c has no value; LDL's is 109 days old, so not yet old.
  expect(prep.missing.map((m) => m.code)).toEqual(["metabolic.hba1c"]);
  expect(prep.stale).toEqual([]);
  expect(prep.quiet).toBe(false);
});

test("a value received after the run is new; one that crossed the interval has moved", () => {
  const prep = presentVisitPrep(
    presentDomainOverview(
      [
        ldl({ value: "2.8", ...BEFORE_RUN }),
        ldl({ value: "3.4", ...AFTER_RUN }),
        hba1c({ value: "5.5", ...BEFORE_RUN }),
      ],
      CATALOG,
      RUN,
      NOW,
    ),
  );
  expect(prep.run).toEqual({ number: 2, day: "12.03.2026" });
  expect(prep.newValues.map((v) => [v.code, v.value, v.position])).toEqual([
    ["cardio.ldl_c", "3.4", "above"],
  ]);
  expect(prep.newOutside).toBe(1);
  expect(prep.moved).toHaveLength(1);
  const move = prep.moved[0]!;
  expect([move.code, move.from, move.to]).toEqual([
    "cardio.ldl_c",
    "within",
    "above",
  ]);
  expect([move.previousDay, move.latestDay]).toEqual([
    "01.12.2025",
    "15.03.2026",
  ]);
  // The run recorded a verdict for one domain of six.
  expect(prep.domainsWithoutVerdict).toEqual([
    "metabolic",
    "immune_inflammation",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
  ]);
  expect(prep.missing).toEqual([]);
});

test("a core marker whose latest value is older than the stated days is listed as old", () => {
  const prep = presentVisitPrep(
    presentDomainOverview(
      [
        hba1c({
          value: "5.5",
          observed_at: "2025-05-01T00:00:00Z",
          received_at: "2025-05-02T08:00:00Z",
        }),
        ldl({ value: "2.8", ...AFTER_RUN }),
      ],
      CATALOG,
      RUN,
      NOW,
    ),
  );
  expect(prep.staleAfterDays).toBe(STALE_AFTER_DAYS);
  expect(prep.stale.map((s) => [s.code, s.observedDay])).toEqual([
    ["metabolic.hba1c", "01.05.2025"],
  ]);
  expect(prep.stale[0]!.ageDays).toBeGreaterThan(STALE_AFTER_DAYS);
  // A new value with no standing value before it has not "moved".
  expect(prep.moved).toEqual([]);
});

test("a value awaiting review is counted, never listed as new", () => {
  const prep = presentVisitPrep(
    presentDomainOverview(
      [
        ldl({ value: "2.8", ...BEFORE_RUN }),
        ldl({ value: "3.4", review_status: "pending", ...AFTER_RUN }),
      ],
      CATALOG,
      RUN,
      NOW,
    ),
  );
  expect(prep.pending).toBe(1);
  expect(prep.newValues).toEqual([]);
  expect(prep.moved).toEqual([]);
});

test("a value no catalog marker names is new too, and counted as unassigned", () => {
  const prep = presentVisitPrep(
    presentDomainOverview(
      [point({ original_name: "Sonstiger Wert", value: "7", ...AFTER_RUN })],
      [],
      RUN,
      NOW,
    ),
  );
  expect(prep.newValues.map((v) => [v.code, v.name, v.axis])).toEqual([
    [null, "Sonstiger Wert", null],
  ]);
  expect(prep.unassigned).toBe(1);
});

test("nothing new, moved, old, missing or waiting is said so", () => {
  const every: DomainMatrixView = {
    ...RUN,
    domains: [
      "metabolic",
      "immune_inflammation",
      "cardiovascular",
      "neurocognitive",
      "musculoskeletal",
      "regenerative_capacity",
    ].map((axis) => ({ ...RUN.domains[0]!, domain_axis: axis })),
  };
  const prep = presentVisitPrep(
    presentDomainOverview(
      [ldl({ value: "2.8", ...BEFORE_RUN })],
      [],
      every,
      NOW,
    ),
  );
  expect(prep.quiet).toBe(true);
});

// A marker of the catalog no laboratory gives an interval for (docs/notes/0025's "ohne
// Referenz der Quelle").
const SBP: CoreKpi = {
  code: "cardio.sbp",
  display_name: "Systolic blood pressure",
  primary_domain_axis: "cardiovascular",
  measurement_class: "vital_sign",
};
function sbp(over: Partial<TimelinePoint>): TimelinePoint {
  return point({
    original_name: "Systolischer Blutdruck",
    kpi_code: "cardio.sbp",
    kpi_primary_domain: "cardiovascular",
    unit: "mm[Hg]",
    original_unit: "mm[Hg]",
    ...over,
  });
}

test("today counts each marker's latest value by its side of the interval; the outside ones carry their course", () => {
  const first = ldl({ value: "2.8", ...BEFORE_RUN });
  const prep = presentVisitPrep(
    presentDomainOverview(
      [
        first,
        ldl({
          value: "3.4",
          ...AFTER_RUN,
          previous_observation_id: first.observation_id,
          comparability: "comparable",
        }),
        hba1c({ value: "5.5", ...BEFORE_RUN }),
        sbp({ value: "128", ...BEFORE_RUN }),
      ],
      [...CATALOG, SBP],
      RUN,
      NOW,
    ),
  );
  // Three markers with a value — LDL counted once, by its latest — one outside, one within,
  // one the source gave no interval for. Counts only: nothing weighted or summed.
  expect(prep.today.withValue).toBe(3);
  expect(prep.today.within).toBe(1);
  expect(prep.today.noReference).toBe(1);
  expect(prep.today.latestDay).toBe("15.03.2026");
  expect(prep.today.outside.map((o) => [o.code, o.value, o.position])).toEqual([
    ["cardio.ldl_c", "3.4", "above"],
  ]);
  // Its course: both standing values, the second joined to the first because the API found
  // them comparable.
  expect(
    prep.today.outside[0]!.trend.map((t) => [t.day, t.position, t.linked]),
  ).toEqual([
    ["01.12.2025", "within", false],
    ["15.03.2026", "above", true],
  ]);
  // Each domain beside the clinician's verdict: its core markers with a value, its markers
  // outside, and the verdict as recorded (none where the run recorded none).
  const cardio = prep.domains.find((d) => d.axis === "cardiovascular")!;
  expect(cardio).toMatchObject({
    coreTotal: 2,
    coreWithValue: 2,
    outside: 1,
    verdict: {
      cisStatus: "CIS_3_RISK_DOMINANT_OR_CONFLICTING",
      actionabilityClass: "D_ACTIONABLE_UNDER_GOVERNANCE",
      followupAdequacy: "adequate",
      reviewed: true,
    },
  });
  expect(prep.domains.find((d) => d.axis === "metabolic")!.verdict).toBeNull();
  expect(prep.domains.map((d) => d.axis)).toHaveLength(6);
});

test("a course draws no line between values the API did not find comparable", () => {
  const first = ldl({ value: "3.2", ...BEFORE_RUN });
  const prep = presentVisitPrep(
    presentDomainOverview(
      [
        first,
        ldl({
          value: "3.4",
          ...AFTER_RUN,
          previous_observation_id: first.observation_id,
          comparability: "not_comparable",
        }),
      ],
      CATALOG,
      RUN,
      NOW,
    ),
  );
  expect(prep.today.outside[0]!.trend.map((t) => t.linked)).toEqual([
    false,
    false,
  ]);
});

test("old and missing core markers are grouped by sample day and by domain", () => {
  const OLD = {
    observed_at: "2025-05-01T00:00:00Z",
    received_at: "2025-05-02T08:00:00Z",
  };
  const prep = presentVisitPrep(
    presentDomainOverview(
      [hba1c({ value: "5.5", ...OLD }), ldl({ value: "2.8", ...OLD })],
      [...CATALOG, SBP],
      RUN,
      NOW,
    ),
  );
  expect(prep.staleByDay).toEqual([{ key: "01.05.2025", count: 2 }]);
  expect(prep.staleByAxis).toEqual([
    { key: "metabolic", count: 1 },
    { key: "cardiovascular", count: 1 },
  ]);
  expect(prep.missingByAxis).toEqual([{ key: "cardiovascular", count: 1 }]);
  expect(prep.today.outside).toEqual([]);
});

test("the card is on the patient page and opens as a page of its own", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/patients");
    const row = page.getByRole("button", { name: /SYN-0001/ }).first();
    await hydrated(row);
    await row.click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);

    const card = page.getByRole("region", { name: "Vorbereitung" });
    await expect(card).toBeVisible();
    await expect(card).toContainText(
      /Seit Lauf \d+ · erfasst am \d{2}\.\d{2}\.\d{4}/,
    );
    await expect(card).toContainText("jede Zeile führt zum Wert");

    // Today's position first: the counts, then the clinician's six verdicts of the run.
    const today = card.getByRole("region", { name: /^Lage heute/ });
    await expect(today).toContainText("Marker mit Wert");
    await expect(today).toContainText("außerhalb des Intervalls");
    await expect(today).toContainText(
      "Urteile der Ärztin oder des Arztes, wie erfasst",
    );
    const verdicts = today.getByRole("table").filter({
      has: page.getByRole("columnheader", { name: "Actionability" }),
    });
    await expect(verdicts.getByRole("row")).toHaveCount(7);
    // The header says where the record stands in time (the first of two such lines: the
    // other is the Werte tab's, hidden).
    await expect(
      page.getByText(/^Letzte Interpretation: Lauf \d+ · /).first(),
    ).toBeVisible();

    // The old and the missing are counted per domain; their lists wait behind a button.
    const gaps = card.getByRole("region", { name: /^Alt und fehlend/ });
    const unfold = gaps
      .getByRole("button", { name: /^\d+ Marker anzeigen$/ })
      .first();
    await hydrated(unfold);
    await expect(unfold).toHaveAttribute("aria-expanded", "false");
    await unfold.click();
    await expect(
      gaps.getByRole("button", { name: "Marker ausblenden" }),
    ).toHaveAttribute("aria-expanded", "true");

    // A marker's line opens the marker's history, as the domain lists do.
    const markers = card.getByRole("button", { name: /^Marker .* öffnen$/ });
    if ((await markers.count()) > 0) {
      const first = markers.first();
      await hydrated(first);
      await first.click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.keyboard.press("Escape");
      // Closed, with the focus back on the line that opened it: the page has settled before
      // the next step, so the navigation that step starts is not crossed by the closing.
      await expect(page.getByRole("dialog")).toBeHidden();
      await expect(first).toBeFocused();
    }

    const open = card.getByRole("link", { name: "Als Seite öffnen" });
    await open.click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}\/vorbereitung$/);
    await expect(
      page.getByRole("heading", { level: 1, name: /^Vorbereitung · / }),
    ).toBeVisible();
    const own = page.getByRole("region", { name: "Vorbereitung" });
    await expect(own.getByRole("button", { name: "Drucken" })).toBeVisible();
    // Here a marker's line leads back to its domain on the patient page.
    const back = own.getByRole("link", { name: "Zur Akte" });
    await expect(back).toHaveAttribute("href", /\/patients\/[0-9a-f-]{36}$/);
  });
});
