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
  rejected: { badge: "badge-danger", label: "Zurückgewiesen" },
};

export interface EvidenceChip {
  label: string;
  status?: string;
  missing: boolean;
  // A published laboratory correction has replaced the cited value: the statement can no
  // longer be approved or released as it stands.
  superseded?: boolean;
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
  // A published laboratory correction has replaced this value; it stays as a preserved record.
  superseded: boolean;
  // A derived value computed from an input that a laboratory correction has replaced.
  inputReplaced: boolean;
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
  // The run cites a value a laboratory correction has since replaced. The run is a preserved
  // record; the note asks for a new look, it is not a verdict.
  citesReplaced: boolean;
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
  // A cited value no longer stands: not approvable or releasable; a new draft is the way on.
  citesReplaced: boolean;
  // Why this version was rejected / why the version this one reworks was rejected (closed
  // vocabulary codes; null when not applicable or not recorded).
  rejectionReason: string | null;
  reworksRejectionReason: string | null;
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
  // Each step says only what the status proves. A draft exists only from published values,
  // so step 1 says that and no more ("complete" is not something the status knows). A
  // rejected version may have been rejected before or after the clinical approval — the
  // status does not say which — so it is never shown as signed.
  return [
    step("Datenerfassung", "done", "1", "Werte veröffentlicht", "", ""),
    step("Entwurf erstellt", "done", "2", "Quellengebunden", "", ""),
    step(
      "Klinischer Review",
      draft ? "active" : approved || released ? "done" : "",
      "3",
      "Signiert",
      "In Bearbeitung",
      rejected ? "Version zurückgewiesen" : "Ausstehend",
    ),
    step(
      "Ärztliche Freigabe",
      approved ? "active" : released ? "done" : "",
      "4",
      "Abgeschlossen",
      "In Prüfung",
      rejected ? "Nicht erfolgt" : "Ausstehend",
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

// What a released status proves — and no more. Whether the patient can open the report also
// depends on a valid access link and standing consent, which the status does not carry (a
// withdrawn consent or an expired link leaves the status "released").
const RELEASED_ACCESS =
  "Für die Patientin ist nur diese Version einsehbar – solange ihr Zugriffslink gültig ist und die Einwilligung besteht.";

// A cited value was replaced by a laboratory correction: the version can be neither approved
// nor released as it stands, whatever its status says.
const CITES_REPLACED =
  "Ein zitierter Wert wurde vom Labor korrigiert – siehe Hinweis unten.";

// Where this report version stands, said above its text. Only a version that still awaits a
// decision is called a draft; an approved or released version is never labelled "nicht
// freigegeben". An unknown status is treated as not released (fail-safe).
export interface ReportStageView {
  key: "draft" | "approved" | "released" | "rejected";
  // Draws attention instead of confirming: the version rests on a replaced value.
  attention: boolean;
  title: string;
  badge: string;
  headline: string;
  detail: string;
}

export function reportStage(
  status: string,
  edited: boolean,
  citesReplaced: boolean,
): ReportStageView {
  if (status === "released")
    return {
      key: "released",
      attention: citesReplaced,
      title: "Quellengebundener Bericht",
      badge: "Freigegeben",
      headline: "Ärztlich freigegeben.",
      detail: citesReplaced ? CITES_REPLACED : RELEASED_ACCESS,
    };
  if (status === "approved")
    return {
      key: "approved",
      attention: citesReplaced,
      title: "Quellengebundener Bericht",
      badge: "Genehmigt",
      headline: "Klinisch genehmigt – noch nicht freigegeben.",
      detail: citesReplaced
        ? CITES_REPLACED
        : "Die Freigabe an die Patientin ist der ärztlichen Leitung vorbehalten.",
    };
  if (status === "rejected")
    return {
      key: "rejected",
      attention: false,
      title: "Zurückgewiesene Fassung",
      badge: "Zurückgewiesen",
      headline: "Zurückgewiesen – nicht freigegeben.",
      detail:
        "Eine Überarbeitung erstellt eine neue Version; diese Fassung bleibt erhalten.",
    };
  return {
    key: "draft",
    attention: false,
    title: "Quellengebundener Entwurf",
    badge: "Nicht freigegeben",
    headline:
      status === "draft_edited" || edited
        ? "Überarbeiteter Entwurf – nicht freigegeben."
        : "Systementwurf – nicht freigegeben.",
    detail: citesReplaced
      ? CITES_REPLACED
      : "Aussagen müssen anhand der Quellen geprüft und vom klinischen Team signiert werden.",
  };
}

// Honest, role-aware status line under the Freigabe action bar (shared by the review
// and detail surfaces; the server enforces the actions — this only explains them).
export function statusHint(
  status: string,
  role: string | null,
  citesReplaced = false,
): string {
  if (citesReplaced && status === "released")
    return "Freigegeben — ein zitierter Wert wurde vom Labor korrigiert; der Zugriff der Patientin wird erst mit einem neuen Entwurf zurückgezogen.";
  if (citesReplaced && status !== "rejected")
    return "Ein zitierter Wert wurde vom Labor korrigiert — diese Fassung kann nicht genehmigt oder freigegeben werden.";
  if (status === "released") return `Freigegeben — ${RELEASED_ACCESS}`;
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
      citesReplaced: d.cells.some((c) =>
        c.evidence.some((e) => e.superseded === true),
      ),
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
    citesReplaced: report.cites_replaced_evidence === true,
    rejectionReason: report.rejection_reason ?? null,
    reworksRejectionReason: report.reworks_rejection_reason ?? null,
    statements: report.statements.map((s) => ({
      id: s.id,
      text: s.text,
      evidenceIds: s.evidence.map((e) => e.observation_id),
      evidence: s.evidence.map((e) =>
        e.missing
          ? { label: "Beleg nicht auflösbar", missing: true }
          : {
              // The cited evidence as the source wrote it — what the reviewer has to judge,
              // including a result the statement does not quote. (An API answer without the
              // source fields falls back to the normalized value.)
              label: `${e.original_name ?? "Beobachtung"}: ${
                e.original_value != null
                  ? unitJoin(e.original_value, e.original_unit)
                  : unitJoin(e.value, e.unit)
              }`,
              status: e.review_status,
              missing: false,
              superseded: e.superseded === true,
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
      superseded: p.superseded_by_observation_id != null,
      inputReplaced: p.input_replaced === true,
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
