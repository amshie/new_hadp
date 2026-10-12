"use client";

import { useState, useTransition, type CSSProperties } from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import type { ReviewQueueItem } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";

import { resolveReviewItemAction } from "./actions";

// Closed reason vocabulary (imports/normalize.py + imports/parsers/base.py +
// imports/matching.py) → neutral German labels. No verdict language: a queued value is
// undecided, never "auffällig" or graded.
const REASON_LABELS: Record<string, string> = {
  unmapped_metric: "Kennzahl nicht zugeordnet",
  unparseable_value: "Wert nicht lesbar",
  unsupported_unit: "Einheit nicht unterstützt",
  impossible_value: "Wert außerhalb der plausiblen Spanne",
  unparseable_reference: "Referenzgrenze nicht lesbar",
  ambiguous_local_time: "Uhrzeit nicht eindeutig (Zeitumstellung)",
  preliminary_report: "Vom Labor als vorläufig markiert",
  previously_reported: "Vom Labor als bereits berichtet markiert",
  corrected_result: "Vom Labor als korrigiert markiert",
  source_comment: "Laborkommentar zum Wert — Quelle prüfen",
  ambiguous_reference: "Referenzbereich nicht eindeutig — Quelle prüfen",
  multiple_result_values: "Mehrere Werte zu einer Analyse — Quelle prüfen",
  possible_duplicate:
    "Für diese Analyse und Abnahmezeit liegt bereits ein Wert vor",
  ambiguous_correction:
    "Korrektur ohne eindeutigen Bezug — frühere Werte prüfen",
};

type HeldValue = NonNullable<ReviewQueueItem["replaces"]>;

const HELD_STATUS: Record<string, string> = {
  published: "veröffentlicht",
  pending: "in Prüfung",
  rejected: "abgelehnt",
};

// A value the patient already holds, as the source wrote it, with its sampling time and
// where it stands. The time matters: a value of the same day is not always the same sample.
function heldLabel(held: HeldValue): string {
  const value = `${held.original_value} ${held.original_unit ?? ""}`.trim();
  const status = held.superseded
    ? "ersetzt"
    : (HELD_STATUS[held.review_status] ?? held.review_status);
  return `${value} · ${fmtObserved(held.observed_at, held.observed_at_is_date_only)} (${status})`;
}

// The reference bounds the platform holds for a queued value: what a position against the
// interval is stated from once the value is published. Said so the reviewer sees it before.
function heldReference(item: ReviewQueueItem): string | null {
  const { reference_low: low, reference_high: high } = item;
  if (low == null && high == null) return null;
  const unit = item.reference_unit ? ` ${item.reference_unit}` : "";
  const bounds =
    low != null && high != null
      ? `${low}–${high}`
      : high != null
        ? `obere Grenze ${high}`
        : `untere Grenze ${low}`;
  return `Referenz der Quelle${item.reference_converted ? " (umgerechnet)" : ""}: ${bounds}${unit}`;
}

function reasonLabel(reason: string): string {
  return REASON_LABELS[reason] ?? reason;
}

// A date-only value is the calendar day the source wrote (kept as midnight UTC): it is read
// back in UTC, so no zone can move it to the day before. A time is shown on the clinic's wall
// clock — the same on the server and in the browser, whatever zone either is in.
function fmtObserved(iso: string, dateOnly: boolean): string {
  const d = new Date(iso);
  const timeZone = dateOnly ? "UTC" : CLINIC_TIME_ZONE;
  const date = d.toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone,
  });
  if (dateOnly) return date;
  return `${date}, ${d.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone,
  })}`;
}

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "11px 14px",
  fontFamily: "var(--font-mono)",
  fontSize: "10.5px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  borderBottom: "1px solid var(--border-subtle)",
};

const tdStyle: CSSProperties = {
  padding: "12px 14px",
  fontSize: "13px",
  color: "var(--text-body)",
  borderBottom: "1px solid var(--border-subtle)",
  verticalAlign: "top",
};

const contextStyle: CSSProperties = {
  marginTop: "4px",
  fontSize: "11.5px",
  lineHeight: 1.4,
  color: "var(--text-muted)",
};

const btnSec: CSSProperties = {
  height: "32px",
  padding: "0 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
  fontFamily: "var(--font-text)",
  fontSize: "12.5px",
  fontWeight: 600,
  cursor: "pointer",
};

const btnPri: CSSProperties = {
  ...btnSec,
  border: "1px solid var(--brand)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
};

