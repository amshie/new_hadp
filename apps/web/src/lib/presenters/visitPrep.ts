// The page before a visit (docs/notes/0022): what has happened to a record since the latest
// interpretation run, as facts a clinician reads in two minutes. Every line is counted or
// copied from the domain overview — a value received after the run, a marker whose latest
// value sits on another side of its laboratory's interval than the one before, a core marker
// whose latest value is older than a stated number of days, a core marker with no value, a
// domain the run left without a verdict. Nothing is rated, ranked by urgency, or summed into a
// score (ADR-0003): the order is the catalog's, and the only verdicts named are the clinician's.
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/visit-prep.spec.ts).

import type { ReferencePosition } from "../referencePosition";
import type { DomainOverview, MarkerSeries, ValueView } from "./domainOverview";

// After this many days a core marker's latest value is listed as old. A stated constant, said
// on the page beside the list; a clinic's own setting is a later step (CLAUDE.md, "data older
// than a configured duration").
export const STALE_AFTER_DAYS = 180;

export interface PrepValue {
  // The catalog marker, or null for a value no catalog marker names yet.
  code: string | null;
  name: string;
  axis: string | null;
  valueId: string;
  value: string | null;
  unit: string | null;
  referenceLow: string | null;
  referenceHigh: string | null;
  observedDay: string;
  position: ReferencePosition;
  // Computed by the platform from other values (observedDay: the latest of theirs), not measured.
  derived: boolean;
}

export interface PrepMove {
  code: string;
  name: string;
  axis: string;
  from: ReferencePosition;
  to: ReferencePosition;
  previousId: string;
  previousDay: string;
  latestId: string;
  latestDay: string;
  value: string | null;
  unit: string | null;
  referenceLow: string | null;
  referenceHigh: string | null;
}

export interface PrepStale {
  code: string;
  name: string;
  axis: string;
  latestId: string;
  observedDay: string;
  ageDays: number;
}

export interface PrepMissing {
  code: string;
  name: string;
  axis: string;
}

// One standing value of a marker on its trend: where it lies against its interval, and
// whether a line may join it to the value before it (the API found the two comparable).
export interface PrepTrendPoint {
  id: string;
  day: string;
  position: ReferencePosition;
  linked: boolean;
}

// A marker whose latest standing value lies outside its laboratory's interval, with every
// standing value of the marker behind it.
export interface PrepOutside extends PrepValue {
  code: string;
  axis: string;
  trend: PrepTrendPoint[];
}

// What stands today (docs/notes/0025): every marker's latest standing value, counted by
// where it lies against the laboratory's interval. Counts and positions, never a rating.
export interface PrepToday {
  // Markers with a published standing value, the values no catalog marker names included.
  withValue: number;
  outside: PrepOutside[];
  within: number;
  // Published, but with no interval of the source to lie against.
  noReference: number;
  // The newest sample day among them; null without a value.
  latestDay: string | null;
}

// One domain's line beside the clinician's latest verdict: how many of its core markers
// have a value, how many of its markers lie outside their interval, and the verdict itself
// (null when the run recorded none, or without a run).
export interface PrepDomain {
  axis: string;
  coreTotal: number;
  coreWithValue: number;
  outside: number;
  verdict: {
    cisStatus: string;
    actionabilityClass: string;
    followupAdequacy: string;
    reviewed: boolean;
  } | null;
}

export interface PrepCount {
  key: string;
  count: number;
}

export interface VisitPrep {
  // The run the facts are "since"; null when the record has no interpretation yet — then
  // there is no "new" and no "moved", only what stands today.
  run: { number: number; day: string } | null;
  today: PrepToday;
  domains: PrepDomain[];
  // The old and the missing core markers, grouped: by sample day (most first) and by domain
  // (the catalog's order), so a page can say "17, all from 10.06.2025" before it lists them.
  staleByDay: PrepCount[];
  staleByAxis: PrepCount[];
  missingByAxis: PrepCount[];
  // Published values received after the run, in the order of the domain lists.
  newValues: PrepValue[];
  // Of those, how many lie outside their laboratory's interval.
  newOutside: number;
  // Markers whose latest value, received after the run, lies on another side of the interval
  // than the standing value before it.
  moved: PrepMove[];
  // Core markers whose latest value is older than `staleAfterDays`.
  stale: PrepStale[];
  // Core markers of the catalog with no published value.
  missing: PrepMissing[];
  // Values waiting in the review queue (not published, so in no list above).
  pending: number;
  // Values no catalog marker names: they belong to no domain until a person maps them.
  unassigned: number;
  // Domains the run recorded no verdict for (empty without a run).
  domainsWithoutVerdict: string[];
  // Domains whose verdict cites a value a laboratory correction has since replaced.
  domainsCitingReplaced: string[];
  staleAfterDays: number;
  // Nothing to list at all: no new value, nothing moved, nothing old, missing or waiting.
  quiet: boolean;
}

const EVALUABLE = new Set<ReferencePosition>(["above", "below", "within"]);

function asPrepValue(
  s: MarkerSeries | null,
  v: ValueView,
  axis: string | null,
): PrepValue {
  return {
    code: s?.kpiCode ?? null,
    name: s?.name ?? v.name,
    axis,
    valueId: v.id,
    value: v.value,
    unit: v.unit,
    referenceLow: v.referenceLow,
    referenceHigh: v.referenceHigh,
    observedDay: v.observedDay,
    position: v.position,
    derived: v.derivation != null,
  };
}

// The standing value before the latest one, if any.
function previousStanding(s: MarkerSeries): ValueView | null {
  const standing = s.values.filter((v) => v.standing);
  return standing.length >= 2 ? (standing[standing.length - 2] ?? null) : null;
}

