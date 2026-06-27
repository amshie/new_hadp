// VitaBahn dashboard presenters (ADR-0005 / real-data path). Maps the REAL, tenant-scoped
// API responses (WorklistRow[] + PatientOut[]) into render-ready view shapes for the
// /overview and /patients screens. ALL display formatting lives here; the API returns
// codes/raw fields/timestamps. Everything here is a deterministic count/format over real
// data — no score, no risk, no quality engine (those have no backend; see ADR-0005).

import type { Patient, WorklistRow } from "@/lib/api";

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
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
  return String(age);
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
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
  synthetic: boolean;
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
      synthetic: p.is_synthetic,
    };
  });
  return {
    total: patients.length,
    withReport: rows.filter((r) => r.report_id != null).length,
    openAssessments: rows.filter((r) => DRAFT(r.report_status)).length,
    rows: directory,
  };
}
