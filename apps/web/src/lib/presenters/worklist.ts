// Worklist presenter: maps the structured API rows (WorklistRow) into render-ready view
// rows. ALL display formatting (initials, age, relative time, status badge/label) lives
// here in the frontend — the API returns codes/raw fields/timestamps, not display strings.

import type { WorklistRow } from "@/lib/api";

const REPORT_STATUS: Record<
  string,
  { badge: string; label: string; group: string }
> = {
  draft_generated: {
    badge: "badge-brand",
    label: "Klinischer Review",
    group: "open",
  },
  draft_edited: {
    badge: "badge-brand",
    label: "Klinischer Review",
    group: "open",
  },
  approved: { badge: "badge-info", label: "Genehmigt", group: "approved" },
  released: { badge: "badge-success", label: "Freigegeben", group: "released" },
  rejected: { badge: "badge-danger", label: "Abgelehnt", group: "other" },
};
const NO_REPORT = {
  badge: "badge-neutral",
  label: "Kein Entwurf",
  group: "none",
};

export interface WorklistView {
  patientId: string;
  reportId: string | null;
  name: string;
  initials: string;
  ref: string;
  profile: string;
  assessment: string;
  statusBadge: string;
  statusLabel: string;
  statusGroup: string;
  updatedLabel: string;
  open: boolean;
  reviewUrl: string | null;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0] ?? "");
  return letters.join("").toUpperCase() || "–";
}

function ageProfile(dob: string | null): string {
  if (!dob) return "Alter unbekannt";
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
  return `${age} J.`;
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "gerade eben";
  if (mins < 60) return `vor ${mins} Min.`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `vor ${hours} h`;
  const days = Math.round(hours / 24);
  if (days === 1) return "gestern";
  return `vor ${days} T`;
}

export function presentWorklist(rows: WorklistRow[]): WorklistView[] {
  return rows.map((r) => {
    const status = r.report_status
      ? (REPORT_STATUS[r.report_status] ?? NO_REPORT)
      : NO_REPORT;
    return {
      patientId: r.patient_id,
      reportId: r.report_id ?? null,
      name: r.display_name,
      initials: initials(r.display_name),
      ref: r.external_ref ?? "—",
      profile: ageProfile(r.date_of_birth ?? null),
      assessment: r.report_id
        ? `Bericht · v${r.version_no ?? 1}`
        : "Kein Entwurf",
      statusBadge: status.badge,
      statusLabel: status.label,
      statusGroup: status.group,
      updatedLabel: relativeTime(r.updated_at),
      open: r.report_id != null,
      reviewUrl: r.report_id
        ? `/patients/${r.patient_id}/assessments/${r.report_id}`
        : null,
    };
  });
}
