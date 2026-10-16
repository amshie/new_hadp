"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  useTransition,
  type CSSProperties,
} from "react";

import type { IntakeBatch, IntakePendingValue } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { byCount, fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";

import { confirmGreenAction, decideIntakeValueAction } from "./actions";

// The confirmation screen (docs/product/INTAKE_AGENT.md): one proposal, every value beside the
// page region it was read from. Green confirms with one click; yellow is confirmed only after
// the region was looked at (the checkbox says so); red is corrected or rejected. The page
// measures how long a value and the whole screen took — timings the API stores with the
// decision, nothing else. No wording here rates the patient: every reason describes the
// READING of the document.

type Wording = Messages["intakePage"];
type Status = IntakePendingValue["status"];

const card: CSSProperties = {
  display: "grid",
  gridTemplateColumns:
    "minmax(220px, 1fr) minmax(260px, 1.4fr) minmax(240px, 1fr)",
  gap: "16px",
  padding: "16px 22px",
  borderTop: "1px solid var(--border-subtle)",
  alignItems: "start",
};
const label: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "11px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  margin: "0 0 6px",
};
const muted: CSSProperties = {
  fontSize: "12px",
  color: "var(--text-muted)",
  margin: "4px 0 0",
  lineHeight: 1.5,
};
const btn: CSSProperties = {
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
  ...btn,
  border: "1px solid var(--brand)",
  background: "var(--brand)",
  color: "var(--text-on-brand)",
};
const input: CSSProperties = {
  height: "32px",
  padding: "0 8px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
  fontSize: "12.5px",
  width: "100%",
};

// Status as a word in a bordered chip (never colour alone); the border tone differs as well.
const chipTone: Record<Status, string> = {
  green: "var(--ok, var(--border-default))",
  yellow: "var(--warn, var(--border-default))",
  red: "var(--btn-danger-border, var(--border-default))",
};

function fmtDate(iso: string | null, dateOnly: boolean): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: dateOnly ? "UTC" : CLINIC_TIME_ZONE,
  });
}

function fmtWhen(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("de-DE", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: CLINIC_TIME_ZONE })}, ${d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", timeZone: CLINIC_TIME_ZONE })}`;
}

function written(v: { value_text: string; unit_text: string | null }): string {
  return `${v.value_text}${v.unit_text ? ` ${v.unit_text}` : ""}`;
}

function seconds(since: number): number {
  return Math.max(0, Math.min(86400, Math.round((Date.now() - since) / 1000)));
}