export function presentVisitPrep(
  overview: DomainOverview,
  staleAfterDays: number = STALE_AFTER_DAYS,
): VisitPrep {
  const hasRun = overview.runNumber != null;
  const run =
    overview.runNumber != null && overview.runRecordedDay != null
      ? { number: overview.runNumber, day: overview.runRecordedDay }
      : null;

  const newValues: PrepValue[] = [];
  const moved: PrepMove[] = [];
  const stale: PrepStale[] = [];
  const missing: PrepMissing[] = [];

  for (const domain of overview.domains) {
    for (const row of domain.rows) {
      if (row.kind === "missing") {
        missing.push({
          code: row.marker.code,
          name: row.marker.name,
          axis: domain.axis,
        });
        continue;
      }
      const s = row.series;
      if (hasRun) {
        for (const v of s.values) {
          if (v.standing && v.receivedAfterRun)
            newValues.push(asPrepValue(s, v, domain.axis));
        }
        const latest = s.latest;
        const previous = latest ? previousStanding(s) : null;
        if (
          latest &&
          previous &&
          latest.receivedAfterRun &&
          EVALUABLE.has(latest.position) &&
          EVALUABLE.has(previous.position) &&
          latest.position !== previous.position
        ) {
          moved.push({
            code: s.kpiCode,
            name: s.name,
            axis: domain.axis,
            from: previous.position,
            to: latest.position,
            previousId: previous.id,
            previousDay: previous.observedDay,
            latestId: latest.id,
            latestDay: latest.observedDay,
            value: latest.value,
            unit: latest.unit,
            referenceLow: latest.referenceLow,
            referenceHigh: latest.referenceHigh,
          });
        }
      }
      if (s.core && s.latest && s.latest.ageDays > staleAfterDays) {
        stale.push({
          code: s.kpiCode,
          name: s.name,
          axis: domain.axis,
          latestId: s.latest.id,
          observedDay: s.latest.observedDay,
          ageDays: s.latest.ageDays,
        });
      }
    }
  }
  if (hasRun) {
    for (const v of overview.unassigned) {
      if (v.standing && v.receivedAfterRun)
        newValues.push(asPrepValue(null, v, null));
    }
  }

  const pending = overview.counts.pending ?? 0;
  const unassigned = overview.unassigned.filter(
    (v) => v.status !== "rejected",
  ).length;

  // What stands today, per marker; the unassigned values count one each.
  const outside: PrepOutside[] = [];
  let within = 0;
  let noReference = 0;
  let withValue = 0;
  let latestMs = -Infinity;
  let latestDay: string | null = null;
  const tally = (v: ValueView) => {
    withValue += 1;
    if (v.observedMs > latestMs) {
      latestMs = v.observedMs;
      latestDay = v.observedDay;
    }
    if (v.position === "within") within += 1;
    else if (v.position !== "above" && v.position !== "below") noReference += 1;
  };
  for (const domain of overview.domains) {
    for (const row of domain.rows) {
      if (row.kind !== "series") continue;
      const s = row.series;
      const latest = s.latest;
      if (!latest) continue;
      tally(latest);
      if (latest.position === "above" || latest.position === "below") {
        outside.push({
          ...asPrepValue(s, latest, domain.axis),
          code: s.kpiCode,
          axis: domain.axis,
          trend: s.values
            .filter((v) => v.standing)
            .map((v) => ({
              id: v.id,
              day: v.observedDay,
              position: v.position,
              linked: v.previousId != null && v.comparability === "comparable",
            })),
        });
      }
    }
  }
  for (const v of overview.unassigned) if (v.standing) tally(v);

  const domains: PrepDomain[] = overview.domains.map((d) => ({
    axis: d.axis,
    coreTotal: d.facts.coreTotal,
    coreWithValue: d.facts.coreWithValue,
    outside: d.facts.outside,
    verdict: d.verdict
      ? {
          cisStatus: d.verdict.cisStatus,
          actionabilityClass: d.verdict.actionabilityClass,
          followupAdequacy: d.verdict.followupAdequacy,
          reviewed: d.verdict.reviewed,
        }
      : null,
  }));

  const countBy = <T>(items: T[], key: (item: T) => string): PrepCount[] => {
    const out: PrepCount[] = [];
    for (const item of items) {
      const k = key(item);
      const found = out.find((c) => c.key === k);
      if (found) found.count += 1;
      else out.push({ key: k, count: 1 });
    }
    return out;
  };
  const staleByDay = countBy(stale, (x) => x.observedDay).sort(
    (a, b) => b.count - a.count,
  );
  const domainsWithoutVerdict = hasRun
    ? overview.domains.filter((d) => d.verdict == null).map((d) => d.axis)
    : [];
  const domainsCitingReplaced = overview.domains
    .filter((d) => d.verdict?.citesReplaced === true)
    .map((d) => d.axis);

  return {
    run,
    today: { withValue, outside, within, noReference, latestDay },
    domains,
    staleByDay,
    staleByAxis: countBy(stale, (x) => x.axis),
    missingByAxis: countBy(missing, (x) => x.axis),
    newValues,
    newOutside: newValues.filter(
      (v) => v.position === "above" || v.position === "below",
    ).length,
    moved,
    stale,
    missing,
    pending,
    unassigned,
    domainsWithoutVerdict,
    domainsCitingReplaced,
    staleAfterDays,
    quiet:
      newValues.length === 0 &&
      moved.length === 0 &&
      stale.length === 0 &&
      missing.length === 0 &&
      pending === 0 &&
      unassigned === 0 &&
      domainsWithoutVerdict.length === 0 &&
      domainsCitingReplaced.length === 0,
  };
}
