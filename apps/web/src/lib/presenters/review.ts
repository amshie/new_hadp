// Review presenter: maps structured API data (Patient + ReportView + observation timeline)
// into render-ready view shapes. Raw observations, derived deltas, and the generated
// narrative stay SEPARATE here; per-observation provenance (code/status) is preserved.
// Domain rollup / data-quality coverage are intentionally absent (Gate G1, ADR-0002 §6).

import { comparabilityNote } from "@/lib/comparabilityCopy";
import {
  referenceBar,
  referencePosition,
  type PositionBar,
  type ReferencePosition,
} from "@/lib/referencePosition";
import type {
  DomainMatrixView,
  EvidenceObs,
  Patient,
  ReportView,
  TimelinePoint,
} from "@/lib/api";

export const DOMAIN_AXIS_LABELS: Record<string, string> = {
  metabolic: "Metabolisch",
  immune_inflammation: "Immun / Entzündung",
  cardiovascular: "Kardiovaskulär",
  neurocognitive: "Neurokognitiv",
  musculoskeletal: "Muskuloskelettal",
  regenerative_capacity: "Regenerationskapazität",
};
export const CIS_LABELS: Record<string, string> = {
  CIS_0_INSUFFICIENT_EVIDENCE: "CIS-0 · Unzureichende Evidenz",
  CIS_1_APPARENT_BIOLOGICAL_IMPROVEMENT_ONLY:
    "CIS-1 · Nur scheinbare Verbesserung",
  CIS_2_NOT_YET_CREDIBLE: "CIS-2 · Noch nicht glaubwürdig",
  CIS_3_RISK_DOMINANT_OR_CONFLICTING: "CIS-3 · Risiko-dominant",
  CIS_4_CREDIBLE_IMPROVEMENT: "CIS-4 · Glaubwürdige Verbesserung",
  CIS_5_STABLE_NO_MATERIAL_CHANGE: "CIS-5 · Stabil",
};
export const ACTIONABILITY_LABELS: Record<string, string> = {
  A_DISCOVERY: "A · Erkundung",
  B_SUPPORTIVE: "B · Unterstützend",
  C_CLINICALLY_INTERPRETABLE: "C · Klinisch interpretierbar",
  D_ACTIONABLE_UNDER_GOVERNANCE: "D · Unter Governance handelbar",
  E_DO_NOT_ACT: "E · Nicht handeln",
};
const TRI_AXIS_LABELS: Record<string, string> = {
  biological: "Biologisch",
  risk: "Risiko",
  functional: "Funktionell",
};
export const ADEQUACY_LABELS: Record<string, string> = {
  adequate: "adäquat",
  inadequate: "inadäquat",
  not_assessed: "nicht bewertet",
};

const REPORT_STATUS: Record<string, { badge: string; label: string }> = {
  draft_generated: { badge: "badge-warning", label: "Klinische Prüfung offen" },
  draft_edited: { badge: "badge-warning", label: "Klinische Prüfung offen" },
  approved: {
    badge: "badge-info",
    label: "An ärztliche Freigabe weitergeleitet",
  },
  released: { badge: "badge-success", label: "Freigegeben" },
  rejected: { badge: "badge-danger", label: "Abgelehnt" },
};