export function IntakeBatchContent({
  batch,
  sessionRole,
}: {
  batch: IntakeBatch;
  sessionRole: string | null;
}) {
  const t = useI18n().t.intakePage;
  const router = useRouter();
  const canDecide = sessionRole === "clinician";
  const [pending, startTransition] = useTransition();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // When the screen was opened: `screen_seconds` of every decision made on it.
  const opened = useRef<number>(0);
  useEffect(() => {
    opened.current = Date.now();
  }, []);

  const values = batch.values;
  const openGreen = values.filter(
    (v) => v.status === "green" && !v.decision,
  ).length;
  const counts = {
    green: values.filter((v) => v.status === "green").length,
    yellow: values.filter((v) => v.status === "yellow").length,
    red: values.filter((v) => v.status === "red").length,
  };

  const confirmAllGreen = () => {
    startTransition(async () => {
      setError(null);
      setNotice(null);
      const out = await confirmGreenAction(
        batch.batch_id,
        seconds(opened.current),
      );
      if (out.ok) {
        setNotice(byCount(t.confirmedN, out.confirmed));
        router.refresh();
      } else setError(out.error);
    });
  };

  return (
    <section
      className="vb-ov-card"
      style={{ overflow: "hidden" }}
      aria-labelledby="intake-heading"
    >
      <div style={{ padding: "20px 22px 16px" }}>
        <h2
          id="intake-heading"
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-lg)",
            color: "var(--text-strong)",
            margin: 0,
          }}
        >
          {t.title}
        </h2>
        <p style={{ ...muted, maxWidth: "88ch", marginTop: "6px" }}>{t.lead}</p>
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "8px 18px",
            margin: "14px 0 0",
            fontSize: "12.5px",
          }}
        >
          <div>
            <dt style={label}>{t.file}</dt>
            <dd
              style={{
                margin: 0,
                color: "var(--text-strong)",
                wordBreak: "break-word",
              }}
            >
              {batch.filename} · {byCount(t.pages, batch.page_count)}
            </dd>
          </div>
          <div>
            <dt style={label}>{t.readBy}</dt>
            <dd style={{ margin: 0, color: "var(--text-strong)" }}>
              {batch.extraction_provider} · {batch.model_id} ·{" "}
              {batch.prompt_version}
            </dd>
          </div>
          <div>
            <dt style={label}>{t.documentDob}</dt>
            <dd style={{ margin: 0, color: "var(--text-strong)" }}>
              {fmtDate(batch.proposed_patient_date_of_birth, true) ?? t.unknown}
            </dd>
          </div>
          <div>
            <dt style={label}>{t.documentIssue}</dt>
            <dd style={{ margin: 0, color: "var(--text-strong)" }}>
              {fmtDate(batch.proposed_issue_date, true) ?? t.unknown}
            </dd>
          </div>
        </dl>
        <p
          style={{ ...muted, marginTop: "12px", color: "var(--text-strong)" }}
          aria-live="polite"
        >
          {[
            fill(t.counts.green, { n: counts.green }),
            fill(t.counts.yellow, { n: counts.yellow }),
            fill(t.counts.red, { n: counts.red }),
            byCount(t.counts.open, batch.open_count),
          ].join(" · ")}
        </p>
        {canDecide ? (
          <div
            style={{
              display: "flex",
              gap: "10px",
              alignItems: "center",
              marginTop: "12px",
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              style={btnPri}
              disabled={pending || openGreen === 0}
              onClick={confirmAllGreen}
            >
              {openGreen === 0
                ? t.confirmAllGreenNone
                : `${t.confirmAllGreen} (${openGreen})`}
            </button>
            <Link
              href={`/patients/${batch.patient_id}`}
              style={{ fontSize: "12.5px" }}
            >
              {t.back}
            </Link>
          </div>
        ) : (
          <p style={{ ...muted, marginTop: "12px" }}>{t.readOnly}</p>
        )}
        {notice && (
          <p role="status" style={{ ...muted, color: "var(--text-strong)" }}>
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" style={{ ...muted, color: "var(--text-strong)" }}>
            {error}
          </p>
        )}
      </div>

      <ol
        style={{ listStyle: "none", margin: 0, padding: 0 }}
        aria-label={t.title}
      >
        {values.map((v) => (
          <li key={v.pending_value_id}>
            <ValueRow
              batchId={batch.batch_id}
              value={v}
              canDecide={canDecide}
              opened={opened}
              t={t}
              onDecided={() => router.refresh()}
            />
          </li>
        ))}
      </ol>
    </section>
  );
}

