"use client";

import { Fragment, useEffect, useRef, useState, useTransition } from "react";

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
import { lageLabel } from "@/lib/lageCopy";
import {
  reportStage,
  statusHint,
  type MarkerView,
  type ReviewView,
} from "@/lib/presenters/review";

// "Veränderung" cell: the withheld-delta comparability note (text-carried, no color-alone) when the
// comparison was suppressed (§9), else the normal delta. Shared by both observation tables.
function ChangeCell({ marker }: { marker: MarkerView }) {
  if (!marker.comparabilityShort)
    return <span className="num">{marker.change}</span>;
  return (
    <span
      className="comparability-note"
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
function LageCell({ marker }: { marker: MarkerView }) {
  const l = lageLabel(marker.lagePosition);
  const bar = marker.lageBar;
  const intervalText =
    marker.reference === "—"
      ? "kein Referenzintervall hinterlegt"
      : marker.reference;
  return (
    <div className="lage-cell">
      <span className={`badge ${l.badge} no-dot lage-pill`}>
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
              Referenz {marker.referenceRange}
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
          keine Skala
        </span>
      )}
      <span className="sr-only">
        {`${marker.name} ${marker.current}; Referenzintervall ${intervalText}; ${l.sentence}.`}
      </span>
    </div>
  );
}

type RefFilter = "all" | "outside" | "no_ref";

const REF_FILTERS: { key: RefFilter; label: string }[] = [
  { key: "all", label: "Alle" },
  { key: "outside", label: "Außerhalb Referenz" },
  { key: "no_ref", label: "Ohne Referenz" },
];

