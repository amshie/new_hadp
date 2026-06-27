// VitaBahn patient Detail presenter (ADR-0005 / real-data path). Reuses presentReview (the
// authoritative interpretation + observation + report mapping) and adds a real, deterministic
// DATA-COMPLETENESS stat over the observation timeline. This is the compliant, real replacement
// for the comp's invented "data-quality 94%" gauge: counts/freshness over real observations, NOT
// a clinical-quality score. The observation Status is the verdict-free positional Lage (computed
// in presentReview via referencePosition), never a Normal/Grenzwertig/Auffällig verdict.

import type {
  DomainMatrixView,
  Patient,
  ReportView,
  TimelinePoint,
} from "@/lib/api";

import { presentReview, type ReviewView } from "./review";

export interface Completeness {
  total: number;
  published: number;
  withReference: number;
  latestAgeDays: number | null;
}

export interface DetailView {
  review: ReviewView;
  completeness: Completeness;
  // Link to the authoritative review surface (where approve/release live); null if no report.
  reportLink: string | null;
}

export function dataCompleteness(points: TimelinePoint[]): Completeness {
  const total = points.length;
  const published = points.filter(
    (p) => p.review_status === "published",
  ).length;
  const withReference = points.filter(
    (p) => p.reference_low != null || p.reference_high != null,
  ).length;
  let latestAgeDays: number | null = null;
  if (points.length) {
    const newest = Math.max(
      ...points.map((p) => new Date(p.observed_at).getTime()),
    );
    latestAgeDays = Math.max(0, Math.round((Date.now() - newest) / 86400000));
  }
  return { total, published, withReference, latestAgeDays };
}

export function presentDetail(
  patient: Patient,
  report: ReportView,
  points: TimelinePoint[],
  matrix: DomainMatrixView | null,
): DetailView {
  return {
    review: presentReview(patient, report, points, matrix),
    completeness: dataCompleteness(points),
    reportLink: report.report_id
      ? `/patients/${patient.id}/assessments/${report.report_id}`
      : null,
  };
}