export function ReviewQueueContent({
  items,
  sessionRole,
  path,
}: {
  items: ReviewQueueItem[];
  sessionRole: string | null;
  path: string;
}) {
  const [confirm, setConfirm] = useState<{
    item: ReviewQueueItem;
    decision: "publish" | "reject";
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const canResolve = sessionRole === "clinician";

  const close = () => {
    setConfirm(null);
    setError(null);
  };

  const run = () => {
    if (!confirm) return;
    startTransition(async () => {
      const res = await resolveReviewItemAction(
        confirm.item.review_item_id,
        confirm.decision,
        path,
      );
      if (!res.ok) {
        setError(res.error);
        return;
      }
      close();
    });
  };

  return (
    <>
      <div style={{ marginBottom: "18px" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 800,
            fontSize: "var(--text-2xl, 26px)",
            color: "var(--text-strong)",
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          Review-Queue
        </h1>
        <p
          style={{
            margin: "6px 0 0",
            fontSize: "13px",
            color: "var(--text-muted)",
            maxWidth: "82ch",
          }}
        >
          Offene Prüfaufgaben aus dem Import — kein Wert wird ohne menschliche
          Entscheidung veröffentlicht. Angezeigt wird die Quellrepräsentation
          (Originalname, -wert, -einheit).
          {!canResolve &&
            " Die Entscheidung ist der klinischen Rolle vorbehalten (Nur-Lese-Ansicht)."}
        </p>
      </div>

      {items.length === 0 ? (
        <div
          style={{
            ...cardStyle,
            padding: "36px 24px",
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "13.5px",
          }}
        >
          Keine offenen Prüfaufgaben.
        </div>
      ) : (
        <div style={{ ...cardStyle, overflow: "hidden" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse" }}
            aria-label="Offene Prüfaufgaben"
          >
            <thead>
              <tr>
                <th style={thStyle}>Patientin/Patient</th>
                <th style={thStyle}>Wert (Quelle)</th>
                <th style={thStyle}>Grund</th>
                <th style={thStyle}>Beobachtet</th>
                <th style={thStyle}>Entscheidung</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.review_item_id}>
                  <td style={tdStyle}>
                    <div
                      style={{ fontWeight: 600, color: "var(--text-strong)" }}
                    >
                      {item.patient_display_name}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--text-faint)",
                      }}
                    >
                      {item.patient_external_ref ?? "—"}
                    </div>
                  </td>
                  <td style={tdStyle}>
                    <div
                      style={{ fontWeight: 600, color: "var(--text-strong)" }}
                    >
                      {item.original_name}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                      }}
                    >
                      {item.original_value} {item.original_unit ?? ""}
                    </div>
                    {heldReference(item) && (
                      <div style={contextStyle}>{heldReference(item)}</div>
                    )}
                    {item.replaces && (
                      <div style={contextStyle}>
                        Ersetzt bei Veröffentlichung: {heldLabel(item.replaces)}
                        {item.replaces_cited_in_report_count > 0 &&
                          ` — in ${item.replaces_cited_in_report_count} Bericht(en) zitiert`}
                      </div>
                    )}
                    {item.related.map((held) => (
                      <div key={held.observation_id} style={contextStyle}>
                        Bereits vorhanden: {heldLabel(held)}
                      </div>
                    ))}
                  </td>
                  <td style={tdStyle}>{reasonLabel(item.reason)}</td>
                  <td style={tdStyle}>
                    {fmtObserved(
                      item.observed_at,
                      item.observed_at_is_date_only,
                    )}
                  </td>
                  <td style={tdStyle}>
                    {canResolve ? (
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          type="button"
                          style={btnPri}
                          disabled={pending}
                          onClick={() =>
                            setConfirm({ item, decision: "publish" })
                          }
                        >
                          Veröffentlichen
                        </button>
                        <button
                          type="button"
                          style={btnSec}
                          disabled={pending}
                          onClick={() =>
                            setConfirm({ item, decision: "reject" })
                          }
                        >
                          Ablehnen
                        </button>
                      </div>
                    ) : (
                      <span
                        style={{
                          color: "var(--text-faint)",
                          fontSize: "12.5px",
                        }}
                      >
                        Klinische Rolle erforderlich
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {confirm && (
        <Dialog
          onClose={close}
          labelledBy="rq-dialog-title"
          lockScroll
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "480px",
            maxWidth: "100%",
            ...cardStyle,
            padding: "22px",
          }}
        >
          <h3
            id="rq-dialog-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: "var(--text-xl)",
              color: "var(--text-strong)",
              margin: 0,
            }}
          >
            {confirm.decision === "publish"
              ? "Wert veröffentlichen?"
              : "Wert ablehnen?"}
          </h3>
          <p
            style={{
              margin: "10px 0 0",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            {`${confirm.item.original_name}: ${confirm.item.original_value} ${confirm.item.original_unit ?? ""}`.trim()}
            {" — "}
            {reasonLabel(confirm.item.reason)}.{" "}
            {confirm.decision === "publish"
              ? "Der Wert wird veröffentlicht und erscheint in der klinischen Zeitleiste. Bleibt eine weitere offene Prüfaufgabe zu diesem Wert bestehen, bleibt er bis zu deren Entscheidung zurückgehalten."
              : "Der Wert wird abgelehnt und nie veröffentlicht. Die Entscheidung wird Ihnen zugeordnet und auditiert."}
          </p>
          {confirm.item.replaces && (
            <p
              style={{
                margin: "10px 0 0",
                fontSize: "12.5px",
                lineHeight: 1.5,
                color: "var(--text-strong)",
              }}
            >
              {confirm.decision === "publish"
                ? `Mit der Veröffentlichung ersetzt dieser Wert den früheren Wert ${heldLabel(confirm.item.replaces)}. Der frühere Wert bleibt unverändert erhalten und wird als ersetzt gekennzeichnet.`
                : `Der frühere Wert ${heldLabel(confirm.item.replaces)} bleibt bestehen.`}
              {confirm.decision === "publish" &&
                confirm.item.replaces_cited_in_report_count > 0 &&
                ` Er ist in ${confirm.item.replaces_cited_in_report_count} Bericht(en) zitiert: Diese können erst mit einem neuen Entwurf genehmigt oder freigegeben werden; ein bereits freigegebener Bericht bleibt für die Patientin sichtbar, bis auf der Berichtsseite ein neuer Entwurf erstellt wird.`}
            </p>
          )}
          {error && (
            <p
              role="alert"
              style={{
                margin: "12px 0 0",
                fontSize: "12.5px",
                color: "var(--danger, #b3261e)",
              }}
            >
              {error}
            </p>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
              marginTop: "20px",
            }}
          >
            <button
              type="button"
              style={btnSec}
              disabled={pending}
              onClick={close}
            >
              Abbrechen
            </button>
            <button
              type="button"
              style={confirm.decision === "publish" ? btnPri : btnSec}
              disabled={pending}
              onClick={run}
            >
              {confirm.decision === "publish" ? "Veröffentlichen" : "Ablehnen"}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
