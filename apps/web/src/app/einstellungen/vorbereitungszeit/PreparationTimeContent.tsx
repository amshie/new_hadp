import type { CSSProperties } from "react";

import type {
  PreparationMeasured,
  PreparationStatement,
  PreparationTime,
} from "@/lib/api";
import { CLINIC_TIME_ZONE, clinicTime } from "@/lib/clinicTime";
import { byCount, fill } from "@/lib/i18n/fill";
import type { Messages } from "@/lib/i18n/messages";

import { recordStatementAction } from "./actions";

// The preparation-time metric as the owner reads it. Two quantities, in two sections that do
// not borrow from each other: what the clinic STATES (minutes of preparation per appointment,
// as a median) and what the platform MEASURES (elapsed time from a report's first draft to its
// first approval that stood). The second is not minutes of work, and the page never subtracts
// one from the other — and it says that a measure which could be set against the stated
// minutes does not exist yet. Covered by the web copy scan
// (apps/api/tests/test_web_copy_language.py).
//
// The page follows the interface language (lib/i18n): its wording comes in from the route.
// Names are shown as recorded; times and figures keep their form.

export type Outcome = {
  saved?: boolean;
  failure?:
    | "eingabe"
    | "minuten"
    | "stichprobe"
    | "schaetzung"
    | "rolle"
    | "zuviele"
    | "allgemein";
};

type T = Messages["preparationPage"];

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
  padding: "18px 22px",
};

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "10px 14px",
  fontFamily: "var(--font-mono)",
  fontSize: "9.5px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
  borderBottom: "1px solid var(--border-subtle)",
  whiteSpace: "nowrap",
};

const tdStyle: CSSProperties = {
  padding: "10px 14px",
  fontSize: "12.5px",
  color: "var(--text-body)",
  borderBottom: "1px solid var(--border-subtle)",
  verticalAlign: "top",
};

const fieldStyle: CSSProperties = {
  height: "36px",
  padding: "0 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-strong)",
  fontFamily: "var(--font-text)",
  fontSize: "12.5px",
};

const labelStyle: CSSProperties = {
  display: "grid",
  gap: "5px",
  fontSize: "11.5px",
  color: "var(--text-muted)",
};

const h2Style: CSSProperties = { fontSize: "16px", margin: "0 0 4px" };

const leadStyle: CSSProperties = {
  color: "var(--text-muted)",
  fontSize: "12.5px",
  lineHeight: 1.55,
  margin: "0 0 14px",
  maxWidth: "88ch",
};

const figureStyle: CSSProperties = {
  fontSize: "22px",
  fontWeight: 600,
  color: "var(--text-strong)",
};

// An elapsed time in the two largest units that say something: "unter 1 Min.", "12 Min.",
// "2 Std. 5 Min.", "3 Tage 4 Std." (in German). Nothing finer than a minute is shown.
export function elapsed(seconds: number, t: T["elapsed"]): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return t.underOne;
  if (minutes < 60) return fill(t.minutes, { m: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest
      ? fill(t.hoursMinutes, { h: hours, m: rest })
      : fill(t.hours, { h: hours });
  }
  const days = Math.floor(hours / 24);
  const rest = hours % 24;
  return rest
    ? fill(byCount(t.daysHours, days), { h: rest })
    : byCount(t.days, days);
}

function basisText(statement: PreparationStatement, t: T): string {
  if (statement.basis !== "timed_sample") return t.basis.estimate;
  return byCount(t.timedOver, statement.sample_size ?? 0);
}

function Stated({
  title,
  statement,
  empty,
  t,
}: {
  title: string;
  statement: PreparationStatement | null;
  empty: string;
  t: T;
}) {
  return (
    <div style={{ ...cardStyle, flex: "1 1 260px" }}>
      <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
        {title}
      </div>
      {statement ? (
        <>
          <div style={figureStyle}>
            {fill(t.minutes, { n: statement.median_minutes })}
          </div>
          <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
            {fill(t.stated.perAppointment, { basis: basisText(statement, t) })}
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
            {t.stated.recordedAt}{" "}
            <time dateTime={statement.recorded_at}>
              {clinicTime(statement.recorded_at)}
            </time>
            {statement.recorded_by
              ? fill(t.stated.recordedBy, {
                  name: statement.recorded_by.display_name,
                })
              : ""}
          </div>
        </>
      ) : (
        <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
          {empty}
        </div>
      )}
    </div>
  );
}