function ValueRow({
  batchId,
  value: v,
  canDecide,
  opened,
  t,
  onDecided,
}: {
  batchId: string;
  value: IntakePendingValue;
  canDecide: boolean;
  opened: { current: number };
  t: Wording;
  onDecided: () => void;
}) {
  const [pending, startTransition] = useTransition();
  const [mode, setMode] = useState<"idle" | "correct" | "reject">("idle");
  const [viewed, setViewed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // How long this value took: from the first touch of its row to the decision.
  const touched = useRef<number | null>(null);
  const touch = () => {
    if (touched.current === null) touched.current = Date.now();
  };
  const reasons: Record<string, string> = t.reasons;
  const decided = v.decision !== null && v.decision !== undefined;
  const sampled = fmtDate(v.observed_at, v.observed_at_is_date_only);

  const decide = (body: Parameters<typeof decideIntakeValueAction>[1]) => {
    startTransition(async () => {
      setError(null);
      const out = await decideIntakeValueAction(batchId, {
        ...body,
        review_seconds: touched.current ? seconds(touched.current) : null,
        screen_seconds: seconds(opened.current),
      });
      if (out.ok) {
        setMode("idle");
        onDecided();
      } else setError(out.error);
    });
  };

  const submitCorrection = (form: HTMLFormElement) => {
    const data = new FormData(form);
    const read = (name: string) => {
      const raw = data.get(name);
      const text = typeof raw === "string" ? raw.trim() : "";
      return text;
    };
    const date = read("date");
    decide({
      pending_value_id: v.pending_value_id,
      decision: "corrected",
      correction: {
        analyte_text:
          read("analyte") !== v.analyte_text ? read("analyte") || null : null,
        value_text:
          read("value") !== v.value_text ? read("value") || null : null,
        unit_text:
          read("unit") !== (v.unit_text ?? "") ? read("unit") || null : null,
        clear_unit: read("unit") === "" && v.unit_text !== null,
        clear_reference: false,
        observed_at: date ? `${date}T00:00:00Z` : null,
        observed_at_is_date_only: date ? true : null,
      },
    });
  };

  return (
    <article
      style={card}
      aria-label={`${v.analyte_text} ${written(v)}`}
      onFocusCapture={touch}
      onClickCapture={touch}
    >
      <div>
        <p style={label}>{t.columns.value}</p>
        <p
          style={{
            margin: 0,
            fontSize: "15px",
            fontWeight: 600,
            color: "var(--text-strong)",
          }}
        >
          {v.analyte_text}
        </p>
        <p
          style={{
            margin: "2px 0 0",
            fontSize: "15px",
            color: "var(--text-strong)",
          }}
        >
          {written(v)}
        </p>
        <p style={muted}>
          {sampled ? fill(t.sampled, { date: sampled }) : t.noDate}
          {v.reference_text
            ? ` · ${fill(t.reference, { text: v.reference_text })}`
            : ""}
        </p>
        <p style={muted}>
          {v.kpi_code ? fill(t.kpi, { code: v.kpi_code }) : t.noKpi}
          {v.normalized_value &&
          v.canonical_unit &&
          v.canonical_unit !== v.unit_text
            ? ` · ${fill(t.normalized, { unit: v.canonical_unit, value: v.normalized_value })}`
            : ""}
        </p>
        <p style={muted}>
          {fill(t.confidence, {
            value: Number(v.confidence).toLocaleString("de-DE", {
              maximumFractionDigits: 2,
            }),
          })}
        </p>
      </div>

      <div>
        <p style={label}>
          {t.columns.source} · {fill(t.page, { n: v.page })}
          {v.has_region ? "" : ` · ${t.noRegion}`}
        </p>
        <img
          src={`/intake/${batchId}/region/${v.pending_value_id}`}
          alt={fill(t.regionAlt, { n: v.page, value: written(v) })}
          loading="lazy"
          style={{
            display: "block",
            maxWidth: "100%",
            maxHeight: v.has_region ? "140px" : "420px",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            background: "#fff",
          }}
        />
      </div>

      <div>
        <p style={label}>{t.columns.checks}</p>
        <p style={{ margin: 0 }}>
          <span
            style={{
              display: "inline-block",
              padding: "2px 8px",
              borderRadius: "999px",
              border: `2px solid ${chipTone[v.status]}`,
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--text-strong)",
            }}
          >
            {t.status[v.status]}
          </span>{" "}
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            {t.statusHint[v.status]}
          </span>
        </p>
        {v.reasons.length > 0 && (
          <ul
            style={{
              margin: "6px 0 0",
              paddingLeft: "18px",
              fontSize: "12px",
              color: "var(--text-body)",
              lineHeight: 1.5,
            }}
          >
            {v.reasons.map((r) => (
              <li key={r}>{reasons[r] ?? r}</li>
            ))}
          </ul>
        )}

        <p style={{ ...label, marginTop: "12px" }}>{t.columns.decision}</p>
        {decided ? (
          <p
            style={{
              margin: 0,
              fontSize: "12.5px",
              color: "var(--text-strong)",
            }}
          >
            {v.decision === "confirmed" && t.decided.confirmed}
            {v.decision === "corrected" &&
              fill(t.decided.corrected, {
                value: v.corrected_to ? written(v.corrected_to) : "",
              })}
            {v.decision === "rejected" &&
              fill(t.decided.rejected, {
                reason: v.rejection_reason
                  ? ((t.rejection.reasons as Record<string, string>)[
                      v.rejection_reason
                    ] ?? v.rejection_reason)
                  : "",
              })}
            {v.decided_at
              ? ` · ${fill(t.decided.at, { when: fmtWhen(v.decided_at) })}`
              : ""}
            {v.observation_id ? ` · ${t.decided.toRecord}` : ""}
          </p>
        ) : !canDecide ? (
          <p
            style={{
              margin: 0,
              fontSize: "12.5px",
              color: "var(--text-faint)",
            }}
          >
            —
          </p>
        ) : mode === "correct" ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitCorrection(e.currentTarget);
            }}
            style={{ display: "grid", gap: "8px" }}
          >
            <p
              style={{
                margin: 0,
                fontSize: "12.5px",
                fontWeight: 600,
                color: "var(--text-strong)",
              }}
            >
              {t.correction.title}
            </p>
            <label style={{ fontSize: "12px" }}>
              {t.correction.analyte}
              <input
                name="analyte"
                defaultValue={v.analyte_text}
                style={input}
                required
                maxLength={200}
              />
            </label>
            <label style={{ fontSize: "12px" }}>
              {t.correction.value}
              <input
                name="value"
                defaultValue={v.value_text}
                style={input}
                required
                maxLength={120}
              />
            </label>
            <label style={{ fontSize: "12px" }}>
              {t.correction.unit}
              <input
                name="unit"
                defaultValue={v.unit_text ?? ""}
                style={input}
                maxLength={60}
              />
            </label>
            <label style={{ fontSize: "12px" }}>
              {t.correction.date}
              <input
                name="date"
                type="date"
                defaultValue={v.observed_at ? v.observed_at.slice(0, 10) : ""}
                style={input}
              />
            </label>
            <p style={{ ...muted, margin: 0 }}>{t.correction.note}</p>
            <div style={{ display: "flex", gap: "8px" }}>
              <button type="submit" style={btnPri} disabled={pending}>
                {t.actions.saveCorrection}
              </button>
              <button
                type="button"
                style={btn}
                onClick={() => setMode("idle")}
                disabled={pending}
              >
                {t.actions.cancel}
              </button>
            </div>
          </form>
        ) : mode === "reject" ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const reason = new FormData(e.currentTarget).get("reason");
              if (typeof reason !== "string" || !reason) return;
              decide({
                pending_value_id: v.pending_value_id,
                decision: "rejected",
                rejection_reason:
                  reason as IntakePendingValue["rejection_reason"] & string,
              });
            }}
            style={{ display: "grid", gap: "8px" }}
          >
            <label style={{ fontSize: "12px" }}>
              {t.rejection.title}
              <select name="reason" style={input} required defaultValue="">
                <option value="" disabled>
                  —
                </option>
                {Object.entries(t.rejection.reasons).map(([code, text]) => (
                  <option key={code} value={code}>
                    {text}
                  </option>
                ))}
              </select>
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              <button type="submit" style={btnPri} disabled={pending}>
                {t.actions.saveRejection}
              </button>
              <button
                type="button"
                style={btn}
                onClick={() => setMode("idle")}
                disabled={pending}
              >
                {t.actions.cancel}
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: "grid", gap: "8px" }}>
            {v.status === "yellow" && (
              <label
                style={{
                  fontSize: "12.5px",
                  display: "flex",
                  gap: "6px",
                  alignItems: "center",
                }}
              >
                <input
                  type="checkbox"
                  checked={viewed}
                  onChange={(e) => setViewed(e.currentTarget.checked)}
                />
                {t.actions.viewed}
              </label>
            )}
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {v.status !== "red" && (
                <button
                  type="button"
                  style={btnPri}
                  disabled={pending || (v.status === "yellow" && !viewed)}
                  onClick={() =>
                    decide({
                      pending_value_id: v.pending_value_id,
                      decision: "confirmed",
                    })
                  }
                >
                  {t.actions.confirm}
                </button>
              )}
              <button
                type="button"
                style={btn}
                disabled={pending}
                onClick={() => setMode("correct")}
              >
                {t.actions.correct}
              </button>
              <button
                type="button"
                style={btn}
                disabled={pending}
                onClick={() => setMode("reject")}
              >
                {t.actions.reject}
              </button>
            </div>
          </div>
        )}
        {error && (
          <p role="alert" style={{ ...muted, color: "var(--text-strong)" }}>
            {error}
          </p>
        )}
      </div>
    </article>
  );
}