function matchesRefFilter(marker: MarkerView, filter: RefFilter): boolean {
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
  const stage = reportStage(view.status, view.edited, view.citesReplaced);
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
      toast("Überarbeitung als neue Version gespeichert.");
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
              : { ok: false as const, error: "Bitte einen Grund wählen." }
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
          ? "Bericht genehmigt."
          : kind === "redraft"
            ? "Neuer Entwurf aus den aktuellen Werten erstellt."
            : "Bericht zurückgewiesen.",
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
    ? view.markers.filter((m) => selected.markerCodes.includes(m.code))
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
          !selected.markerCodes.includes(m.code),
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
              <span>{view.ageProfile}</span>
              <span>Bericht · v{view.versionNo}</span>
            </div>
          </div>
          <span className={`badge ${view.statusBadge}`}>
            {view.statusLabel}
          </span>
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
          <p>
            Jede Aussage bleibt auf die zugrunde liegenden Beobachtungen
            zurückführbar.
          </p>
        </div>
        <span className="badge badge-brand no-dot">{stage.badge}</span>
      </div>

      <section className="card summary-card" aria-label={stage.title}>
        <span className="kicker">
          {view.edited
            ? "Klinisch überarbeitete Fassung"
            : "Deterministische Zusammenfassung"}
        </span>
        {view.statements.length === 0 && (
          <p style={{ marginTop: "12px" }}>
            Für diesen Bericht liegen keine Aussagen vor.
          </p>
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
            <strong>Zurückgewiesen.</strong>{" "}
            {rejection
              ? `Grund: ${rejection.label}. ${rejection.desc}`
              : "Für diese Zurückweisung wurde kein Grund erfasst."}
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
            Überarbeitung nach einer Zurückweisung. Damaliger Grund:{" "}
            <strong>{reworked.label}</strong>. {reworked.desc}
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
            Ein zitierter Wert wurde vom Labor korrigiert. Diese Fassung kann
            nicht genehmigt oder freigegeben werden.
            {view.status === "released" &&
              " Der Zugriff der Patientin auf diese Fassung wird erst mit einem neuen Entwurf zurückgezogen."}
            {sessionRole === "clinician"
              ? " Erstellen Sie einen neuen Entwurf aus den aktuellen Werten."
              : " Ein neuer Entwurf ist der klinischen Rolle vorbehalten."}
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
                    Aussage {index + 1}
                    {row.removed ? " · wird entfernt" : ""}
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
                    {e.label}
                    {e.status && e.status !== "published"
                      ? ` · ${e.status}`
                      : ""}
                    {e.superseded ? " · vom Labor korrigiert" : ""}
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
                  {row.removed
                    ? "Aussage wiederherstellen"
                    : "Aussage entfernen"}
                </button>
              )}
            </div>
          );
        })}
        {editing && (
          <div style={{ marginTop: "16px" }}>
            <p>
              Die Belege bleiben an die jeweilige Aussage gebunden. Beim
              Speichern entsteht Version v{view.versionNo + 1} als Entwurf; die
              zurückgewiesene Version v{view.versionNo} bleibt erhalten. Die
              neue Version muss erneut genehmigt und freigegeben werden.
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
                Als neue Version speichern
              </button>
              <button
                className="btn btn-secondary"
                type="button"
                disabled={pending}
                onClick={cancelRework}
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}
      </section>

      <div className="section-header">
        <div>
          <h2>Domänen-Interpretation</h2>
          <p>
            Sechs Domänen-Achsen · Actionability-Verdict je Achse. Kein Score.
          </p>
        </div>
        {view.runNumber != null && (
          <span className="badge badge-brand no-dot">
            Run #{view.runNumber}
          </span>
        )}
      </div>
      {view.domains.length === 0 ? (
        <section
          className="card"
          style={{ padding: "20px" }}
          aria-label="Domänen-Interpretation"
        >
          <div className="notice notice-brand">
            <Icon name="shieldInfo" />
            <span>
              Für diese Patientin liegt noch kein Interpretation-Run vor.
            </span>
          </div>
        </section>
      ) : (
        <section
          aria-label="Domänen-Interpretation"
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
                    <strong>{d.axisLabel}</strong>
                    <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                      {d.reviewed ? "✓ reviewt" : "Entwurf"}
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
                    <span className="source-link">{d.actionabilityLabel}</span>
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "12px",
                      color: "var(--muted)",
                    }}
                  >
                    Follow-up-Adäquanz: {d.adequacyLabel}
                  </p>
                  {d.citesReplaced && (
                    <p
                      style={{
                        margin: "6px 0 0",
                        fontSize: "12px",
                        color: "var(--danger)",
                      }}
                    >
                      Stützt sich auf einen vom Labor korrigierten Wert —
                      Interpretation prüfen.
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
                      ? "✓ Biomarker im Beobachtungsnachweis"
                      : `Biomarker ansehen (${d.markerCodes.length})`}
                  </span>
                </button>
              </article>
            );
          })}
        </section>
      )}

      <div className="section-header">
        <div>
          <h2>Beobachtungsnachweis</h2>
          <p>
            {selected
              ? `Eigene Beobachtungen der Domäne: ${selected.axisLabel}.`
              : "Gemessene Werte, Einheiten, Referenzintervalle und Provenienz — mit Lage zum Referenzintervall."}
          </p>
        </div>
        {selected && (
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => setSelectedDomain(null)}
          >
            Alle anzeigen
          </button>
        )}
      </div>
      <div
        className="lage-filters"
        role="group"
        aria-label="Nach Lage zum Referenzintervall filtern"
      >
        {REF_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className="tab"
            aria-pressed={refFilter === f.key}
            onClick={() => setRefFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>
      <section
        className="card evidence-table-card"
        aria-labelledby="evidence-heading"
      >
        <h3 className="sr-only" id="evidence-heading">
          Beobachtungsnachweis
        </h3>
        <div className="table-wrap">
          <table className="marker-table">
            <caption className="sr-only">
              Gemessene Beobachtungen dieses Assessments
            </caption>
            <thead>
              <tr>
                <th>Marker</th>
                <th>Aktuell</th>
                <th>Lage zum Referenzintervall</th>
                <th>Veränderung</th>
                <th>Referenz</th>
                <th>Code / Status</th>
              </tr>
            </thead>
            <tbody>
              {visiblePrimary.map((m, i) => (
                <tr key={i}>
                  <td>
                    <span className="marker-name">{m.name}</span>
                  </td>
                  <td className="num">{m.current}</td>
                  <td>
                    <LageCell marker={m} />
                  </td>
                  <td>
                    <ChangeCell marker={m} />
                  </td>
                  <td>{m.reference}</td>
                  <td className="source">
                    {m.code}
                    {m.reviewRequired ? ` · ${m.status}` : ""}
                    {m.superseded ? " · durch Laborkorrektur ersetzt" : ""}
                    {m.inputReplaced
                      ? " · Eingangswert durch Laborkorrektur ersetzt"
                      : ""}
                  </td>
                </tr>
              ))}
              {visiblePrimary.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    style={{ color: "var(--muted)", padding: "18px" }}
                  >
                    {refFilter === "outside"
                      ? "Keine Marker außerhalb des Referenzintervalls."
                      : refFilter === "no_ref"
                        ? "Keine Marker ohne hinterlegte Referenz."
                        : selected
                          ? "Keine Beobachtungen für diese Domäne."
                          : "Keine Beobachtungen vorhanden."}
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
              <h2>Sekundär relevant</h2>
              <p>
                Auch für {selected.axisLabel} relevant. Zur Übersicht angezeigt
                – geführt und bewertet wird jeder Wert in seiner Primärdomäne;
                hieraus wird keine Domänen-Bewertung abgeleitet.
              </p>
            </div>
          </div>
          <section
            className="card evidence-table-card"
            aria-label={`Sekundär relevante Beobachtungen für ${selected.axisLabel}`}
          >
            <div className="table-wrap">
              <table className="marker-table">
                <caption className="sr-only">
                  Sekundär relevante Beobachtungen für {selected.axisLabel}
                </caption>
                <thead>
                  <tr>
                    <th>Marker</th>
                    <th>Primärdomäne</th>
                    <th>Aktuell</th>
                    <th>Lage zum Referenzintervall</th>
                    <th>Veränderung</th>
                    <th>Referenz</th>
                    <th>Code / Status</th>
                  </tr>
                </thead>
                <tbody>
                  {secondaryMarkers.map((m, i) => (
                    <tr key={i}>
                      <td>
                        <span className="marker-name">{m.name}</span>
                      </td>
                      <td>{m.primaryDomainLabel ?? "—"}</td>
                      <td className="num">{m.current}</td>
                      <td>
                        <LageCell marker={m} />
                      </td>
                      <td>
                        <ChangeCell marker={m} />
                      </td>
                      <td>{m.reference}</td>
                      <td className="source">
                        {m.code}
                        {m.reviewRequired ? ` · ${m.status}` : ""}
                        {m.superseded ? " · durch Laborkorrektur ersetzt" : ""}
                        {m.inputReplaced
                          ? " · Eingangswert durch Laborkorrektur ersetzt"
                          : ""}
                      </td>
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
          <h2>Audit-Status</h2>
          <p>
            Fortschritt von Datenerfassung bis Patientenfreigabe (Live-Status).
          </p>
        </div>
      </div>
      <section className="card audit-card" aria-label="Audit-Status">
        <div className="audit-steps">
          {view.auditSteps.map((s, i) => (
            <Fragment key={s.label}>
              <div className={`audit-step ${s.state}`.trim()}>
                <span className="audit-step-dot">{s.dot}</span>
                <span className="audit-step-copy">
                  <strong>{s.label}</strong>
                  <span>{s.sub}</span>
                </span>
              </div>
              {i < view.auditSteps.length - 1 && (
                <span className="audit-line" aria-hidden="true" />
              )}
            </Fragment>
          ))}
        </div>
      </section>

      <div className="action-bar">
        <div className="action-bar-copy">
          <strong>
            Bericht v{view.versionNo} · Status: {view.statusLabel}
          </strong>
          <span>
            {statusHint(view.status, sessionRole, view.citesReplaced)}
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
              Überarbeiten
            </button>
          )}
          {canRedraft && !editing && (
            <button
              className="btn btn-primary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("redraft")}
            >
              Neuen Entwurf erstellen
            </button>
          )}
          {canReject && (
            <button
              className="btn btn-secondary"
              type="button"
              disabled={pending}
              onClick={() => setDialog("reject")}
            >
              Zurückweisen
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
              Bericht genehmigen
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
              An Patientin freigeben
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
                {dialog === "approve" && "Bericht genehmigen?"}
                {dialog === "reject" && "Bericht zurückweisen?"}
                {dialog === "redraft" && "Neuen Entwurf erstellen?"}
                {dialog === "release" &&
                  (releasedUrl
                    ? "Freigegeben — Zugriffslink"
                    : "An Patientin freigeben?")}
              </h2>
              <p id="review-dialog-copy">
                {dialog === "approve" &&
                  "Sie bestätigen, dass Sie die sichtbaren Beobachtungen, Referenzintervalle und Quellen geprüft haben. Die Genehmigung wird serverseitig geschrieben, ist Ihnen zugeordnet und wird auditiert."}
                {dialog === "reject" &&
                  "Die aktuelle Version wird als zurückgewiesen festgehalten (zugeordnet und auditiert), zusammen mit dem gewählten Grund. Wer den Bericht überarbeitet, sieht diesen Grund; eine Überarbeitung erstellt eine neue Version."}
                {dialog === "redraft" &&
                  `Aus den aktuell gültigen Werten wird eine neue Entwurfsversion erstellt. Die bisherige Version bleibt gespeichert, wird hier aber nicht mehr angezeigt; manuell überarbeitete Formulierungen werden nicht übernommen. ${
                    view.status === "released"
                      ? "Der Zugriff der Patientin auf den freigegebenen Bericht wird damit zurückgezogen, bis die neue Version genehmigt und erneut freigegeben ist."
                      : "Die neue Version muss genehmigt und freigegeben werden."
                  }`}
                {dialog === "release" &&
                  (releasedUrl
                    ? "Der Bericht ist freigegeben. Synthetische Demo: Den Link manuell und sicher übermitteln — kein automatischer Versand."
                    : "Die Freigabe ist einwilligungsgebunden (report_release), wird Ihnen zugeordnet und auditiert. Die Patientin sieht ausschließlich die freigegebene Version.")}
              </p>
            </div>
            <button
              className="icon-btn"
              type="button"
              aria-label="Dialog schließen"
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
                Grund der Zurückweisung
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
                  <span>
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
              <span>
                Ich habe die offenen Hinweise geprüft und bestätige die
                klinische Dokumentation.
              </span>
            </label>
          )}
          {dialog === "release" && releasedUrl && (
            <div style={{ marginTop: "17px" }}>
              <label className="field">
                <span className="field-label">
                  Zugriffslink (einmalig angezeigt)
                </span>
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
                      .then(() => toast("Link kopiert."));
                  }}
                >
                  Link kopieren
                </button>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={closeDialog}
                >
                  Schließen
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
                  Abbrechen
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
                  {dialog === "approve" && "Genehmigen"}
                  {dialog === "reject" && "Zurückweisen"}
                  {dialog === "redraft" && "Neuen Entwurf erstellen"}
                  {dialog === "release" && "Freigeben"}
                </button>
              </>
            )}
          </div>
        </Dialog>
      )}
    </>
  );
}
