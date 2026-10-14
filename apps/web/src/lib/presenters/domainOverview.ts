// The patient page's domain overview: every value of a record, placed in its domain by the KPI
// catalog, with the counts a clinician reads before a visit. Everything here is counted or
// copied from recorded values — a value's position against its laboratory's own interval
// (lib/referencePosition), a change the API computed between comparable values, the time a
// value was received. Nothing is rated, merged into a domain status, or scored (ADR-0003). The
// only verdicts shown are the clinician's own, quoted from the latest interpretation run.
//
// Grouping comes from the catalog (`kpi_primary_domain`), not from the values a run cites: a
// record without a run still shows its values per domain.
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/domain-overview.spec.ts).

import type { CoreKpi, DomainMatrixView, TimelinePoint } from "../api";
import { CLINIC_TIME_ZONE } from "../clinicTime";
import {
  referencePosition,
  type ReferencePosition,
} from "../referencePosition";

// The six domains in the founder-approved order (ADR-0003).
export const DOMAIN_ORDER = [
  "metabolic",
  "immune_inflammation",
  "cardiovascular",
  "neurocognitive",
  "musculoskeletal",
  "regenerative_capacity",
] as const;

// The four counts before a visit; each is also a filter of the lists below it.
export type PrepFilter = "since_run" | "outside" | "pending" | "missing";
export const PREP_FILTERS: readonly PrepFilter[] = [
  "since_run",
  "outside",
  "pending",
  "missing",
];

export interface ValueView {
  id: string;
  // The source's name for the value, as written.
  name: string;
  observedAt: string;
  // The same instant in milliseconds, for drawing it on a time axis.
  observedMs: number;
  dateOnly: boolean;
  // The day of the sample as the clinic reads it ("02.03.2026"); a date-only value keeps its date.
  observedDay: string;
  // Whole days from the sample to the moment the page was put together.
  ageDays: number;
  receivedAt: string;
  // The number the platform holds and its unit; null when the source wrote no one number.
  value: string | null;
  unit: string | null;
  originalValue: string;
  originalUnit: string | null;
  converted: boolean;
  referenceLow: string | null;
  referenceHigh: string | null;
  status: string;
  // A published laboratory correction replaced it, or it was derived from a value that was.
  superseded: boolean;
  inputReplaced: boolean;
  // Published and still standing: the only kind of value that counts as a marker's latest.
  standing: boolean;
  // The change the API computed against the previous comparable value, if any.
  delta: string | null;
  previousId: string | null;
  comparability: string | null;
  comparabilityReason: string | null;
  // Stated for a standing value only; anything else is not evaluated.
  position: ReferencePosition;
  // Received after the latest interpretation run was recorded (false without a run).
  receivedAfterRun: boolean;
}

export interface MarkerSeries {
  kpiCode: string;
  name: string;
  core: boolean;
  primaryDomain: string;
  secondaryDomains: string[];
  // Oldest first, as the API orders them.
  values: ValueView[];
  latest: ValueView | null;
  pending: number;
  receivedSinceRun: number;
  outside: boolean;
  corrected: boolean;
}

export interface MissingMarker {
  code: string;
  // The catalog's (English) name: no source has named it for this record.
  name: string;
  measurementClass: string;
}

export type DomainRow =
  | { kind: "series"; series: MarkerSeries }
  | { kind: "missing"; marker: MissingMarker };

export interface DomainFacts {
  coreTotal: number;
  coreWithValue: number;
  outside: number;
  pending: number;
  receivedSinceRun: number;
  latestObservedAt: string | null;
  latestObservedDay: string | null;
}

export interface DomainVerdict {
  cisStatus: string;
  actionabilityClass: string;
  followupAdequacy: string;
  reviewed: boolean;
  // The run cites a value a laboratory correction has since replaced.
  citesReplaced: boolean;
}

export interface DomainSection {
  axis: string;
  // Core markers in catalog order — with their values, or as missing — then the domain's other
  // markers by name.
  rows: DomainRow[];
  // Markers of another domain that the catalog links here too. Shown, never counted here.
  alsoRelevant: MarkerSeries[];
  facts: DomainFacts;
  verdict: DomainVerdict | null;
}

export interface TimeAxis {
  start: number;
  end: number;
}

export interface DomainOverview {
  runNumber: number | null;
  runRecordedAt: string | null;
  // The day the run was recorded, as the clinic reads it.
  runRecordedDay: string | null;
  // One calendar axis for every history on the page, from shortly before the oldest value
  // to the moment the page was put together; null without a value.
  timeAxis: TimeAxis | null;
  domains: DomainSection[];
  // Values without a catalog marker: they belong to no domain until a person maps them.
  unassigned: ValueView[];
  // since_run is null without a run: nothing was interpreted, so nothing came after it.
  counts: Record<PrepFilter, number | null>;
}

