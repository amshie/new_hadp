"use client";

import { useState, useTransition, type CSSProperties } from "react";

import { Dialog } from "@/components/vitabahn/Dialog";
import { EmptyState } from "@/components/vitabahn/EmptyState";
import type { ReviewQueueItem } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { byCount, fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";

import { resolveReviewItemAction } from "./actions";

type Wording = Messages["reviewQueue"];

// The page follows the interface language (ADR-0007); numbers and dates keep their format.
// The reasons below are a closed vocabulary, and a closed vocabulary keeps its German until
// its English names are confirmed — they stay German on an English page, and say so.
const GERMAN = "de";

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

// A value the patient already holds, as the source wrote it, with its sampling time and
// where it stands. The time matters: a value of the same day is not always the same sample.
function heldLabel(held: HeldValue, t: Wording): string {
  const value = `${held.original_value} ${held.original_unit ?? ""}`.trim();
  const status: Record<string, string> = t.heldStatus;
  const where = held.superseded
    ? t.heldStatus.superseded
    : (status[held.review_status] ?? held.review_status);
  return `${value} · ${fmtObserved(held.observed_at, held.observed_at_is_date_only)} (${where})`;
}

// The reference bounds the platform holds for a queued value: what a position against the
// interval is stated from once the value is published. Said so the reviewer sees it before.
function heldReference(item: ReviewQueueItem, t: Wording): string | null {
  const { reference_low: low, reference_high: high } = item;
  if (low == null && high == null) return null;
  const unit = item.reference_unit ? ` ${item.reference_unit}` : "";
  const bounds =
    low != null && high != null
      ? `${low}–${high}`
      : high != null
        ? fill(t.reference.upper, { high })
        : fill(t.reference.lower, { low: low ?? "" });
  return fill(
    item.reference_converted ? t.reference.lineConverted : t.reference.line,
    { bounds: `${bounds}${unit}` },
  );
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

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "11px 14px",
  fontFamily: "var(--font-mono)",
  fontSize: "11px",
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
  const t = useI18n().t.reviewQueue;

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
      <div className="vb-ov-pagehead" style={{ marginBottom: "18px" }}>
        <div style={{ minWidth: 0 }}>
          <h1 className="vb-ov-h1" style={{ marginTop: 0 }}>
            {t.title}
          </h1>
          <p className="vb-ov-lead">
            {t.lead}
            {!canResolve && t.readOnly}
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="vb-ov-card">
          <EmptyState>{t.empty}</EmptyState>
        </div>
      ) : (
        // On a narrow screen the table scrolls sideways: clipped, its last column — the
        // decision — was out of reach on a phone.
        <div
          className="vb-ov-card"
          style={{ position: "relative", overflowX: "auto" }}
        >
          <table
            style={{
              width: "100%",
              minWidth: "680px",
              borderCollapse: "collapse",
            }}
            aria-label={t.tableAria}
          >
            <thead>
              <tr>
                <th style={thStyle}>{t.columns.patient}</th>
                <th style={thStyle}>{t.columns.value}</th>
                <th style={thStyle}>{t.columns.reason}</th>
                <th style={thStyle}>{t.columns.observed}</th>
                <th style={thStyle}>{t.columns.decision}</th>
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
                    {heldReference(item, t) && (
                      <div style={contextStyle}>{heldReference(item, t)}</div>
                    )}
                    {item.replaces && (
                      <div style={contextStyle}>
                        {fill(t.replacesOnPublish, {
                          held: heldLabel(item.replaces, t),
                        })}
                        {item.replaces_cited_in_report_count > 0 &&
                          byCount(
                            t.citedIn,
                            item.replaces_cited_in_report_count,
                          )}
                      </div>
                    )}
                    {item.related.map((held) => (
                      <div key={held.observation_id} style={contextStyle}>
                        {fill(t.alreadyHeld, { held: heldLabel(held, t) })}
                      </div>
                    ))}
                  </td>
                  <td style={tdStyle} lang={GERMAN}>
                    {reasonLabel(item.reason)}
                  </td>
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
                          {t.publish}
                        </button>
                        <button
                          type="button"
                          style={btnSec}
                          disabled={pending}
                          onClick={() =>
                            setConfirm({ item, decision: "reject" })
                          }
                        >
                          {t.reject}
                        </button>
                      </div>
                    ) : (
                      <span
                        style={{
                          color: "var(--text-faint)",
                          fontSize: "12.5px",
                        }}
                      >
                        {t.clinicalRoleRequired}
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
          dialogClassName="vb-ov-card"
          dialogStyle={{
            width: "480px",
            maxWidth: "100%",
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
              ? t.dialog.publishTitle
              : t.dialog.rejectTitle}
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
            <span lang={GERMAN}>{reasonLabel(confirm.item.reason)}</span>.{" "}
            {confirm.decision === "publish"
              ? t.dialog.publishBody
              : t.dialog.rejectBody}
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
              {fill(
                confirm.decision === "publish"
                  ? t.dialog.replacesPublish
                  : t.dialog.replacesReject,
                { held: heldLabel(confirm.item.replaces, t) },
              )}
              {confirm.decision === "publish" &&
                confirm.item.replaces_cited_in_report_count > 0 &&
                byCount(
                  t.dialog.citedInReports,
                  confirm.item.replaces_cited_in_report_count,
                )}
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
              {t.cancel}
            </button>
            <button
              type="button"
              style={confirm.decision === "publish" ? btnPri : btnSec}
              disabled={pending}
              onClick={run}
            >
              {confirm.decision === "publish" ? t.publish : t.reject}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
