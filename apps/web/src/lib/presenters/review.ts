// Review presenter: maps structured API data (Patient + ReportView + observation timeline)
// into render-ready view shapes. Raw observations, derived deltas, and the generated
// narrative stay SEPARATE here; per-observation provenance (code/status) is preserved.
// Domain rollup / data-quality coverage are intentionally absent (Gate G1, ADR-0002 §6).

import { comparabilityNote } from "@/lib/comparabilityCopy";
import {
  derivationOf,
  derivedInputsText,
  type Derivation,
} from "@/lib/derivation";
import { fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";
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

// The badge of a report status; its words are the page's (reportStatusLabel below).
const REPORT_STATUS_BADGE: Record<string, string> = {
  draft_generated: "badge-warning",
  draft_edited: "badge-warning",
  approved: "badge-info",
  released: "badge-success",
  rejected: "badge-danger",
};

export interface EvidenceChip {
  // What the source called the cited observation (null: not stated) and the value it wrote —
  // the page words the chip. Empty for evidence that cannot be resolved.
  name: string | null;
  value: string;
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
  id: string;
  name: string;
  // The value the platform holds: normalized where it could be, otherwise the source's own
  // number in the source's unit — or, for a result that is no number, the source's writing.
  current: string;
  change: string;
  reference: string;
  // Shown: the source code where one is stamped, else the catalog code.
  code: string;
  // What ties a value to the same analyte elsewhere (catalog code first, like the timeline).
  identity: string | null;
  // How `current` relates to what the source wrote — null when the value is normalized in
  // the unit the source itself used. Provenance, never a verdict. The page words it
  // (sourceNoteText below); for a conversion: what the source wrote, and the unit the value
  // was converted to (null: the metric's own, not named); for a value the platform computed
  // from other values: the formula and the inputs — no source reported it.
  sourceNote:
    | { kind: "text" | "source_unit" }
    | { kind: "converted"; source: string; unit: string | null }
    | { kind: "derived"; derivation: Derivation }
    | null;
  status: string;
  // Not published: still in the review queue, or rejected there. Such a value is shown as
  // what it is — with its status, and without a position against its reference interval.
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
  // Which step, and which of its lines applies — the page words them.
  key: "capture" | "draft" | "clinical" | "release" | "patient";
  subKey: "done" | "active" | "pending" | "rejected";
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
  // The age in full years, null without a date of birth — the page words it.
  ageYears: number | null;
  // The date of birth as the clinic reads it ("17.05.1980"); null without one.
  dateOfBirth: string | null;
  reportId: string;
  status: string;
  statusBadge: string;
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

// "1980-05-17" → "17.05.1980"; anything else → null.
function birthDay(dob: string | null | undefined): string | null {
  const m = dob ? /^(\d{4})-(\d{2})-(\d{2})/.exec(dob) : null;
  return m ? `${m[3]}.${m[2]}.${m[1]}` : null;
}

function ageYears(dob: string | null | undefined): number | null {
  if (!dob) return null;
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
  return age;
}

function unitJoin(
  value: string | null | undefined,
  unit: string | null | undefined,
): string {
  if (value == null) return "—";
  return unit ? `${value} ${unit}` : value;
}

// How the shown value relates to the source's writing. Four cases need saying: no source
// wrote it — the platform computed it from other values of the record; the platform converted
// the unit; the value is held as the source wrote it (not normalized, so no change over time
// is computed); no number is read from the source's writing at all — a text result, an
// addition ("<0,5", "12,4 H"), or a way of writing a number the platform does not read one
// way ("4.000", "1.234,5").
function sourceNote(
  p: TimelinePoint,
  byId: ReadonlyMap<string, TimelinePoint>,
): MarkerView["sourceNote"] {
  const derivation = derivationOf(p, byId);
  if (derivation) return { kind: "derived", derivation };
  if (p.value == null) return { kind: "text" };
  if (p.converted)
    return {
      kind: "converted",
      source: unitJoin(p.original_value, p.original_unit),
      unit: p.unit ?? null,
    };
  if (!p.normalized) return { kind: "source_unit" };
  return null;
}

function auditSteps(status: string): AuditStepView[] {
  const draft = status === "draft_generated" || status === "draft_edited";
  const released = status === "released";
  const approved = status === "approved";
  const rejected = status === "rejected";
  const step = (
    key: AuditStepView["key"],
    state: "done" | "active" | "",
    dot: string,
  ): AuditStepView => ({
    key,
    subKey:
      state === "done"
        ? "done"
        : state === "active"
          ? "active"
          : rejected
            ? "rejected"
            : "pending",
    state,
    dot: state === "done" ? "✓" : dot,
  });
  // Each step says only what the status proves. A draft exists only from published values,
  // so step 1 says that and no more ("complete" is not something the status knows). A
  // rejected version may have been rejected before or after the clinical approval — the
  // status does not say which — so it is never shown as signed.
  return [
    step("capture", "done", "1"),
    step("draft", "done", "2"),
    step(
      "clinical",
      draft ? "active" : approved || released ? "done" : "",
      "3",
    ),
    step("release", approved ? "active" : released ? "done" : "", "4"),
    step("patient", released ? "done" : "", "5"),
  ];
}

// Where this report version stands, said above its text. Only a version that still awaits a
// decision is called a draft; an approved or released version is never labelled "not
// released". An unknown status is treated as not released (fail-safe). The wording comes in
// the page's language (lib/i18n).
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
  t: Messages["reportPage"]["stage"],
): ReportStageView {
  // A cited value was replaced by a laboratory correction: the version can be neither
  // approved nor released as it stands, whatever its status says.
  if (status === "released")
    return {
      key: "released",
      attention: citesReplaced,
      title: t.title.report,
      badge: t.badge.released,
      headline: t.headline.released,
      detail: citesReplaced ? t.detail.citesReplaced : t.detail.released,
    };
  if (status === "approved")
    return {
      key: "approved",
      attention: citesReplaced,
      title: t.title.report,
      badge: t.badge.approved,
      headline: t.headline.approved,
      detail: citesReplaced ? t.detail.citesReplaced : t.detail.approved,
    };
  if (status === "rejected")
    return {
      key: "rejected",
      attention: false,
      title: t.title.rejected,
      badge: t.badge.rejected,
      headline: t.headline.rejected,
      detail: t.detail.rejected,
    };
  return {
    key: "draft",
    attention: false,
    title: t.title.draft,
    badge: t.badge.draft,
    headline:
      status === "draft_edited" || edited
        ? t.headline.draftEdited
        : t.headline.draftSystem,
    detail: citesReplaced ? t.detail.citesReplaced : t.detail.draft,
  };
}

// Honest, role-aware status line under the release action bar (the server enforces the
// actions — this only explains them). What a released status proves — and no more: whether
// the patient can open the report also depends on a valid access link and standing consent,
// which the status does not carry.
export function statusHint(
  status: string,
  role: string | null,
  citesReplaced: boolean,
  t: Messages["reportPage"]["bar"]["hint"],
): string {
  if (citesReplaced && status === "released") return t.releasedReplaced;
  if (citesReplaced && status !== "rejected") return t.replaced;
  if (status === "released") return t.released;
  if (status === "rejected")
    return role === "clinician" ? t.rejectedClinician : t.rejected;
  if (status === "approved")
    return role === "medical_director" ? t.approvedDirector : t.approved;
  if (role === "clinician") return t.draftClinician;
  if (role === "medical_director") return t.draftDirector;
  return t.readOnly;
}

// How a shown value relates to what the source wrote, in the page's language.
export function sourceNoteText(
  note: NonNullable<MarkerView["sourceNote"]>,
  t: Messages["patientPage"]["sourceNote"],
): { short: string; full: string } {
  if (note.kind === "derived") {
    const values = {
      inputs:
        derivedInputsText(note.derivation, t.derived.and) ??
        t.derived.otherValues,
      formula: note.derivation.formulaId ?? "—",
    };
    return {
      short: fill(t.derived.short, values),
      full: fill(t.derived.full, values),
    };
  }
  if (note.kind !== "converted") return t[note.kind];
  const values = {
    source: note.source ?? "",
    unit: note.unit ?? t.converted.unitOfMetric,
  };
  return {
    short: fill(t.converted.short, values),
    full: fill(t.converted.full, values),
  };
}

// The words for a report status (the badge in the header, the action bar).
export function reportStatusLabel(
  status: string,
  t: Messages["patientPage"]["reportStatus"],
): string {
  if (status === "draft_generated" || status === "draft_edited") return t.draft;
  if (status === "approved") return t.approved;
  if (status === "released") return t.released;
  if (status === "rejected") return t.rejected;
  return status;
}

export function presentReview(
  patient: Patient,
  report: ReportView,
  timeline: TimelinePoint[],
  matrix: DomainMatrixView | null,
): ReviewView {
  const age = ageYears(patient.date_of_birth);
  // A computed value names the values it was computed from (sourceNote).
  const byId = new Map(timeline.map((p) => [p.observation_id, p]));
  const domains: DomainView[] = (matrix?.domains ?? []).map((d) => {
    const markerCodes = Array.from(
      new Set(
        d.cells.flatMap((c) =>
          c.evidence
            .map((e) => e.kpi_code ?? e.metric_code)
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
    ageYears: age,
    dateOfBirth: birthDay(patient.date_of_birth),
    reportId: report.report_id,
    status: report.status,
    statusBadge: REPORT_STATUS_BADGE[report.status] ?? "badge-neutral",
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
          ? { name: null, value: "", missing: true }
          : {
              // The cited evidence as the source wrote it — what the reviewer has to judge,
              // including a result the statement does not quote. (An API answer without the
              // source fields falls back to the normalized value.)
              name: e.original_name ?? null,
              value:
                e.original_value != null
                  ? unitJoin(e.original_value, e.original_unit)
                  : unitJoin(e.value, e.unit),
              status: e.review_status,
              missing: false,
              superseded: e.superseded === true,
            },
      ),
    })),
    markers: timeline.map((p) => {
      // A position against the reference interval is stated for a published value only.
      const published = p.review_status === "published";
      return {
        id: p.observation_id,
        name: p.original_name,
        current:
          p.value != null
            ? unitJoin(p.value, p.unit)
            : unitJoin(p.original_value, p.original_unit),
        change: p.delta_vs_previous ?? "—",
        reference:
          p.reference_low != null || p.reference_high != null
            ? `${p.reference_low ?? "—"}–${p.reference_high ?? "—"} ${p.unit ?? ""}`.trim()
            : "—",
        code: p.metric_code ?? p.kpi_code ?? "—",
        identity: p.kpi_code ?? p.metric_code ?? null,
        sourceNote: sourceNote(p, byId),
        status: p.review_status,
        reviewRequired: !published,
        superseded: p.superseded_by_observation_id != null,
        inputReplaced: p.input_replaced === true,
        lagePosition: published
          ? referencePosition(p.value, p.reference_low, p.reference_high)
          : "not_evaluable",
        lageBar: published
          ? referenceBar(p.value, p.reference_low, p.reference_high)
          : referenceBar(null, null, null),
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
      };
    }),
    auditSteps: auditSteps(report.status),
  };
}