export interface EvidenceChip {
  label: string;
  status?: string;
  missing: boolean;
}
export interface StatementView {
  id: string;
  text: string;
  evidence: EvidenceChip[];
  // The observations the statement is bound to — a rework keeps this binding unchanged.
  evidenceIds: string[];
}
export interface MarkerView {
  name: string;
  current: string;
  change: string;
  reference: string;
  code: string;
  status: string;
  reviewRequired: boolean;
  // Lage zum Referenzintervall (docs/notes/0009 out_of_source_interval): the value's deterministic
  // position relative to the lab interval + a cosmetic position bar. Provenance, never a verdict.
  lagePosition: ReferencePosition;
  lageBar: PositionBar;
  referenceRange: string | null; // lab interval low–high (no unit) for the bar's "Referenz x–y" label
  // Catalog linkage (ADR-0004 Slice 2b): the canonical KPI + its navigational domains.
  kpiCode: string | null;
  primaryDomainLabel: string | null;
  secondaryDomains: string[];
  // Comparability note (ADR-0004 Slice 3, §9): set only when the delta was withheld because the
  // measurement context differs/is missing. Provenance about the comparison, never a verdict.
  comparabilityShort: string | null;
  comparabilityFull: string | null;
}
export interface AuditStepView {
  label: string;
  sub: string;
  state: "done" | "active" | "";
  dot: string;
}
export interface DomainCellView {
  axisLabel: string;
  state: string;
  endpointAdequacy: string;
  evidence: EvidenceObs[];
}
export interface DomainView {
  axisLabel: string;
  domainAxis: string; // raw closed-vocabulary value, used to match secondary-domain markers
  cisLabel: string;
  actionabilityLabel: string;
  adequacyLabel: string;
  reviewed: boolean;
  markerCodes: string[];
  cells: DomainCellView[];
}
export interface ReviewView {
  patientName: string;
  ref: string;
  ageProfile: string;
  reportId: string;
  status: string;
  statusBadge: string;
  statusLabel: string;
  versionNo: number;
  // True once the current version carries a human edit (no longer the provider's output).
  edited: boolean;
  statements: StatementView[];
  markers: MarkerView[];
  auditSteps: AuditStepView[];
  runNumber: number | null;
  domains: DomainView[];
}

function ageProfile(dob: string | null | undefined): string {
  if (!dob) return "Alter unbekannt";
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
  return `${age} Jahre`;
}

function unitJoin(
  value: string | null | undefined,
  unit: string | null | undefined,
): string {
  if (value == null) return "—";
  return unit ? `${value} ${unit}` : value;
}

function auditSteps(status: string): AuditStepView[] {
  const draft = status === "draft_generated" || status === "draft_edited";
  const released = status === "released";
  const approved = status === "approved";
  const rejected = status === "rejected";
  const step = (
    label: string,
    state: "done" | "active" | "",
    dot: string,
    subDone: string,
    subActive: string,
    subPending: string,
  ): AuditStepView => ({
    label,
    state,
    dot: state === "done" ? "✓" : dot,
    sub:
      state === "done" ? subDone : state === "active" ? subActive : subPending,
  });
  return [
    step("Datenerfassung", "done", "1", "Vollständig", "", ""),
    step("Entwurf erstellt", "done", "2", "Quellengebunden", "", ""),
    step(
      "Klinischer Review",
      draft ? "active" : "done",
      "3",
      "Signiert",
      "In Bearbeitung",
      "Ausstehend",
    ),
    step(
      "Ärztliche Freigabe",
      approved ? "active" : released ? "done" : "",
      "4",
      "Abgeschlossen",
      "In Prüfung",
      rejected ? "Zurückgewiesen" : "Ausstehend",
    ),
    step(
      "Patientenfreigabe",
      released ? "done" : "",
      "5",
      "Freigegeben",
      "",
      rejected ? "Zurückgewiesen — Überarbeitung nötig" : "Nicht möglich",
    ),
  ];
}

// Honest, role-aware status line under the Freigabe action bar (shared by the review
// and detail surfaces; the server enforces the actions — this only explains them).
export function statusHint(status: string, role: string | null): string {
  if (status === "released")
    return "Freigegeben — die Patientin sieht ausschließlich diese Version.";
  if (status === "rejected")
    return role === "clinician"
      ? "Zurückgewiesen — „Überarbeiten“ erstellt eine neue Version; die zurückgewiesene bleibt erhalten."
      : "Zurückgewiesen — eine Überarbeitung erstellt eine neue Version.";
  if (status === "approved") {
    return role === "medical_director"
      ? "Bereit zur Freigabe an die Patientin — einwilligungsgebunden, zugeordnet und auditiert."
      : "Genehmigt — wartet auf die ärztliche Freigabe.";
  }
  if (role === "clinician")
    return "Genehmigung wird serverseitig geschrieben, ist Ihnen zugeordnet und wird auditiert.";
  if (role === "medical_director")
    return "Wartet auf die klinische Genehmigung.";
  return "Nur-Lese-Ansicht für Ihre Rolle.";
}

