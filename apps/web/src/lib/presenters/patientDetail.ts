// VitaBahn patient Detail presenter (ADR-0006 / real-data path). Reuses presentReview (the
// authoritative interpretation + observation + report mapping) and adds a real, deterministic
// DATA-COMPLETENESS stat over the observation timeline. This is the compliant, real replacement
// for the comp's invented "data-quality 94%" gauge: counts/freshness over real observations, NOT
// a clinical-quality score. The observation Status is the verdict-free positional Lage (computed
// in presentReview via referencePosition), never a Normal/Grenzwertig/Auffällig verdict.

import type {
  CoreKpi,
  DomainMatrixView,
  Patient,
  ReportView,
  TimelinePoint,
} from "@/lib/api";

import { presentDomainOverview, type DomainOverview } from "./domainOverview";
import { presentVisitPrep, type VisitPrep } from "./visitPrep";
import { presentReview, type ReviewView } from "./review";

export interface Completeness {
  total: number;
  published: number;
  withReference: number;
  latestAgeDays: number | null;
}

export interface DetailView {
  patientId: string;
  review: ReviewView;
  // The values per domain, placed by the catalog, with the counts before a visit.
  overview: DomainOverview;
  // The facts since the latest interpretation run, one line each (docs/notes/0022).
  prep: VisitPrep;
  completeness: Completeness;
  // Link to the authoritative review surface (where approve/release live); null if no report.
  reportLink: string | null;
  // True once a gated erasure has tombstoned this record (identity blanked, artifacts deleted).
  erased: boolean;
}

// Over the values sources reported: a value the platform computed from them adds no data,
// has no reference interval of its own, and was not measured.
export function dataCompleteness(timeline: TimelinePoint[]): Completeness {
  const points = timeline.filter((p) => p.derived !== true);
  const total = points.length;
  const published = points.filter(
    (p) => p.review_status === "published",
  ).length;
  const withReference = points.filter(
    (p) => p.reference_low != null || p.reference_high != null,
  ).length;
  let latestAgeDays: number | null = null;
  const times = points
    .map((p) => new Date(p.observed_at).getTime())
    .filter((t) => Number.isFinite(t));
  if (times.length) {
    const newest = Math.max(...times);
    latestAgeDays = Math.max(0, Math.round((Date.now() - newest) / 86400000));
  }
  return { total, published, withReference, latestAgeDays };
}

export function presentDetail(
  patient: Patient,
  report: ReportView,
  points: TimelinePoint[],
  matrix: DomainMatrixView | null,
  catalog: CoreKpi[],
): DetailView {
  const overview = presentDomainOverview(points, catalog, matrix);
  return {
    patientId: patient.id,
    review: presentReview(patient, report, points, matrix),
    overview,
    prep: presentVisitPrep(overview),
    completeness: dataCompleteness(points),
    reportLink: report.report_id
      ? `/patients/${patient.id}/assessments/${report.report_id}`
      : null,
    erased: patient.erased === true,
  };
}
