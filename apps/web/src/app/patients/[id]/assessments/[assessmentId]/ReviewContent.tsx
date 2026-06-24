"use client";

import { Fragment, useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toaster";
import type { MarkerView, ReviewView } from "@/lib/presenters/review";

// "Veränderung" cell: the withheld-delta comparability note (text-carried, no color-alone) when the
// comparison was suppressed (§9), else the normal delta. Shared by both observation tables.
function ChangeCell({ marker }: { marker: MarkerView }) {
  if (!marker.comparabilityShort) return <span className="num">{marker.change}</span>;
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

const NOT_IMPLEMENTED = "Diese Ansicht ist im Prototyp noch nicht umgesetzt.";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((p) => p[0] ?? "")
      .join("") || "–"
  ).toUpperCase();
}

export function ReviewContent({ view }: { view: ReviewView }) {
  const toast = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<number | null>(null);
  const selected =
    selectedDomain != null ? (view.domains[selectedDomain] ?? null) : null;
  // Beobachtungsnachweis shows the selected domain's own biomarkers, or all when none is selected.
  const primaryMarkers = selected
    ? view.markers.filter((m) => selected.markerCodes.includes(m.code))
    : view.markers;
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

  useEffect(() => {
    document.body.classList.toggle("modal-open", dialogOpen);
    if (!dialogOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDialogOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [dialogOpen]);

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
        <div className="page-actions">
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() =>
              toast(
                "Quelldokumente würden hier in einem sicheren Viewer geöffnet.",
              )
            }
          >
            <Icon name="reports" />
            Quelldokumente
          </button>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() =>
              toast(
                "Weitere Patientenaktionen sind im Prototyp nicht angebunden.",
              )
            }
          >
            Mehr
          </button>
        </div>
      </header>

      <nav className="review-tabs" aria-label="Patientenansichten">
        <a href="#" aria-current="page" onClick={(e) => e.preventDefault()}>
          Assessment
        </a>
        {["Laborwerte", "Verlauf", "Dokumente", "Bericht"].map((t) => (
          <a
            key={t}
            href="#"
            onClick={(e) => {
              e.preventDefault();
              toast(NOT_IMPLEMENTED);
            }}
          >
            {t}
          </a>
        ))}
      </nav>

      <div className="draft-banner" role="status">
        <Icon name="alert" />
        <span>
          <strong>Systementwurf – nicht freigegeben.</strong> Aussagen müssen
          anhand der Quellen geprüft und vom klinischen Team signiert werden.
        </span>
      </div>

      <div className="section-header">
        <div>
          <h2>Quellengebundener Entwurf</h2>
          <p>
            Jede Aussage bleibt auf die zugrunde liegenden Beobachtungen
            zurückführbar.
          </p>
        </div>
        <span className="badge badge-brand no-dot">Nicht freigegeben</span>
      </div>

      <section
        className="card summary-card"
        aria-label="Quellengebundener Entwurf"
      >
        <span className="kicker">Deterministische Zusammenfassung</span>
        {view.statements.length === 0 && (
          <p style={{ marginTop: "12px" }}>
            Für diesen Bericht liegen keine Aussagen vor.
          </p>
        )}
        {view.statements.map((s) => (
          <div
            className="system-draft"
            key={s.id}
            style={{ marginTop: "14px" }}
          >
            <p style={{ marginTop: 0 }}>{s.text}</p>
            <div className="source-links">
              {s.evidence.map((e, i) => (
                <span
                  key={i}
                  className={`source-link${e.missing ? " " : ""}`}
                  style={
                    e.missing
                      ? {
                          color: "var(--danger)",
                          borderColor: "var(--btn-danger-border)",
                        }
                      : undefined
                  }
                >
                  {e.label}
                  {e.status && e.status !== "published" ? ` · ${e.status}` : ""}
                </span>
              ))}
            </div>
          </div>
        ))}
      </section>

      <div className="section-header">
        <div>
          <h2>Domänen-Interpretation</h2>
          <p>
            Sechs Domänen-Achsen · Actionability-Verdict je Achse. Kein Score.
          </p>
        </div>
        {view.runNumber != null && (
          <span className="badge badge-brand no-dot">Run #{view.runNumber}</span>
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
                    style={{ margin: 0, fontSize: "12px", color: "var(--muted)" }}
                  >
                    Follow-up-Adäquanz: {d.adequacyLabel}
                  </p>
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
              : "Gemessene Werte, Einheiten, Referenzintervalle und Provenienz."}
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
                <th>Vorher</th>
                <th>Veränderung</th>
                <th>Referenz</th>
                <th>Code / Status</th>
              </tr>
            </thead>
            <tbody>
              {primaryMarkers.map((m, i) => (
                <tr key={i}>
                  <td>
                    <span className="marker-name">{m.name}</span>
                  </td>
                  <td className="num">{m.current}</td>
                  <td className="num">{m.previous}</td>
                  <td>
                    <ChangeCell marker={m} />
                  </td>
                  <td>{m.reference}</td>
                  <td className="source">
                    {m.code}
                    {m.reviewRequired ? ` · ${m.status}` : ""}
                  </td>
                </tr>
              ))}
              {primaryMarkers.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    style={{ color: "var(--muted)", padding: "18px" }}
                  >
                    {selected
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
                Auch für {selected.axisLabel} relevant. Zur Übersicht angezeigt –
                geführt und bewertet wird jeder Wert in seiner Primärdomäne;
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
                    <th>Vorher</th>
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
                      <td className="num">{m.previous}</td>
                      <td>
                        <ChangeCell marker={m} />
                      </td>
                      <td>{m.reference}</td>
                      <td className="source">
                        {m.code}
                        {m.reviewRequired ? ` · ${m.status}` : ""}
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
            Die Signatur ist noch nicht an den Freigabe-Lifecycle angebunden
            (Gate G2); sie veröffentlicht keinen Bericht an die Patientin.
          </span>
        </div>
        <div className="action-bar-buttons">
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => toast("Der Vorgang wurde nicht verändert.")}
          >
            Zurückstellen
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => setDialogOpen(true)}
          >
            <Icon name="check" />
            Review signieren
          </button>
        </div>
      </div>

      {dialogOpen && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDialogOpen(false);
          }}
        >
          <section
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-dialog-title"
            aria-describedby="review-dialog-copy"
          >
            <div className="dialog-head">
              <div>
                <h2 id="review-dialog-title">Klinischen Review signieren?</h2>
                <p id="review-dialog-copy">
                  Sie bestätigen, dass Sie die sichtbaren Beobachtungen,
                  Referenzintervalle und Quellen geprüft haben. Hinweis: Die
                  Anbindung an den Freigabe-Lifecycle ist noch nicht freigegeben
                  (Gate G2) — die Signatur wird derzeit nicht serverseitig
                  geschrieben.
                </p>
              </div>
              <button
                className="icon-btn"
                type="button"
                aria-label="Dialog schließen"
                onClick={() => setDialogOpen(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            <label className="checkbox" style={{ marginTop: "17px" }}>
              <input
                type="checkbox"
                autoFocus
                checked={confirmChecked}
                onChange={(e) => setConfirmChecked(e.target.checked)}
              />
              <span>
                Ich habe die offenen Hinweise geprüft und bestätige die
                klinische Dokumentation.
              </span>
            </label>
            <div className="dialog-actions">
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => setDialogOpen(false)}
              >
                Abbrechen
              </button>
              <button
                className="btn btn-primary"
                type="button"
                disabled={!confirmChecked}
                onClick={() => {
                  setDialogOpen(false);
                  setConfirmChecked(false);
                  toast(
                    "Signatur erfasst (Demo). Anbindung an Genehmigung/Freigabe folgt nach Gate G2.",
                  );
                }}
              >
                Signieren und weiterleiten
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