const DAY_IN_CLINIC = new Intl.DateTimeFormat("de-DE", {
  timeZone: CLINIC_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});
// A date-only value is stored at UTC midnight of its date: read in UTC, it keeps that date.
const DAY_AS_GIVEN = new Intl.DateTimeFormat("de-DE", {
  timeZone: "UTC",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

export function dayOf(iso: string, dateOnly: boolean): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  return (dateOnly ? DAY_AS_GIVEN : DAY_IN_CLINIC).format(at);
}

// The direction of a change the API computed: an arrow beside the number, never a judgement.
export function deltaDirection(delta: string | null): "up" | "down" | "none" {
  const n = delta == null ? NaN : Number(delta);
  if (!Number.isFinite(n) || n === 0) return "none";
  return n > 0 ? "up" : "down";
}

function time(iso: string): number {
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? t : 0;
}

function toValue(
  p: TimelinePoint,
  runAt: number | null,
  now: number,
): ValueView {
  const superseded = p.superseded_by_observation_id != null;
  const inputReplaced = p.input_replaced === true;
  const standing =
    p.review_status === "published" && !superseded && !inputReplaced;
  return {
    id: p.observation_id,
    name: p.original_name,
    observedAt: p.observed_at,
    observedMs: time(p.observed_at),
    dateOnly: p.observed_at_is_date_only,
    observedDay: dayOf(p.observed_at, p.observed_at_is_date_only),
    ageDays: Math.max(0, Math.floor((now - time(p.observed_at)) / 86_400_000)),
    receivedAt: p.received_at,
    value: p.value ?? null,
    unit: p.unit ?? null,
    originalValue: p.original_value,
    originalUnit: p.original_unit ?? null,
    converted: p.converted,
    referenceLow: p.reference_low ?? null,
    referenceHigh: p.reference_high ?? null,
    status: p.review_status,
    superseded,
    inputReplaced,
    standing,
    delta: p.delta_vs_previous ?? null,
    previousId: p.previous_observation_id ?? null,
    comparability: p.comparability ?? null,
    comparabilityReason: p.comparability_reason ?? null,
    position: standing
      ? referencePosition(p.value, p.reference_low, p.reference_high)
      : "not_evaluable",
    receivedAfterRun:
      runAt != null &&
      p.review_status !== "rejected" &&
      time(p.received_at) > runAt,
  };
}

function isOutside(v: ValueView): boolean {
  return v.standing && (v.position === "above" || v.position === "below");
}

function toSeries(
  kpiCode: string,
  points: TimelinePoint[],
  values: ValueView[],
  core: boolean,
): MarkerSeries {
  let latest: ValueView | null = null;
  for (const v of values) if (v.standing) latest = v;
  const named = latest ?? values[values.length - 1];
  const first = points[0];
  return {
    kpiCode,
    name: named?.name ?? kpiCode,
    core,
    primaryDomain: first?.kpi_primary_domain ?? "",
    secondaryDomains: first?.kpi_secondary_domains ?? [],
    values,
    latest,
    pending: values.filter((v) => v.status === "pending").length,
    receivedSinceRun: values.filter((v) => v.receivedAfterRun).length,
    outside: latest != null && isOutside(latest),
    corrected: values.some((v) => v.superseded),
  };
}

export function presentDomainOverview(
  timeline: TimelinePoint[],
  catalog: CoreKpi[],
  matrix: DomainMatrixView | null,
  now: number = Date.now(),
): DomainOverview {
  const runRecordedAt = matrix?.recorded_at ?? null;
  const runAt = runRecordedAt != null ? time(runRecordedAt) : null;
  const coreCodes = new Set(catalog.map((k) => k.code));

  // One series per catalog marker; values without one are unassigned.
  const byCode = new Map<
    string,
    { points: TimelinePoint[]; values: ValueView[] }
  >();
  const unassigned: ValueView[] = [];
  for (const p of timeline) {
    const value = toValue(p, runAt, now);
    if (p.kpi_code == null || p.kpi_primary_domain == null) {
      unassigned.push(value);
      continue;
    }
    const entry = byCode.get(p.kpi_code) ?? { points: [], values: [] };
    entry.points.push(p);
    entry.values.push(value);
    byCode.set(p.kpi_code, entry);
  }
  const series = new Map<string, MarkerSeries>();
  for (const [code, { points, values }] of byCode) {
    series.set(code, toSeries(code, points, values, coreCodes.has(code)));
  }
  const allSeries = Array.from(series.values());

  const domains: DomainSection[] = DOMAIN_ORDER.map((axis) => {
    const core = catalog.filter((k) => k.primary_domain_axis === axis);
    const rows: DomainRow[] = core.map((k) => {
      const s = series.get(k.code);
      return s
        ? { kind: "series", series: s }
        : {
            kind: "missing",
            marker: {
              code: k.code,
              name: k.display_name,
              measurementClass: k.measurement_class,
            },
          };
    });
    const others = allSeries
      .filter((s) => !s.core && s.primaryDomain === axis)
      .sort((a, b) => a.name.localeCompare(b.name, "de"));
    for (const s of others) rows.push({ kind: "series", series: s });

    const own = allSeries.filter((s) => s.primaryDomain === axis);
    let newest: ValueView | null = null;
    for (const s of own) {
      if (
        s.latest &&
        (newest == null || time(s.latest.observedAt) > time(newest.observedAt))
      )
        newest = s.latest;
    }
    const verdict = matrix?.domains.find((d) => d.domain_axis === axis);
    return {
      axis,
      rows,
      alsoRelevant: allSeries
        .filter(
          (s) => s.primaryDomain !== axis && s.secondaryDomains.includes(axis),
        )
        .sort((a, b) => a.name.localeCompare(b.name, "de")),
      facts: {
        coreTotal: core.length,
        coreWithValue: core.filter((k) => series.get(k.code)?.latest != null)
          .length,
        outside: own.filter((s) => s.outside).length,
        pending: own.reduce((n, s) => n + s.pending, 0),
        receivedSinceRun: own.reduce((n, s) => n + s.receivedSinceRun, 0),
        latestObservedAt: newest?.observedAt ?? null,
        latestObservedDay: newest?.observedDay ?? null,
      },
      verdict: verdict
        ? {
            cisStatus: verdict.cis_status,
            actionabilityClass: verdict.actionability_class,
            followupAdequacy: verdict.followup_adequacy,
            reviewed: verdict.review_status === "clinician_reviewed",
            citesReplaced: verdict.cells.some((c) =>
              c.evidence.some((e) => e.superseded === true),
            ),
          }
        : null,
    };
  });

  const everyValue = [...allSeries.flatMap((s) => s.values), ...unassigned];
  const drawn = everyValue.filter((v) => v.status !== "rejected");
  let timeAxis: TimeAxis | null = null;
  if (drawn.length > 0) {
    const oldest = Math.min(...drawn.map((v) => v.observedMs));
    const end = Math.max(now, ...drawn.map((v) => v.observedMs));
    // A margin before the oldest value: at least a month, so its mark is not on the edge.
    const margin = Math.max(30 * 86_400_000, (end - oldest) * 0.04);
    timeAxis = { start: oldest - margin, end };
  }
  return {
    runNumber: matrix?.run_number ?? null,
    runRecordedAt,
    runRecordedDay: runRecordedAt != null ? dayOf(runRecordedAt, false) : null,
    timeAxis,
    domains,
    unassigned,
    counts: {
      since_run:
        runAt == null
          ? null
          : everyValue.filter((v) => v.receivedAfterRun).length,
      outside:
        allSeries.filter((s) => s.outside).length +
        unassigned.filter(isOutside).length,
      pending: everyValue.filter((v) => v.status === "pending").length,
      missing: domains.reduce(
        (n, d) => n + d.facts.coreTotal - d.facts.coreWithValue,
        0,
      ),
    },
  };
}

// Whether a row of a domain list, or an unassigned value, belongs under a filter. The counts
// above and these predicates say the same thing: every value or marker a count counts is in a
// row its filter shows, and every row it shows holds one.
export function rowMatches(row: DomainRow, filter: PrepFilter | null): boolean {
  if (filter == null) return true;
  if (row.kind === "missing") return filter === "missing";
  const s = row.series;
  if (filter === "since_run") return s.receivedSinceRun > 0;
  if (filter === "outside") return s.outside;
  if (filter === "pending") return s.pending > 0;
  return s.core && s.latest == null;
}

export function valueMatches(v: ValueView, filter: PrepFilter | null): boolean {
  if (filter == null) return true;
  if (filter === "since_run") return v.receivedAfterRun;
  if (filter === "outside") return isOutside(v);
  if (filter === "pending") return v.status === "pending";
  return false;
}
