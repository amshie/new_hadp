"use client";

import { useEffect, useRef, useState, useTransition } from "react";

import { AuditSteps } from "@/components/vitabahn/AuditSteps";
import { Dialog } from "@/components/vitabahn/Dialog";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toaster";
import {
  approveReportAction,
  editReportAction,
  redraftReportAction,
  rejectReportAction,
  releaseReportAction,
} from "@/app/reports/actions";
import {
  REJECTION_REASONS,
  rejectionCopy,
  type RejectionReason,
} from "@/lib/rejectionCopy";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import { lageLabel } from "@/lib/lageCopy";
import {
  reportStage,
  reportStatusLabel,
  sourceNoteText,
  statusHint,
  type MarkerView,
  type ReviewView,
} from "@/lib/presenters/review";

// The page follows the interface language (lib/i18n). The VALUES of closed vocabularies on it
// do not, and are marked lang="de" wherever they show: the names of the domain axes, the
// Actionability class, the value of follow-up adequacy, the position against the reference
// interval, the comparability notes and the reasons for a rejection (ADR-0007: their English
// needs the medical director). What NAMES a kind of fact (a column heading, "Follow-up
// adequacy:") is interface. The statements of a report stay as they were written, and so do
// the names and values the source wrote. Numbers and dates keep their form.
const GERMAN = "de";
type T = Messages["reportPage"];

// "Veränderung" cell: the withheld-delta comparability note (text-carried, no color-alone) when the
// comparison was suppressed (§9), else the normal delta. Shared by both observation tables.
function ChangeCell({ marker }: { marker: MarkerView }) {
  if (!marker.comparabilityShort)
    return <span className="num">{marker.change}</span>;
  return (
    <span
      className="comparability-note"
      lang={GERMAN}
      title={marker.comparabilityFull ?? undefined}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        color: "var(--muted)",
        fontSize: "12px",
      }}
    >
      <span aria-hidden="true" style={{ display: "inline-flex" }}>
        <Icon name="shieldInfo" />
      </span>
      <span>{marker.comparabilityShort}</span>
      <span className="sr-only">{marker.comparabilityFull}</span>
    </span>
  );
}