export function presentReview(
  patient: Patient,
  report: ReportView,
  timeline: TimelinePoint[],
  matrix: DomainMatrixView | null,
): ReviewView {
  const statusInfo = REPORT_STATUS[report.status] ?? {
    badge: "badge-neutral",
    label: report.status,
  };
  const domains: DomainView[] = (matrix?.domains ?? []).map((d) => {
    const markerCodes = Array.from(
      new Set(
        d.cells.flatMap((c) =>
          c.evidence
            .map((e) => e.metric_code)
            .filter((code): code is string => code != null),
        ),
      ),
    );
    return {
      axisLabel: DOMAIN_AXIS_LABELS[d.domain_axis] ?? d.domain_axis,
      domainAxis: d.domain_axis,
      cisLabel: CIS_LABELS[d.cis_status] ?? d.cis_status,
      actionabilityLabel:
        ACTIONABILITY_LABELS[d.actionability_class] ?? d.actionability_class,
      adequacyLabel:
        ADEQUACY_LABELS[d.followup_adequacy] ?? d.followup_adequacy,
      reviewed: d.review_status === "clinician_reviewed",
      markerCodes,
      cells: d.cells.map((c) => ({
        axisLabel: TRI_AXIS_LABELS[c.tri_state_axis] ?? c.tri_state_axis,
        state: c.state,
        endpointAdequacy:
          ADEQUACY_LABELS[c.endpoint_adequacy] ?? c.endpoint_adequacy,
        evidence: c.evidence,
      })),
    };
  });
  return {
    runNumber: matrix?.run_number ?? null,
    domains,
    patientName: patient.display_name,
    ref: patient.external_ref ?? "—",
    ageProfile: ageProfile(patient.date_of_birth),
    reportId: report.report_id,
    status: report.status,
    statusBadge: statusInfo.badge,
    statusLabel: statusInfo.label,
    versionNo: report.version_no,
    edited: report.edited === true,
    statements: report.statements.map((s) => ({
      id: s.id,
      text: s.text,
      evidenceIds: s.evidence.map((e) => e.observation_id),
      evidence: s.evidence.map((e) =>
        e.missing
          ? { label: "Beleg nicht auflösbar", missing: true }
          : {
              label: `${e.original_name ?? "Beobachtung"}: ${unitJoin(e.value, e.unit)}`,
              status: e.review_status,
              missing: false,
            },
      ),
    })),
    markers: timeline.map((p) => ({
      name: p.original_name,
      current: unitJoin(p.value, p.unit),
      change: p.delta_vs_previous ?? "—",
      reference:
        p.reference_low != null || p.reference_high != null
          ? `${p.reference_low ?? "—"}–${p.reference_high ?? "—"} ${p.unit ?? ""}`.trim()
          : "—",
      code: p.metric_code ?? "—",
      status: p.review_status,
      reviewRequired: p.review_status !== "published",
      lagePosition: referencePosition(
        p.value,
        p.reference_low,
        p.reference_high,
      ),
      lageBar: referenceBar(p.value, p.reference_low, p.reference_high),
      referenceRange:
        p.reference_low != null && p.reference_high != null
          ? `${p.reference_low}–${p.reference_high}`
          : null,
      kpiCode: p.kpi_code ?? null,
      primaryDomainLabel: p.kpi_primary_domain
        ? (DOMAIN_AXIS_LABELS[p.kpi_primary_domain] ?? p.kpi_primary_domain)
        : null,
      secondaryDomains: p.kpi_secondary_domains ?? [],
      comparabilityShort:
        comparabilityNote(p.comparability, p.comparability_reason)?.short ??
        null,
      comparabilityFull:
        comparabilityNote(p.comparability, p.comparability_reason)?.full ??
        null,
    })),
    auditSteps: auditSteps(report.status),
  };
}
