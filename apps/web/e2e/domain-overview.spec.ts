import { expect, test } from "@playwright/test";

import type { CoreKpi, DomainMatrixView, TimelinePoint } from "../src/lib/api";
import {
  presentDomainOverview,
  rowMatches,
  valueMatches,
  type DomainRow,
  type PrepFilter,
} from "../src/lib/presenters/domainOverview";

// The patient page's domain overview (apps/web/src/lib/presenters/domainOverview.ts): values
// placed by the catalog, the counts before a visit, and the filters those counts are. No
// browser: synthetic timeline points in, the overview out.

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
    code: "cardio.apob",
    display_name: "Apolipoprotein B",
    primary_domain_axis: "cardiovascular",
    measurement_class: "laboratory",
  },
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
  {
    code: "neuro.episodic_memory_score",
    display_name: "Episodic memory score",
    primary_domain_axis: "neurocognitive",
    measurement_class: "functional_test",
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

function seriesRow(rows: DomainRow[], code: string) {
  const row = rows.find(
    (r) => r.kind === "series" && r.series.kpiCode === code,
  );
  if (!row || row.kind !== "series") throw new Error(`no row for ${code}`);
  return row.series;
}

test("values are placed by the catalog; expected markers without a value are listed in place", () => {
  const overview = presentDomainOverview(
    [
      ldl({ value: "2.8", observed_at: "2025-06-10T00:00:00Z" }),
      point({
        original_name: "Lp(a)",
        kpi_code: "cardio.lpa",
        kpi_primary_domain: "cardiovascular",
        value: "142",
        unit: "nmol/L",
      }),
      point({
        original_name: "Albumin",
        kpi_code: "cardio.albumin_like",
        kpi_primary_domain: "cardiovascular",
      }),
    ],
    CATALOG,
    null,
  );
  expect(overview.domains.map((d) => d.axis)).toEqual([
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
  ]);
  const cardio = overview.domains[2]!;
  // Core markers in catalog order (ApoB missing, LDL present), then the domain's other
  // markers by name.
  expect(
    cardio.rows.map((r) =>
      r.kind === "series"
        ? `series:${r.series.kpiCode}`
        : `missing:${r.marker.code}`,
    ),
  ).toEqual([
    "missing:cardio.apob",
    "series:cardio.ldl_c",
    "series:cardio.albumin_like",
    "series:cardio.lpa",
  ]);
  expect(cardio.facts.coreTotal).toBe(2);
  expect(cardio.facts.coreWithValue).toBe(1);
  // A domain without a value still has its row of expected markers.
  const neuro = overview.domains[3]!;
  expect(neuro.rows).toEqual([
    {
      kind: "missing",
      marker: {
        code: "neuro.episodic_memory_score",
        name: "Episodic memory score",
        measurementClass: "functional_test",
      },
    },
  ]);
  // Without a run there are values per domain all the same, and no verdict.
  expect(cardio.verdict).toBeNull();
  expect(overview.runNumber).toBeNull();
});

test("a marker's latest value is its latest standing published one", () => {
  const replaced = ldl({
    value: "3.4",
    observed_at: "2025-11-20T00:00:00Z",
    superseded_by_observation_id: "x",
  });
  const correction = ldl({ value: "3.1", observed_at: "2025-11-20T00:00:00Z" });
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
  const overview = presentDomainOverview(
    [replaced, correction, pending, rejected],
    CATALOG,
    null,
  );
  const s = seriesRow(overview.domains[2]!.rows, "cardio.ldl_c");
  // Neither the value in review, nor the rejected one, nor the replaced one is "latest".
  expect(s.latest?.value).toBe("3.1");
  expect(s.values).toHaveLength(4);
  expect(s.pending).toBe(1);
  expect(s.corrected).toBe(true);
  // 3.1 above an interval of 0–3.0: outside, from the latest standing value alone.
  expect(s.latest?.position).toBe("above");
  expect(s.outside).toBe(true);
  // A position is stated for a standing value only.
  expect(s.values.map((v) => v.position)).toEqual([
    "not_evaluable",
    "above",
    "not_evaluable",
    "not_evaluable",
  ]);
  // The name is the source's, from the latest standing value.
  expect(s.name).toBe("LDL-Cholesterin");
});

test("a derived value from a replaced input does not stand", () => {
  const overview = presentDomainOverview(
    [
      point({
        kpi_code: "metabolic.hba1c",
        kpi_primary_domain: "metabolic",
        value: "5.4",
        observed_at: "2025-01-15T00:00:00Z",
      }),
      point({
        kpi_code: "metabolic.hba1c",
        kpi_primary_domain: "metabolic",
        value: "5.9",
        observed_at: "2025-06-10T00:00:00Z",
        input_replaced: true,
      }),
    ],
    CATALOG,
    null,
  );
  const s = seriesRow(overview.domains[0]!.rows, "metabolic.hba1c");
  expect(s.latest?.value).toBe("5.4");
});

test("the counts before a visit, and the filters they are", () => {
  const timeline = [
    // Received before the run: interpreted.
    ldl({ value: "2.5", received_at: "2026-03-03T09:00:00Z" }),
    // Received after the run, in review.
    ldl({
      value: "2.9",
      observed_at: "2026-09-01T00:00:00Z",
      received_at: "2026-09-02T09:00:00Z",
      review_status: "pending",
    }),
    // Received after the run, rejected: not counted as a value since the run.
    ldl({
      value: "8",
      observed_at: "2026-09-03T00:00:00Z",
      received_at: "2026-09-04T09:00:00Z",
      review_status: "rejected",
    }),
    // HbA1c above its interval.
    point({
      kpi_code: "metabolic.hba1c",
      kpi_primary_domain: "metabolic",
      value: "5.8",
      reference_low: "4.0",
      reference_high: "5.6",
      received_at: "2026-03-03T09:00:00Z",
    }),
    // A value without a catalog marker, in review.
    point({
      original_name: "Smoke-Analyt",
      review_status: "pending",
      received_at: "2025-06-12T08:00:00Z",
    }),
  ];
  const overview = presentDomainOverview(timeline, CATALOG, RUN);
  expect(overview.runRecordedAt).toBe("2026-03-12T10:00:00Z");
  expect(overview.counts).toEqual({
    since_run: 1,
    outside: 1,
    pending: 2,
    // ApoB and the memory score have no value at all.
    missing: 2,
  });

  const cardio = overview.domains[2]!;
  expect(cardio.facts).toEqual({
    coreTotal: 2,
    coreWithValue: 1,
    outside: 0,
    pending: 1,
    receivedSinceRun: 1,
    latestObservedAt: "2025-06-10T00:00:00Z",
    latestObservedDay: "10.06.2025",
  });
  expect(cardio.verdict).toEqual({
    cisStatus: "CIS_3_RISK_DOMINANT_OR_CONFLICTING",
    actionabilityClass: "D_ACTIONABLE_UNDER_GOVERNANCE",
    followupAdequacy: "adequate",
    reviewed: true,
    citesReplaced: false,
  });

  // Each count is matched by what its filter shows.
  const shown = (filter: PrepFilter) => ({
    rows: overview.domains.flatMap((d) =>
      d.rows.filter((r) => rowMatches(r, filter)),
    ),
    unassigned: overview.unassigned.filter((v) => valueMatches(v, filter)),
  });
  const codes = (filter: PrepFilter) =>
    shown(filter).rows.map((r) =>
      r.kind === "series" ? r.series.kpiCode : r.marker.code,
    );
  expect(codes("since_run")).toEqual(["cardio.ldl_c"]);
  expect(codes("outside")).toEqual(["metabolic.hba1c"]);
  expect(codes("pending")).toEqual(["cardio.ldl_c"]);
  expect(shown("pending").unassigned.map((v) => v.name)).toEqual([
    "Smoke-Analyt",
  ]);
  expect(codes("missing")).toEqual([
    "cardio.apob",
    "neuro.episodic_memory_score",
  ]);
  // No filter shows everything.
  expect(
    overview.domains.every((d) => d.rows.every((r) => rowMatches(r, null))),
  ).toBe(true);
});

test("a marker whose only value is in review is still missing a published value", () => {
  const overview = presentDomainOverview(
    [ldl({ review_status: "pending" })],
    CATALOG,
    null,
  );
  const cardio = overview.domains[2]!;
  expect(cardio.facts.coreWithValue).toBe(0);
  expect(overview.counts.missing).toBe(4);
  expect(overview.counts.since_run).toBeNull();
  const s = seriesRow(cardio.rows, "cardio.ldl_c");
  expect(s.latest).toBeNull();
  expect(rowMatches({ kind: "series", series: s }, "missing")).toBe(true);
  expect(rowMatches({ kind: "series", series: s }, "pending")).toBe(true);
});

test("a marker linked to another domain is shown there, and counted only in its own", () => {
  const overview = presentDomainOverview(
    [
      point({
        kpi_code: "metabolic.hba1c",
        kpi_primary_domain: "metabolic",
        kpi_secondary_domains: ["cardiovascular"],
        value: "5.8",
        reference_low: "4.0",
        reference_high: "5.6",
      }),
    ],
    CATALOG,
    null,
  );
  const [metabolic, , cardio] = overview.domains;
  expect(cardio!.alsoRelevant.map((s) => s.kpiCode)).toEqual([
    "metabolic.hba1c",
  ]);
  expect(cardio!.facts.outside).toBe(0);
  expect(metabolic!.facts.outside).toBe(1);
  expect(overview.counts.outside).toBe(1);
});

test("a run that cites a replaced value says so", () => {
  const run: DomainMatrixView = {
    ...RUN,
    domains: [
      {
        ...RUN.domains[0]!,
        review_status: "draft",
        cells: [
          {
            tri_state_axis: "biological",
            state: "STABLE",
            endpoint_adequacy: "adequate",
            evidence_count: 1,
            rationale: null,
            evidence: [
              {
                observation_id: "x",
                original_name: "LDL",
                value: "3.4",
                unit: "mmol/L",
                reference: null,
                observed_at: "2025-11-20T00:00:00Z",
                review_status: "published",
                metric_code: null,
                superseded: true,
              },
            ],
          },
        ],
      },
    ],
  };
  const overview = presentDomainOverview([], CATALOG, run);
  expect(overview.domains[2]!.verdict).toMatchObject({
    reviewed: false,
    citesReplaced: true,
  });
});