function fmtNum(n: number): string {
  const r = Math.round(n * 10) / 10;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

// "Lage zum Referenzintervall" cell: a direction pill (glyph + word + full screen-reader sentence)
// above a position bar styled after the Claude Design comp (founder direction 2026-06-25): a cream
// track, a teal reference band, a midpoint tick, the "Referenz x–y" label, 0…scale-end labels, and
// an amber value dot (no pulse). The reference band reflects only the lab-provided interval; the
// amber dot is a palette choice, never a verdict — meaning is still carried by the pill + the
// sr-only sentence (never colour alone). A marker with no lab interval renders "keine Skala" — no
// dot, never a guessed position (doctrine: never read as normal/stable).
function LageCell({ marker, t }: { marker: MarkerView; t: T["evidence"] }) {
  // No position is stated for a value nobody has reviewed.
  if (marker.reviewRequired)
    return (
      <span className="pos-bar-noscale">
        <span aria-hidden="true">—</span>
        <span className="sr-only">{t.notPublished}</span>
      </span>
    );
  const l = lageLabel(marker.lagePosition);
  const bar = marker.lageBar;
  // "Reference interval 3.9–5.6 mmol/L", or that there is none.
  const intervalText =
    marker.reference === "—"
      ? t.noInterval
      : `${t.referenceInterval} ${marker.reference}`;
  return (
    <div className="lage-cell">
      <span className={`badge ${l.badge} no-dot lage-pill`} lang={GERMAN}>
        <span aria-hidden="true">{l.glyph}</span>
        <span>{l.label}</span>
      </span>
      {bar.hasScale ? (
        <div className="pos-bar" aria-hidden="true">
          <div className="pos-bar-track">
            <div
              className="pos-bar-band"
              style={{
                left: `${bar.bandStartPct}%`,
                right: `${100 - bar.bandEndPct}%`,
              }}
            />
          </div>
          <div className="pos-bar-tick" style={{ left: `${bar.midPct}%` }} />
          {marker.referenceRange && (
            <div
              className="pos-bar-refrange"
              style={{ left: `${bar.midPct}%` }}
            >
              {fill(t.reference, { range: marker.referenceRange })}
            </div>
          )}
          {bar.dotPct != null && (
            <div className="pos-bar-dot" style={{ left: `${bar.dotPct}%` }} />
          )}
          <div className="pos-bar-scalemin">0</div>
          <div className="pos-bar-scalemax">{fmtNum(bar.scaleMax)}</div>
        </div>
      ) : (
        <span className="pos-bar-noscale" aria-hidden="true">
          {t.noScale}
        </span>
      )}
      <span className="sr-only">
        {`${marker.name} ${marker.current}; ${intervalText}; `}
        <span lang={GERMAN}>{l.sentence}</span>.
      </span>
    </div>
  );
}

// "Code / Status" cell: the code, where a value stands in the review of imported values when
// it is not published, a laboratory correction, and how the value relates to what the source
// wrote. Shared by both observation tables; worded as on the patient page.
function CodeStatusCell({
  marker,
  t,
}: {
  marker: MarkerView;
  t: Messages["patientPage"];
}) {
  const valueStatus: Record<string, string> = t.valueStatus;
  const note = marker.sourceNote
    ? sourceNoteText(marker.sourceNote, t.sourceNote)
    : null;
  return (
    <td className="source">
      {marker.code}
      {marker.reviewRequired && (
        <span className="marker-status">
          {valueStatus[marker.status] ?? marker.status}
        </span>
      )}
      {marker.superseded ? ` · ${t.evidence.superseded}` : ""}
      {marker.inputReplaced ? ` · ${t.evidence.inputReplaced}` : ""}
      {note && (
        <span className="marker-meta" title={note.full}>
          {note.short}
          <span className="sr-only"> — {note.full}</span>
        </span>
      )}
    </td>
  );
}

type RefFilter = "all" | "outside" | "no_ref";

const REF_FILTERS: RefFilter[] = ["all", "outside", "no_ref"];

function matchesRefFilter(marker: MarkerView, filter: RefFilter): boolean {
  // A value that is not published has no position: it is listed under "Alle" only — not
  // under "Ohne Referenz", which it may well have.
  if (marker.reviewRequired) return filter === "all";
  if (filter === "outside")
    return marker.lagePosition === "above" || marker.lagePosition === "below";
  if (filter === "no_ref")
    return (
      marker.lagePosition === "no_reference" ||
      marker.lagePosition === "not_evaluable"
    );
  return true;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((p) => p[0] ?? "")
      .join("") || "–"
  ).toUpperCase();
}

