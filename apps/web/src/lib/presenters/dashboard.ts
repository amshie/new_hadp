// VitaBahn dashboard presenters (ADR-0006 / real-data path). Maps the REAL, tenant-scoped
// API responses (WorklistRow[] + PatientOut[]) into render-ready view shapes for the
// /overview and /patients screens. ALL display formatting lives here; the API returns
// codes/raw fields/timestamps. Everything here is a deterministic count/format over real
// data — no score, no risk, no quality engine (those have no backend; see ADR-0006).

import type { Patient, WorklistRow } from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";

// The wording these presenters need, in the language of the page (lib/i18n).
export type DashboardWording = Messages["dashboard"];

// Where the latest report stands. What a page filters and counts by — never a label, which
// differs by language.
export type StatusGroup =
  | "review"
  | "approved"
  | "released"
  | "rejected"
  | "none";

export interface BadgeMeta {
  label: string;
  fg: string;
  bg: string;
  bd: string;
}

// Workflow status of the latest report — a closed ReportStatus enum, never a clinical state.
const STATUS_GROUP: Record<string, StatusGroup> = {
  draft_generated: "review",
  draft_edited: "review",
  approved: "approved",
  released: "released",
  rejected: "rejected",
};
const GROUP_COLORS: Record<StatusGroup, Omit<BadgeMeta, "label">> = {
  review: {
    fg: "var(--amber-500)",
    bg: "rgba(201,136,28,0.12)",
    bd: "rgba(201,136,28,0.30)",
  },
  approved: {
    fg: "var(--brand)",
    bg: "var(--brand-soft)",
    bd: "var(--brand-border)",
  },
  released: {
    fg: "var(--vital-500)",
    bg: "rgba(20,169,130,0.12)",
    bd: "rgba(20,169,130,0.32)",
  },
  rejected: {
    fg: "var(--rose-500)",
    bg: "rgba(194,74,74,0.12)",
    bd: "rgba(194,74,74,0.30)",
  },
  none: {
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
  },
};

function statusGroup(reportStatus: string | null | undefined): StatusGroup {
  return (reportStatus && STATUS_GROUP[reportStatus]) || "none";
}

function statusMeta(group: StatusGroup, w: DashboardWording): BadgeMeta {
  return { label: w.status[group], ...GROUP_COLORS[group] };
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

function relativeTime(iso: string, w: DashboardWording["time"]): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return w.now;
  if (mins < 60) return fill(w.minutes, { n: mins });
  const hours = Math.round(mins / 60);
  if (hours < 24) return fill(w.hours, { n: hours });
  const days = Math.round(hours / 24);
  if (days === 1) return w.yesterday;
  return fill(w.days, { n: days });
}

const DRAFT = (s: string | null | undefined) =>
  s === "draft_generated" || s === "draft_edited";

export interface WorkRowView {
  patientId: string;
  name: string;
  initials: string;
  ref: string;
  version: number | null;
  group: StatusGroup;
  statusBadge: BadgeMeta;
  updatedLabel: string;
  // When the latest report reached its status (ISO); null without a report.
  statusAt: string | null;
  reviewUrl: string | null;
  hasReport: boolean;
  valuesPublished: number;
  valuesPending: number;
}

export interface OverviewView {
  rows: WorkRowView[];
}

export function presentOverview(
  rows: WorklistRow[],
  w: DashboardWording,
): OverviewView {
  return {
    rows: rows.map((r) => {
      const group = statusGroup(r.report_status);
      return {
        patientId: r.patient_id,
        name: r.display_name,
        initials: initials(r.display_name),
        ref: r.external_ref ?? "—",
        version: r.report_id ? (r.version_no ?? 1) : null,
        group,
        statusBadge: statusMeta(group, w),
        updatedLabel: relativeTime(r.status_at ?? r.updated_at, w.time),
        statusAt: r.status_at ?? null,
        reviewUrl: r.report_id
          ? `/patients/${r.patient_id}/assessments/${r.report_id}`
          : null,
        hasReport: r.report_id != null,
        valuesPublished: r.values_published ?? 0,
        valuesPending: r.values_pending ?? 0,
      };
    }),
  };
}

export interface DirectoryRowView {
  patientId: string;
  name: string;
  initials: string;
  ref: string;
  age: string;
  group: StatusGroup;
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
  w: DashboardWording,
): DirectoryView {
  const byPatient = new Map<string, WorklistRow>();
  for (const r of rows) byPatient.set(r.patient_id, r);
  const directory: DirectoryRowView[] = patients.map((p) => {
    const r = byPatient.get(p.id);
    const group = statusGroup(r?.report_status);
    const sm = statusMeta(group, w);
    return {
      patientId: p.id,
      name: p.display_name,
      initials: initials(p.display_name),
      ref: p.external_ref ?? "—",
      age: ageYears(p.date_of_birth),
      group,
      statusBadge: sm,
      lastAssessment: r ? relativeTime(r.updated_at, w.time) : "—",
    };
  });
  return {
    total: patients.length,
    withReport: rows.filter((r) => r.report_id != null).length,
    openAssessments: rows.filter((r) => DRAFT(r.report_status)).length,
    rows: directory,
  };
}
