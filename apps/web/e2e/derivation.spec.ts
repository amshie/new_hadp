import { expect, test } from "@playwright/test";

import type { DomainMatrixView, TimelinePoint } from "../src/lib/api";
import { derivationOf, derivedInputsText } from "../src/lib/derivation";
import { presentDomainOverview } from "../src/lib/presenters/domainOverview";
import { presentVisitPrep } from "../src/lib/presenters/visitPrep";

// A value the platform computed from other values (apps/web/src/lib/derivation.ts): it says
// what it was computed from, and never reads as a measured value. No browser: synthetic
// timeline points in, the views out.

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

const total = point({
  original_name: "Gesamtcholesterin",
  original_value: "5,2",
  value: "5.2",
  kpi_code: "cardio.total_cholesterol",
  kpi_primary_domain: "cardiovascular",
});
const hdl = point({
  original_name: "HDL-Cholesterin",
  original_value: "1,3",
  value: "1.3",
  kpi_code: "cardio.hdl_c",
  kpi_primary_domain: "cardiovascular",
});
const nonHdl = point({
  original_name: "Non-HDL cholesterol",
  original_value: "3.90",
  value: "3.90",
  kpi_code: "cardio.non_hdl_c",
  kpi_primary_domain: "cardiovascular",
  received_at: "2026-03-13T08:00:00Z",
  derived: true,
  formula_id: "non_hdl_c.v1",
  derived_from: [
    { role: "hdl", observation_id: hdl.observation_id },
    { role: "total_cholesterol", observation_id: total.observation_id },
  ],
});
const timeline = [total, hdl, nonHdl];
const byId = new Map(timeline.map((p) => [p.observation_id, p]));

test("a computed value names its formula and the values it was computed from", () => {
  const d = derivationOf(nonHdl, byId);
  expect(d?.formulaId).toBe("non_hdl_c.v1");
  expect(d?.inputs.map((i) => [i.role, i.name, i.value, i.unit])).toEqual([
    ["hdl", "HDL-Cholesterin", "1.3", "mmol/L"],
    ["total_cholesterol", "Gesamtcholesterin", "5.2", "mmol/L"],
  ]);
  expect(d && derivedInputsText(d, "und")).toBe(
    "HDL-Cholesterin 1.3 mmol/L und Gesamtcholesterin 5.2 mmol/L",
  );
});

test("a value a source reported carries no derivation", () => {
  expect(derivationOf(total, byId)).toBeNull();
});

test("an input missing from the record: no input is named rather than some", () => {
  const d = derivationOf(nonHdl, new Map([[hdl.observation_id, hdl]]));
  expect(d?.inputs.map((i) => i.name)).toEqual(["HDL-Cholesterin", null]);
  expect(d && derivedInputsText(d, "und")).toBeNull();
});

test("the overview marks a computed marker and its values; a measured one stays unmarked", () => {
  const overview = presentDomainOverview(timeline, [], null);
  const cardio = overview.domains.find((d) => d.axis === "cardiovascular");
  const series = new Map(
    (cardio?.rows ?? []).flatMap((r) =>
      r.kind === "series" ? [[r.series.kpiCode, r.series] as const] : [],
    ),
  );
  expect(series.get("cardio.non_hdl_c")?.derived).toBe(true);
  expect(series.get("cardio.non_hdl_c")?.latest?.derivation?.formulaId).toBe(
    "non_hdl_c.v1",
  );
  expect(series.get("cardio.total_cholesterol")?.derived).toBe(false);
  expect(series.get("cardio.total_cholesterol")?.latest?.derivation).toBeNull();
});

test("the page before a visit lists a computed value as computed", () => {
  const run: DomainMatrixView = {
    run_id: "run-1",
    run_number: 1,
    recorded_at: "2026-03-12T10:00:00Z",
    domains: [],
  };
  const prep = presentVisitPrep(presentDomainOverview(timeline, [], run));
  expect(prep.newValues.map((v) => [v.code, v.derived])).toEqual([
    ["cardio.non_hdl_c", true],
  ]);
});
