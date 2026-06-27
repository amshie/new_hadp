// VitaBahn dashboard presenters (ADR-0006 / real-data path). Maps the REAL, tenant-scoped
// API responses (WorklistRow[] + PatientOut[]) into render-ready view shapes for the
// /overview and /patients screens. ALL display formatting lives here; the API returns
// codes/raw fields/timestamps. Everything here is a deterministic count/format over real
// data — no score, no risk, no quality engine (those have no backend; see ADR-0006).

import type { Coverage, Patient, Throughput, WorklistRow } from "@/lib/api";

export interface BadgeMeta {
  label: string;
  fg: string;
  bg: string;
  bd: string;
}

// Workflow status of the latest report — a closed ReportStatus enum, never a clinical state.
const STATUS_META: Record<string, BadgeMeta> = {
  draft_generated: {
    label: "In Prüfung",
    fg: "var(--amber-500)",
    bg: "rgba(201,136,28,0.12)",
    bd: "rgba(201,136,28,0.30)",
  },
  draft_edited: {
    label: "In Prüfung",
    fg: "var(--amber-500)",
    bg: "rgba(201,136,28,0.12)",
    bd: "rgba(201,136,28,0.30)",
  },
  approved: {
    label: "Genehmigt",
    fg: "var(--brand)",
    bg: "var(--brand-soft)",
    bd: "var(--brand-border)",
  },
  released: {
    label: "Freigegeben",
    fg: "var(--vital-500)",
    bg: "rgba(20,169,130,0.12)",
    bd: "rgba(20,169,130,0.32)",
  },
  rejected: {
    label: "Abgelehnt",
    fg: "var(--rose-500)",
    bg: "rgba(194,74,74,0.12)",
    bd: "rgba(194,74,74,0.30)",
  },
};
const NO_REPORT: BadgeMeta = {
  label: "Kein Entwurf",
  fg: "var(--text-muted)",
  bg: "var(--surface-sunken)",
  bd: "var(--border-default)",
};

function statusMeta(reportStatus: string | null | undefined): BadgeMeta {
  if (!reportStatus) return NO_REPORT;
  return STATUS_META[reportStatus] ?? NO_REPORT;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0] ?? "");
  return letters.join("").toUpperCase() || "–";
}

function ageYears(dob: string | null | undefined): string {
  if (!dob) return "—";
  const birth = new Date(dob);
  if (!Number.isFinite(birth.getTime())) return "—";
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
  return String(age);
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "gerade eben";
  if (mins < 60) return `vor ${mins} Min.`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `vor ${hours} Std.`;
  const days = Math.round(hours / 24);
  if (days === 1) return "gestern";
  return `vor ${days} T`;
}

const DRAFT = (s: string | null | undefined) =>
  s === "draft_generated" || s === "draft_edited";

export interface WorkRowView {
  patientId: string;
  name: string;
  initials: string;
  ref: string;
  assessment: string;
  statusLabel: string;
  statusBadge: BadgeMeta;
  updatedLabel: string;
  reviewUrl: string | null;
  hasReport: boolean;
}

export interface OverviewView {
  kpis: {
    openReviews: number;
    approved: number;
    released: number;
    patients: number;
  };
  rows: WorkRowView[];
  statusSnapshot: StatusSnapshotView;
}

export function presentOverview(
  rows: WorklistRow[],
  patients: Patient[],
): OverviewView {
  const work: WorkRowView[] = rows.map((r) => {
    const sm = statusMeta(r.report_status);
    return {
      patientId: r.patient_id,
      name: r.display_name,
      initials: initials(r.display_name),
      ref: r.external_ref ?? "—",
      assessment: r.report_id
        ? `Bericht · v${r.version_no ?? 1}`
        : "Kein Entwurf",
      statusLabel: sm.label,
      statusBadge: sm,
      updatedLabel: relativeTime(r.updated_at),
      reviewUrl: r.report_id
        ? `/patients/${r.patient_id}/assessments/${r.report_id}`
        : null,
      hasReport: r.report_id != null,
    };
  });
  return {
    kpis: {
      openReviews: rows.filter((r) => DRAFT(r.report_status)).length,
      approved: rows.filter((r) => r.report_status === "approved").length,
      released: rows.filter((r) => r.report_status === "released").length,
      patients: patients.length,
    },
    rows: work,
    statusSnapshot: presentStatusSnapshot(rows),
  };
}

// --- Berichtsstatus snapshot (real, from the worklist we already load) -----------------------
// A current-bestand distribution of the latest report status across the tenant's patients. This
// is a SNAPSHOT (Momentaufnahme), deliberately NOT a throughput time series — a true rate over
// time needs report_versions timestamps (a deferred backend slice). Honest label, real counts.

export interface StatusBucket {
  key: string;
  label: string;
  count: number;
  share: number; // 0..1 of all rows; 0 when there are no rows
  color: string;
}