export function ReviewContent({
  view,
  sessionRole,
  path,
}: {
  view: ReviewView;
  sessionRole: string | null;
  path: string;
}) {
  const toast = useToast();
  const messages = useI18n().t;
  const t = messages.reportPage;
  const p = messages.patientPage;
  const statusLabel = reportStatusLabel(view.status, p.reportStatus);
  const [dialog, setDialog] = useState<
    "approve" | "reject" | "release" | "redraft" | null
  >(null);
  const [confirmChecked, setConfirmChecked] = useState(false);
  // A rejection names its reason (closed vocabulary); nothing is preselected.
  const [rejectReason, setRejectReason] = useState<RejectionReason | null>(
    null,
  );
  const [releasedUrl, setReleasedUrl] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const confirmRef = useRef<HTMLInputElement>(null);

  // Real Freigabe lifecycle (Gate G2 closed): role-appropriate actions only. The API
  // enforces role + lifecycle + consent server-side; hiding here is UX, never a control.
  const isDraft =
    view.status === "draft_generated" || view.status === "draft_edited";
  const isApproved = view.status === "approved";
  // A version that cites a replaced value is refused by the API for both steps.
  const canApprove =
    sessionRole === "clinician" && isDraft && !view.citesReplaced;
  const canRelease =
    sessionRole === "medical_director" && isApproved && !view.citesReplaced;
  const canReject =
    (sessionRole === "clinician" || sessionRole === "medical_director") &&
    (isDraft || isApproved);

  // Rework after rejection: the clinician revises the wording (or drops a statement) and saves
  // it as a NEW version — the rejected version stays a preserved record. Each statement keeps
  // its evidence binding; the API re-validates it and refuses restricted language.
  const canRework = sessionRole === "clinician" && view.status === "rejected";
  // A cited value was corrected by the laboratory: this version can be neither approved nor
  // released. The clinician opens a new draft from the values that stand.
  const canRedraft = sessionRole === "clinician" && view.citesReplaced;
  const stage = reportStage(
    view.status,
    view.edited,
    view.citesReplaced,
    t.stage,
  );
  const rejection = rejectionCopy(view.rejectionReason);
  const reworked = rejectionCopy(view.reworksRejectionReason);
  const [editRows, setEditRows] = useState<
    | { id: string; text: string; evidenceIds: string[]; removed: boolean }[]
    | null
  >(null);
  const [editError, setEditError] = useState<string | null>(null);
  const firstEditRef = useRef<HTMLTextAreaElement>(null);
  const editing = editRows !== null;
  useEffect(() => {
    if (editing) firstEditRef.current?.focus();
  }, [editing]);
  const keptRows = editRows?.filter((r) => !r.removed) ?? [];
  const reworkDirty =
    editRows?.some(
      (r, i) => r.removed || r.text.trim() !== view.statements[i]?.text,
    ) ?? false;
  const reworkValid =
    keptRows.length > 0 && keptRows.every((r) => r.text.trim().length > 0);

  const startRework = () => {
    setEditError(null);
    setEditRows(
      view.statements.map((s) => ({
        id: s.id,
        text: s.text,
        evidenceIds: s.evidenceIds,
        removed: false,
      })),
    );
  };
  const cancelRework = () => {
    setEditRows(null);
    setEditError(null);
  };
  const updateRow = (
    index: number,
    patch: { text?: string; removed?: boolean },
  ) =>
    setEditRows(
      (rows) =>
        rows?.map((r, i) => (i === index ? { ...r, ...patch } : r)) ?? null,
    );
  const saveRework = () => {
    startTransition(async () => {
      const res = await editReportAction(
        view.reportId,
        path,
        keptRows.map((r) => ({
          id: r.id,
          text: r.text.trim(),
          evidence_observation_ids: r.evidenceIds,
        })),
      );
      if (!res.ok) {
        setEditError(res.error);
        return;
      }
      cancelRework();
      toast(t.toast.saved);
    });
  };

  const closeDialog = () => {
    setDialog(null);
    setConfirmChecked(false);
    setRejectReason(null);
    setReleasedUrl(null);
  };

  const runAction = (kind: "approve" | "reject" | "release" | "redraft") => {
    startTransition(async () => {
      const res =
        kind === "approve"
          ? await approveReportAction(view.reportId, path)
          : kind === "reject"
            ? rejectReason
              ? await rejectReportAction(view.reportId, path, rejectReason)
              : { ok: false as const, error: t.errors.chooseReason }
            : kind === "redraft"
              ? await redraftReportAction(view.reportId, path)
              : await releaseReportAction(view.reportId, path);
      if (!res.ok) {
        closeDialog();
        toast(res.error);
        return;
      }
      if (kind === "release" && res.patientViewUrl) {
        // Keep the dialog open: the link is shown exactly once (token is not re-readable).
        setReleasedUrl(res.patientViewUrl);
        return;
      }
      closeDialog();
      toast(
        kind === "approve"
          ? t.toast.approved
          : kind === "redraft"
            ? t.toast.redrafted
            : t.toast.rejected,
      );
    });
  };
  const [selectedDomain, setSelectedDomain] = useState<number | null>(null);
  // Transient view filter on the value's position vs. its reference interval. No counts (a count
  // across markers would read as a severity tally — out of bounds, founder decision 2026-06-24);
  // default "all" never hides values; composes (AND) with the domain selection below.
  const [refFilter, setRefFilter] = useState<RefFilter>("all");
  const selected =
    selectedDomain != null ? (view.domains[selectedDomain] ?? null) : null;
  // Beobachtungsnachweis shows the selected domain's own biomarkers, or all when none is selected.
  const primaryMarkers = selected
    ? view.markers.filter(
        (m) => m.identity != null && selected.markerCodes.includes(m.identity),
      )
    : view.markers;
  const visiblePrimary = primaryMarkers.filter((m) =>
    matchesRefFilter(m, refFilter),
  );
  // Secondary-linked biomarkers (ADR-0004 Slice 2b): the SAME single observation surfaced where it
  // is also relevant — navigational visibility only, never a second verdict. Excludes any already
  // in the domain's own evidence (no duplication across domains).
  const secondaryMarkers = selected
    ? view.markers.filter(
        (m) =>
          m.secondaryDomains.includes(selected.domainAxis) &&
          !(m.identity != null && selected.markerCodes.includes(m.identity)),
      )
    : [];

  return (
    <>
      <header className="page-header">
        <div className="patient-heading">
          <div className="patient-avatar" aria-hidden="true">
            {initials(view.patientName)}
          </div>
          <div className="patient-heading-copy">
            <h1>{view.patientName}</h1>
            <div className="patient-details">
              <span className="num">{view.ref}</span>
              <span>
                {view.ageYears === null
                  ? p.ageUnknown
                  : byCount(p.age, view.ageYears)}
              </span>
              <span>{fill(p.reportVersion, { version: view.versionNo })}</span>
            </div>
          </div>
          <span className={`badge ${view.statusBadge}`}>{statusLabel}</span>
        </div>
      </header>

      <div
        className={`stage-banner is-${stage.attention ? "draft" : stage.key}`}
        role="status"
      >
        <Icon
          name={
            !stage.attention &&
            (stage.key === "approved" || stage.key === "released")
              ? "check"
              : "alert"
          }
        />
        <span>
          <strong>{stage.headline}</strong> {stage.detail}
        </span>
      </div>

      <div className="section-header">
        <div>
          <h2>{stage.title}</h2>
          <p>{t.lead}</p>
        </div>
        <span className="badge badge-brand no-dot">{stage.badge}</span>
      </div>

      <section className="card summary-card" aria-label={stage.title}>
        <span className="kicker">
          {view.edited ? t.kicker.edited : t.kicker.deterministic}
        </span>
        {view.statements.length === 0 && (
          <p style={{ marginTop: "12px" }}>{t.noStatements}</p>
        )}
        {view.status === "rejected" && (
          <p
            role="status"
            style={{
              marginTop: "12px",
              padding: "10px 12px",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12.5px",
              lineHeight: 1.5,
            }}
          >
            <strong>{t.rejected.title}</strong>{" "}
            {rejection ? (
              <>
                {t.rejected.reason}{" "}
                <span lang={GERMAN}>
                  {rejection.label}. {rejection.desc}
                </span>
              </>
            ) : (
              t.rejected.noReason
            )}
          </p>
        )}
        {reworked && (
          <p
            role="status"
            style={{
              marginTop: "12px",
              padding: "10px 12px",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12.5px",
              lineHeight: 1.5,
            }}
          >
            {t.rejected.reworked}{" "}
            <span lang={GERMAN}>
              <strong>{reworked.label}</strong>. {reworked.desc}
            </span>
          </p>
        )}
        {view.citesReplaced && (
          <p
            role="status"
            style={{
              marginTop: "12px",
              padding: "10px 12px",
              border: "1px solid var(--btn-danger-border)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12.5px",
              lineHeight: 1.5,
            }}
          >
            {t.citesReplaced.note}
            {view.status === "released" && t.citesReplaced.released}
            {sessionRole === "clinician"
              ? t.citesReplaced.clinician
              : t.citesReplaced.otherRole}
          </p>
        )}
        {view.statements.map((s, index) => {
          const row = editRows?.[index];
          return (
            <div
              className="system-draft"
              key={s.id}
              style={{ marginTop: "14px", opacity: row?.removed ? 0.6 : 1 }}
            >
              {row ? (
                <label className="field">
                  <span className="field-label">
                    {fill(t.statement.label, { n: index + 1 })}
                    {row.removed ? t.statement.removing : ""}
                  </span>
                  <textarea
                    ref={index === 0 ? firstEditRef : undefined}
                    className="textarea"
                    rows={3}
                    value={row.text}
                    disabled={row.removed || pending}
                    onChange={(e) => updateRow(index, { text: e.target.value })}
                    style={{
                      padding: "10px 12px",
                      fontSize: "12.5px",
                      lineHeight: 1.55,
                      resize: "vertical",
                    }}
                  />
                </label>
              ) : (
                <p style={{ marginTop: 0 }}>{s.text}</p>
              )}
              <div className="source-links">
                {s.evidence.map((e, i) => (
                  <span
                    key={i}
                    className={`source-link${e.missing ? " " : ""}`}
                    style={
                      e.missing || e.superseded
                        ? {
                            color: "var(--danger)",
                            borderColor: "var(--btn-danger-border)",
                          }
                        : undefined
                    }
                  >
                    {e.missing
                      ? t.chip.unresolved
                      : `${e.name ?? t.chip.observation}: ${e.value}`}
                    {e.status && e.status !== "published"
                      ? ` · ${e.status}`
                      : ""}
                    {e.superseded ? t.chip.corrected : ""}
                  </span>
                ))}
              </div>
              {row && (
                <button
                  className="btn btn-ghost btn-sm"
                  type="button"
                  disabled={pending}
                  onClick={() => updateRow(index, { removed: !row.removed })}
                  style={{ marginTop: "8px" }}
                >
                  {row.removed ? t.statement.restore : t.statement.remove}
                </button>
              )}
            </div>
          );
        })}
        {editing && (
          <div style={{ marginTop: "16px" }}>
            <p>
              {fill(t.rework.note, {
                next: view.versionNo + 1,
                version: view.versionNo,
              })}
            </p>
            {editError && (
              <p role="alert" style={{ color: "var(--danger)" }}>
                {editError}
              </p>
            )}
            <div
              className="dialog-actions"
              style={{ justifyContent: "flex-start", marginTop: "12px" }}
            >
              <button
                className="btn btn-primary"
                type="button"
                disabled={pending || !reworkDirty || !reworkValid}
                onClick={saveRework}
              >
                {t.rework.save}
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                disabled={pending}
                onClick={cancelRework}
              >
                {t.dialog.cancel}
              </button>
            </div>
          </div>
        )}
      </section>

      <div className="section-header">
        <div>
          <h2>{t.domains.title}</h2>
          <p>{t.domains.note}</p>
        </div>
        {view.runNumber != null && (
          <span className="badge badge-brand no-dot">
            {fill(t.domains.run, { n: view.runNumber })}
          </span>
        )}
      </div>
      {view.domains.length === 0 ? (
        <section
          className="card"
          style={{ padding: "20px" }}
          aria-label={t.domains.title}
        >
          <div className="notice notice-brand">
            <Icon name="shieldInfo" />
            <span>{t.domains.noRun}</span>
          </div>
        </section>
      ) : (
        <section
          aria-label={t.domains.title}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "14px",
          }}
        >
          {view.domains.map((d, i) => {
            const isSelected = selectedDomain === i;
            return (
              <article
                className="card"
                key={d.axisLabel}
                style={{
                  padding: "16px",
                  boxShadow: isSelected
                    ? "0 0 0 2px var(--brand, #2f6f4e)"
                    : undefined,
                }}
              >
                <button
                  type="button"
                  onClick={() => setSelectedDomain(isSelected ? null : i)}
                  aria-pressed={isSelected}
                  style={{
                    all: "unset",
                    cursor: "pointer",
                    display: "block",
                    width: "100%",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                      gap: "8px",
                      marginBottom: "10px",
                    }}
                  >
                    <strong lang={GERMAN}>{d.axisLabel}</strong>
                    <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                      {d.reviewed ? t.domains.reviewed : t.domains.draft}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "8px",
                      marginBottom: "10px",
                    }}
                  >
                    <span className="source-link" lang={GERMAN}>
                      {d.actionabilityLabel}
                    </span>
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "12px",
                      color: "var(--muted)",
                    }}
                  >
                    {t.domains.adequacy}{" "}
                    <span lang={GERMAN}>{d.adequacyLabel}</span>
                  </p>
                  {d.citesReplaced && (
                    <p
                      style={{
                        margin: "6px 0 0",
                        fontSize: "12px",
                        color: "var(--danger)",
                      }}
                    >
                      {t.domains.citesReplaced}
                    </p>
                  )}
                  <span
                    style={{
                      marginTop: "10px",
                      display: "inline-block",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: isSelected ? "var(--brand, #2f6f4e)" : undefined,
                    }}
                  >
                    {isSelected
                      ? t.domains.shown
                      : fill(t.domains.show, { n: d.markerCodes.length })}
                  </span>
                </button>
              </article>
            );
          })}
        </section>
      )}

      <div className="section-header">
        <div>
          <h2>{t.evidence.title}</h2>
          <p>
            {selected ? (
              <>
                {t.evidence.noteDomain}{" "}
                <span lang={GERMAN}>{selected.axisLabel}</span>.
              </>
            ) : (
              t.evidence.noteAll
            )}
          </p>
        </div>
        {selected && (
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => setSelectedDomain(null)}
          >
            {t.evidence.showAll}
          </button>
        )}
      </div>
      <div
        className="lage-filters"
        role="group"
        aria-label={t.evidence.filtersAria}
      >
        {REF_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            className="tab"
            aria-pressed={refFilter === f}
            onClick={() => setRefFilter(f)}
          >
            {t.evidence.filters[f]}
          </button>
        ))}
      </div>
      <section
        className="card evidence-table-card"
        aria-labelledby="evidence-heading"
      >
        <h3 className="sr-only" id="evidence-heading">
          {t.evidence.title}
        </h3>
        <div className="table-wrap">
          <table className="marker-table">
            <caption className="sr-only">{t.evidence.caption}</caption>
            <thead>
              <tr>
                <th>{t.evidence.columns.marker}</th>
                <th>{t.evidence.columns.current}</th>
                <th>{t.evidence.columns.position}</th>
                <th>{t.evidence.columns.change}</th>
                <th>{t.evidence.columns.reference}</th>
                <th>{t.evidence.columns.codeStatus}</th>
              </tr>
            </thead>
            <tbody>
              {visiblePrimary.map((m, i) => (
                <tr key={i}>
                  <td>
                    <span className="marker-name">{m.name}</span>
                  </td>
                  <td
                    className={
                      m.sourceNote?.kind === "text" ? "source-text" : "num"
                    }
                  >
                    {m.current}
                  </td>
                  <td>
                    <LageCell marker={m} t={t.evidence} />
                  </td>
                  <td>
                    <ChangeCell marker={m} />
                  </td>
                  <td>{m.reference}</td>
                  <CodeStatusCell marker={m} t={messages.patientPage} />
                </tr>
              ))}
              {visiblePrimary.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    style={{ color: "var(--muted)", padding: "18px" }}
                  >
                    {refFilter === "outside"
                      ? t.evidence.empty.outside
                      : refFilter === "no_ref"
                        ? t.evidence.empty.no_ref
                        : selected
                          ? t.evidence.empty.domain
                          : t.evidence.empty.all}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selected && secondaryMarkers.length > 0 && (
        <>
          <div className="section-header">
            <div>
              <h2>{t.secondary.title}</h2>
              <p>
                {t.secondary.noteBefore}{" "}
                <span lang={GERMAN}>{selected.axisLabel}</span>
                {t.secondary.noteAfter}
              </p>
            </div>
          </div>
          <section
            className="card evidence-table-card"
            aria-label={`${t.secondary.label} ${selected.axisLabel}`}
          >
            <div className="table-wrap">
              <table className="marker-table">
                <caption className="sr-only">
                  {t.secondary.label}{" "}
                  <span lang={GERMAN}>{selected.axisLabel}</span>
                </caption>
                <thead>
                  <tr>
                    <th>{t.evidence.columns.marker}</th>
                    <th>{t.evidence.columns.primaryDomain}</th>
                    <th>{t.evidence.columns.current}</th>
                    <th>{t.evidence.columns.position}</th>
                    <th>{t.evidence.columns.change}</th>
                    <th>{t.evidence.columns.reference}</th>
                    <th>{t.evidence.columns.codeStatus}</th>
                  </tr>
                </thead>
                <tbody>
                  {secondaryMarkers.map((m, i) => (
                    <tr key={i}>
                      <td>
                        <span className="marker-name">{m.name}</span>
                      </td>
                      <td lang={m.primaryDomainLabel ? GERMAN : undefined}>
                        {m.primaryDomainLabel ?? "—"}
                      </td>
                      <td
                        className={
                          m.sourceNote?.kind === "text" ? "source-text" : "num"
                        }
                      >
                        {m.current}
                      </td>
                      <td>
                        <LageCell marker={m} t={t.evidence} />
                      </td>
                      <td>
                        <ChangeCell marker={m} />
                      </td>
                      <td>{m.reference}</td>
                      <CodeStatusCell marker={m} t={messages.patientPage} />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <div className="section-header">
        <div>
          <h2>{t.audit.title}</h2>
          <p>{t.audit.note}</p>
        </div>
      </div>
      <section
        className="card"
        style={{ padding: "16px 17px" }}
        aria-label={t.audit.title}
      >
        <AuditSteps steps={view.auditSteps} copy={p.audit.steps} />
      </section>

      <div className="action-bar">
        <div className="action-bar-copy">
          <strong>
            {fill(t.bar.status, {
              version: view.versionNo,
              status: statusLabel,
            })}
          </strong>
          <span>
            {statusHint(
              view.status,
              sessionRole,
              view.citesReplaced,
              t.bar.hint,
            )}
          </span>
        </div>
        <div className="action-bar-buttons">
          {canRework && !editing && (
            <button
              className="btn btn-primary"
              type="button"
              disabled={pending}
              onClick={startRework}
            >
              {t.bar.rework}
            </button>
          )}
          {canRedraft && !editing && (
            <button
              className="btn btn-primary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("redraft")}
            >
              {t.bar.redraft}
            </button>
          )}
          {canReject && (
            <button
              className="btn btn-secondary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("reject")}
            >
              {t.bar.reject}
            </button>
          )}
          {canApprove && (
            <button
              className="btn btn-primary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("approve")}
            >
              <Icon name="check" />
              {t.bar.approve}
            </button>
          )}
          {canRelease && (
            <button
              className="btn btn-primary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("release")}
            >
              <Icon name="check" />
              {t.bar.release}
            </button>
          )}
        </div>
      </div>

      {dialog && (
        <Dialog
          onClose={closeDialog}
          labelledBy="review-dialog-title"
          describedBy="review-dialog-copy"
          initialFocusRef={dialog === "approve" ? confirmRef : undefined}
          lockScroll
          backdropClassName="dialog-backdrop"
          dialogClassName="dialog"
        >
          <div className="dialog-head">
            <div>
              <h2 id="review-dialog-title">
                {dialog === "release" && releasedUrl
                  ? t.dialog.title.released
                  : t.dialog.title[dialog]}
              </h2>
              <p id="review-dialog-copy">
                {dialog === "approve" && t.dialog.body.approve}
                {dialog === "reject" && t.dialog.body.reject}
                {dialog === "redraft" &&
                  `${t.dialog.body.redraft} ${
                    view.status === "released"
                      ? t.dialog.body.redraftReleased
                      : t.dialog.body.redraftOther
                  }`}
                {dialog === "release" &&
                  (releasedUrl
                    ? t.dialog.body.released
                    : t.dialog.body.release)}
              </p>
            </div>
            <button
              className="icon-btn"
              type="button"
              aria-label={t.dialog.close}
              onClick={closeDialog}
            >
              <Icon name="close" />
            </button>
          </div>
          {dialog === "reject" && (
            <fieldset
              style={{ margin: "17px 0 0", padding: 0, border: "none" }}
            >
              <legend
                style={{
                  padding: 0,
                  marginBottom: "8px",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                {t.dialog.reason}
              </legend>
              {REJECTION_REASONS.map((option) => (
                <label
                  key={option.reason}
                  style={{
                    display: "flex",
                    gap: "9px",
                    alignItems: "flex-start",
                    padding: "5px 0",
                    fontSize: "12.5px",
                    lineHeight: 1.45,
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="rejection-reason"
                    value={option.reason}
                    checked={rejectReason === option.reason}
                    onChange={() => setRejectReason(option.reason)}
                    disabled={pending}
                    style={{ marginTop: "3px" }}
                  />
                  <span lang={GERMAN}>
                    <strong>{option.label}</strong> — {option.desc}
                  </span>
                </label>
              ))}
            </fieldset>
          )}
          {dialog === "approve" && (
            <label className="checkbox" style={{ marginTop: "17px" }}>
              <input
                ref={confirmRef}
                type="checkbox"
                checked={confirmChecked}
                onChange={(e) => setConfirmChecked(e.target.checked)}
              />
              <span>{t.dialog.confirm}</span>
            </label>
          )}
          {dialog === "release" && releasedUrl && (
            <div style={{ marginTop: "17px" }}>
              <label className="field">
                <span className="field-label">{t.dialog.link}</span>
                <input
                  className="input"
                  readOnly
                  value={releasedUrl}
                  onFocus={(e) => e.currentTarget.select()}
                />
              </label>
            </div>
          )}
          <div className="dialog-actions">
            {dialog === "release" && releasedUrl ? (
              <>
                <button
                  className="btn btn-secondary"
                  type="button"
                  onClick={() => {
                    void navigator.clipboard
                      .writeText(releasedUrl)
                      .then(() => toast(t.toast.copied));
                  }}
                >
                  {t.dialog.copyLink}
                </button>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={closeDialog}
                >
                  {t.dialog.done}
                </button>
              </>
            ) : (
              <>
                <button
                  className="btn btn-secondary"
                  type="button"
                  disabled={pending}
                  onClick={closeDialog}
                >
                  {t.dialog.cancel}
                </button>
                <button
                  className="btn btn-primary"
                  type="button"
                  disabled={
                    pending ||
                    (dialog === "approve" && !confirmChecked) ||
                    (dialog === "reject" && rejectReason === null)
                  }
                  onClick={() => runAction(dialog)}
                >
                  {t.dialog.submit[dialog]}
                </button>
              </>
            )}
          </div>
        </Dialog>
      )}
    </>
  );
}
