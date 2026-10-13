import { expect, test } from "@playwright/test";

import type { CoreKpi, TimelinePoint } from "../src/lib/api";
import {
  presentDomainOverview,
  type MarkerSeries,
} from "../src/lib/presenters/domainOverview";
import { historyGeometry, niceTicks } from "../src/lib/presenters/history";

// The geometry of a marker's history (apps/web/src/lib/presenters/history.ts): which values
// are drawn, which are joined, and the interval behind each. No browser.

let seq = 0;
function ldl(over: Partial<TimelinePoint>): TimelinePoint {
  seq += 1;
  return {
    observation_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    metric_code: null,
    original_name: "LDL-Cholesterin",
    original_value: "1",
    original_unit: "mmol/L",
    value: "1",
    unit: "mmol/L",
    normalized: true,
    converted: false,
    reference_low: "0",
    reference_high: "3.0",
    observed_at: "2025-06-10T00:00:00Z",
    observed_at_is_date_only: true,
    received_at: "2025-06-12T08:00:00Z",
    review_status: "published",
    delta_vs_previous: null,
    previous_observation_id: null,
    kpi_code: "cardio.ldl_c",
    kpi_primary_domain: "cardiovascular",
    kpi_secondary_domains: [],
    comparability: null,
    comparability_reason: null,
    supersedes_observation_id: null,
    superseded_by_observation_id: null,
    input_replaced: false,
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
];
const BOX = {
  width: 600,
  height: 240,
  padLeft: 40,
  padRight: 20,
  padTop: 20,
  padBottom: 30,
};

function seriesOf(points: TimelinePoint[]): {
  series: MarkerSeries;
  axis: { start: number; end: number };
} {
  const overview = presentDomainOverview(
    points,
    CATALOG,
    null,
    Date.UTC(2026, 9, 13),
  );
  const row = overview.domains[2]!.rows[0]!;
  if (row.kind !== "series") throw new Error("no series");
  return { series: row.series, axis: overview.timeAxis! };
}

test("a line joins exactly the values the API compared; nothing else is joined", () => {
  // A calculated LDL the API did not compare with the direct ones (no delta, no previous).
  const calculated = ldl({
    value: "3.9",
    observed_at: "2024-11-04T00:00:00Z",
    comparability: "not_comparable",
    comparability_reason: "context_differs",
  });
  const first = ldl({ value: "3.6", observed_at: "2025-01-15T00:00:00Z" });
  const second = ldl({
    value: "2.8",
    observed_at: "2025-06-10T00:00:00Z",
    delta_vs_previous: "-0.8",
    previous_observation_id: first.observation_id,
    comparability: "comparable",
  });
  const replaced = ldl({
    value: "3.4",
    observed_at: "2025-11-20T00:00:00Z",
    superseded_by_observation_id: "y",
  });
  const corrected = ldl({
    value: "3.1",
    observed_at: "2025-11-20T00:00:00Z",
    delta_vs_previous: "0.3",
    previous_observation_id: second.observation_id,
    comparability: "comparable",
  });
  const pending = ldl({
    value: "2.9",
    observed_at: "2026-09-01T00:00:00Z",
    review_status: "pending",
  });
  const rejected = ldl({
    value: "9.9",
    observed_at: "2026-09-02T00:00:00Z",
    review_status: "rejected",
  });
  const text = ldl({
    value: null,
    original_value: "folgt",
    observed_at: "2026-09-03T00:00:00Z",
  });
  const { series, axis } = seriesOf([
    calculated,
    first,
    second,
    replaced,
    corrected,
    pending,
    rejected,
    text,
  ]);
  const g = historyGeometry(series, axis, BOX);

  expect(g.segments.map((s) => [s.fromId, s.toId])).toEqual([
    [first.observation_id, second.observation_id],
    [second.observation_id, corrected.observation_id],
  ]);
  expect(
    Object.fromEntries(g.points.map((p) => [p.value.value, p.kind])),
  ).toEqual({
    "3.9": "standing",
    "3.6": "standing",
    "2.8": "standing",
    "3.4": "replaced",
    "3.1": "standing",
    "2.9": "pending",
  });
  // The rejected value and the text result are not drawn; the table lists them.
  expect(g.notDrawn).toBe(2);
  // Outside the interval: the standing values above 3.0 — not the replaced one, not the one
  // in review.
  expect(
    g.points
      .filter((p) => p.outside)
      .map((p) => p.value.value)
      .sort(),
  ).toEqual(["3.1", "3.6", "3.9"]);
  // Time runs left to right, and the higher value is drawn higher.
  const at = (v: string) => g.points.find((p) => p.value.value === v)!;
  expect(at("3.6").x).toBeLessThan(at("2.8").x);
  expect(at("3.6").y).toBeLessThan(at("2.8").y);
});

test("the interval steps with the laboratory and stays open on an open side", () => {
  const labA = ldl({ value: "2.8", observed_at: "2025-06-10T00:00:00Z" });
  const labB = ldl({
    value: "2.5",
    observed_at: "2026-03-02T00:00:00Z",
    reference_low: null,
    reference_high: "2.6",
  });
  const replaced = ldl({
    value: "3.4",
    observed_at: "2025-11-20T00:00:00Z",
    reference_high: "9.9",
    superseded_by_observation_id: "z",
  });
  const { series, axis } = seriesOf([labA, replaced, labB]);
  const g = historyGeometry(series, axis, BOX);

  // Two bands: the replaced value brings none of its own.
  expect(g.bands).toHaveLength(2);
  const [a, b] = g.bands;
  // They meet halfway between their values, and B's upper bound (2.6) is lower than A's (3.0).
  expect(a!.x1).toBeCloseTo(b!.x0);
  expect(b!.top).toBeGreaterThan(a!.top);
  // A states both bounds; B has no lower bound and reaches the bottom of the plot.
  expect(a).toMatchObject({ openTop: false, openBottom: false });
  expect(b).toMatchObject({ openTop: false, openBottom: true });
  expect(b!.bottom).toBe(g.plotBottom);
});

test("the time axis marks quarters and names the year in January", () => {
  const { series, axis } = seriesOf([
    ldl({ value: "3.6", observed_at: "2025-01-15T00:00:00Z" }),
    ldl({ value: "2.8", observed_at: "2025-06-10T00:00:00Z" }),
  ]);
  const g = historyGeometry(series, axis, BOX);
  expect(g.xTicks.map((t) => [t.month, t.year])).toEqual([
    [0, 2025],
    [3, null],
    [6, null],
    [9, null],
    [0, 2026],
    [3, null],
    [6, null],
    [9, null],
  ]);
  // Today is the right end of the axis.
  expect(g.todayX).toBeCloseTo(g.plotRight);
});

test("value ticks are round numbers", () => {
  expect(niceTicks(0, 4.4, 4)).toEqual([0, 1, 2, 3, 4]);
  expect(niceTicks(0.5, 1.3, 4)).toEqual([0.6, 0.8, 1, 1.2]);
  expect(niceTicks(118, 140, 4)).toEqual([120, 125, 130, 135, 140]);
});