export interface StatusSnapshotView {
  total: number;
  buckets: StatusBucket[];
}

export function presentStatusSnapshot(rows: WorklistRow[]): StatusSnapshotView {
  const total = rows.length;
  const count = (pred: (r: WorklistRow) => boolean) => rows.filter(pred).length;
  const raw: { key: string; label: string; count: number; color: string }[] = [
    {
      key: "offen",
      label: "In Prüfung",
      count: count((r) => DRAFT(r.report_status)),
      color: "var(--amber-500)",
    },
    {
      key: "genehmigt",
      label: "Genehmigt",
      count: count((r) => r.report_status === "approved"),
      color: "var(--brand)",
    },
    {
      key: "freigegeben",
      label: "Freigegeben",
      count: count((r) => r.report_status === "released"),
      color: "var(--vital-500)",
    },
    {
      key: "abgelehnt",
      label: "Abgelehnt",
      count: count((r) => r.report_status === "rejected"),
      color: "var(--rose-500)",
    },
    {
      key: "kein",
      label: "Kein Entwurf",
      count: count((r) => r.report_id == null),
      color: "var(--text-faint)",
    },
  ];
  return {
    total,
    buckets: raw.map((b) => ({
      ...b,
      share: total > 0 ? b.count / total : 0,
    })),
  };
}

// --- Review-Durchsatz (real per-day report-version throughput; ADR-0006 follow-up) ------------
// Erstellt = versions created that day; Signiert = versions approved (signed off) that day. Both
// from persisted ReportVersion timestamps — a real rate over time, no fabricated trend. The view
// carries the full window (default 30 days); the tile slices it to the selected 14/30 sub-window
// and recomputes totals from the slice.

export interface ThroughputPoint {
  date: string; // ISO date (YYYY-MM-DD)
  label: string; // short "D.M." for the axis
  created: number;
  signed: number;
}

export interface ThroughputChartView {
  points: ThroughputPoint[];
}

function shortDay(iso: string): string {
  // Parse the date-only "YYYY-MM-DD" by component. `new Date(iso)` would parse it as UTC midnight
  // and `.getDate()` would render it in the viewer's local zone — off-by-one west of UTC, which
  // would disagree with the raw ISO shown in the accessible data table.
  const [, mm, dd] = iso.split("-");
  const m = Number(mm);
  const d = Number(dd);
  if (!Number.isFinite(m) || !Number.isFinite(d)) return "";
  return `${d}.${m}.`;
}

export function presentThroughput(t: Throughput): ThroughputChartView {
  return {
    points: t.buckets.map((b) => ({
      date: b.date,
      label: shortDay(b.date),
      created: b.created,
      signed: b.signed,
    })),
  };
}

// --- Datenlage / coverage (real, tenant-wide observation counts; ADR-0006) -------------------
// Deterministic counts + freshness over real observations. NOT a clinical data-quality score
// (no quality model exists — Gate G1). publishedPct/referencePct are coverage ratios, never a
// merged "quality %".

export interface CoverageView {
  total: number;
  published: number;
  withReference: number;
  publishedPct: number; // 0..100, rounded
  referencePct: number; // 0..100, rounded
  latestAgeLabel: string;
}

export function presentCoverage(c: Coverage): CoverageView {
  const pct = (n: number) =>
    c.total > 0 ? Math.round((n * 100) / c.total) : 0;
  return {
    total: c.total,
    published: c.published,
    withReference: c.with_reference,
    publishedPct: pct(c.published),
    referencePct: pct(c.with_reference),
    latestAgeLabel: c.latest_observed_at
      ? relativeTime(c.latest_observed_at)
      : "—",
  };
}

export interface DirectoryRowView {
  patientId: string;
  name: string;
  initials: string;
  ref: string;
  age: string;
  statusLabel: string;
  statusBadge: BadgeMeta;
  lastAssessment: string;
}

export interface DirectoryView {
  total: number;
  withReport: number;
  openAssessments: number;
  rows: DirectoryRowView[];
}

export function presentDirectory(
  patients: Patient[],
  rows: WorklistRow[],
): DirectoryView {
  const byPatient = new Map<string, WorklistRow>();
  for (const r of rows) byPatient.set(r.patient_id, r);
  const directory: DirectoryRowView[] = patients.map((p) => {
    const r = byPatient.get(p.id);
    const sm = statusMeta(r?.report_status);
    return {
      patientId: p.id,
      name: p.display_name,
      initials: initials(p.display_name),
      ref: p.external_ref ?? "—",
      age: ageYears(p.date_of_birth),
      statusLabel: sm.label,
      statusBadge: sm,
      lastAssessment: r ? relativeTime(r.updated_at) : "—",
    };
  });
  return {
    total: patients.length,
    withReport: rows.filter((r) => r.report_id != null).length,
    openAssessments: rows.filter((r) => DRAFT(r.report_status)).length,
    rows: directory,
  };
}