function Measured({
  title,
  measured,
  minimum,
  t,
}: {
  title: string;
  measured: PreparationMeasured;
  minimum: number;
  t: T;
}) {
  const shown =
    measured.median_seconds !== null &&
    measured.q1_seconds !== null &&
    measured.q3_seconds !== null;
  return (
    <div style={{ ...cardStyle, flex: "1 1 260px" }}>
      <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
        {title}
      </div>
      {shown ? (
        <>
          <div style={figureStyle}>
            {elapsed(measured.median_seconds!, t.elapsed)}
          </div>
          <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
            {fill(t.measured.median, { n: measured.reports })}
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
            {fill(t.measured.middleHalf, {
              q1: elapsed(measured.q1_seconds!, t.elapsed),
              q3: elapsed(measured.q3_seconds!, t.elapsed),
            })}
          </div>
        </>
      ) : (
        <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
          {measured.reports === 0
            ? t.measured.none
            : fill(t.measured.tooFew, { n: measured.reports, minimum })}
        </div>
      )}
    </div>
  );
}

export function PreparationTimeContent({
  metric,
  outcome,
  t,
  title,
}: {
  metric: PreparationTime;
  outcome: Outcome;
  t: T;
  title: string;
}) {
  const { baseline, latest_follow_up: followUp } = metric;
  const difference =
    baseline && followUp
      ? followUp.median_minutes - baseline.median_minutes
      : null;

  return (
    <div style={{ maxWidth: "1040px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>{title}</h1>
      <p style={{ ...leadStyle, fontSize: "13px" }}>
        {fill(t.lead, { zone: CLINIC_TIME_ZONE })}
      </p>

      {outcome.saved && (
        <p
          role="status"
          style={{ ...leadStyle, color: "var(--text-strong)", fontWeight: 600 }}
        >
          {t.saved}
        </p>
      )}
      {outcome.failure && (
        <p
          role="alert"
          style={{ ...leadStyle, color: "var(--text-strong)", fontWeight: 600 }}
        >
          {t.failures[outcome.failure]}
        </p>
      )}

      <section aria-labelledby="angaben" style={{ marginBottom: "26px" }}>
        <h2 id="angaben" style={h2Style}>
          {t.stated.title}
        </h2>
        <p style={leadStyle}>{t.stated.note}</p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "14px",
            marginBottom: "12px",
          }}
        >
          <Stated
            title={t.kind.baseline}
            statement={baseline}
            empty={t.stated.noBaseline}
            t={t}
          />
          <Stated
            title={t.stated.latestFollowUp}
            statement={followUp}
            empty={t.stated.noFollowUp}
            t={t}
          />
        </div>
        {difference !== null && (
          <p style={{ ...leadStyle, color: "var(--text-body)" }}>
            {difference === 0
              ? t.stated.same
              : fill(difference < 0 ? t.stated.below : t.stated.above, {
                  n: Math.abs(difference),
                })}{" "}
            {t.stated.bothStated}
            {baseline && followUp && baseline.basis !== followUp.basis
              ? fill(t.stated.differentBasis, {
                  first: t.basis[baseline.basis],
                  second: t.basis[followUp.basis],
                })
              : "."}
          </p>
        )}

        <form
          action={recordStatementAction}
          style={{
            ...cardStyle,
            display: "flex",
            flexWrap: "wrap",
            alignItems: "end",
            gap: "14px",
          }}
        >
          <label style={labelStyle}>
            {t.form.kind}
            <select name="kind" defaultValue="baseline" style={fieldStyle}>
              <option value="baseline">{t.kind.baseline}</option>
              <option value="follow_up">{t.kind.follow_up}</option>
            </select>
          </label>
          <label style={labelStyle}>
            {t.form.median}
            <input
              name="median_minutes"
              type="number"
              inputMode="numeric"
              min={1}
              max={600}
              step={1}
              required
              style={{ ...fieldStyle, width: "150px" }}
            />
          </label>
          <label style={labelStyle}>
            {t.form.basis}
            <select name="basis" defaultValue="estimate" style={fieldStyle}>
              <option value="estimate">{t.basis.estimate}</option>
              <option value="timed_sample">{t.basis.timed_sample}</option>
            </select>
          </label>
          <label style={labelStyle}>
            {t.form.sample}
            <input
              name="sample_size"
              type="number"
              inputMode="numeric"
              min={1}
              max={100000}
              step={1}
              style={{ ...fieldStyle, width: "150px" }}
            />
          </label>
          <button
            type="submit"
            style={{
              ...fieldStyle,
              cursor: "pointer",
              fontWeight: 600,
              padding: "0 16px",
            }}
          >
            {t.form.save}
          </button>
          <p
            style={{
              flexBasis: "100%",
              margin: 0,
              fontSize: "11.5px",
              color: "var(--text-muted)",
            }}
          >
            {t.form.note}
          </p>
        </form>

        {metric.statements_total > metric.statements.length && (
          <p style={{ ...leadStyle, margin: "14px 0 0" }}>
            {fill(t.history.shown, {
              shown: metric.statements.length,
              total: metric.statements_total,
            })}
          </p>
        )}
        {metric.statements.length > 0 && (
          <div style={{ ...cardStyle, padding: 0, marginTop: "14px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <caption className="sr-only">{t.history.caption}</caption>
              <thead>
                <tr>
                  <th scope="col" style={{ ...thStyle, paddingLeft: "22px" }}>
                    {t.history.columns.recordedAt}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.history.columns.kind}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.history.columns.median}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.history.columns.basis}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.history.columns.recordedBy}
                  </th>
                </tr>
              </thead>
              <tbody>
                {metric.statements.map((s) => (
                  <tr key={s.id}>
                    <td style={{ ...tdStyle, paddingLeft: "22px" }}>
                      <time
                        dateTime={s.recorded_at}
                        style={{ whiteSpace: "nowrap" }}
                      >
                        {clinicTime(s.recorded_at)}
                      </time>
                    </td>
                    <td style={tdStyle}>{t.kind[s.kind]}</td>
                    <td style={tdStyle}>
                      {fill(t.minutes, { n: s.median_minutes })}
                    </td>
                    <td style={tdStyle}>{basisText(s, t)}</td>
                    <td style={tdStyle}>
                      {s.recorded_by?.display_name ?? "–"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="gemessen" style={{ marginBottom: "26px" }}>
        <h2 id="gemessen" style={h2Style}>
          {t.measured.title}
        </h2>
        <p style={leadStyle}>{t.measured.note}</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "14px" }}>
          <Measured
            title={t.measured.last30}
            measured={metric.measured_last_30_days}
            minimum={metric.minimum_reports}
            t={t}
          />
          <Measured
            title={t.measured.allTime}
            measured={metric.measured_all_time}
            minimum={metric.minimum_reports}
            t={t}
          />
        </div>
      </section>

      <section aria-labelledby="grenzen">
        <h2 id="grenzen" style={h2Style}>
          {t.limits.title}
        </h2>
        <ul
          style={{
            ...leadStyle,
            margin: "8px 0 0",
            paddingLeft: "18px",
          }}
        >
          <li>{t.limits.waiting}</li>
          <li>{t.limits.notOffset}</li>
          <li>{t.limits.countsOnce}</li>
          <li>{fill(t.limits.minimum, { minimum: metric.minimum_reports })}</li>
          <li>{t.limits.computed}</li>
          <li>{fill(t.limits.audited, { definition: metric.definition })}</li>
        </ul>
      </section>
    </div>
  );
}
