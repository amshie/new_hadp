import type { CSSProperties } from "react";

import type {
  PreparationMeasured,
  PreparationStatement,
  PreparationTime,
} from "@/lib/api";
import { CLINIC_TIME_ZONE, clinicTime } from "@/lib/clinicTime";

import { recordStatementAction } from "./actions";

// The preparation-time metric as the owner reads it. Two quantities, in two sections that do
// not borrow from each other: what the clinic STATES (minutes of preparation per appointment,
// as a median) and what the platform MEASURES (elapsed time from a report's first draft to its
// first approval). The second is not minutes of work, and the page never subtracts one from
// the other. Covered by the web copy scan (apps/api/tests/test_web_copy_language.py).

export type Outcome = {
  saved?: boolean;
  failure?:
    | "eingabe"
    | "minuten"
    | "stichprobe"
    | "schaetzung"
    | "rolle"
    | "allgemein";
};

const FAILURE_TEXT: Record<NonNullable<Outcome["failure"]>, string> = {
  eingabe: "Die Angabe wurde nicht gespeichert: Die Eingabe war unvollständig.",
  minuten:
    "Die Angabe wurde nicht gespeichert: Der Median ist eine ganze Zahl von 1 bis 600 Minuten.",
  stichprobe:
    "Die Angabe wurde nicht gespeichert: Zu einer Zeitmessung gehört die Anzahl der gemessenen Termine (1 bis 100000).",
  schaetzung:
    "Die Angabe wurde nicht gespeichert: Eine Schätzung hat keine Anzahl gemessener Termine. Bitte das Feld leer lassen oder „Zeitmessung“ wählen.",
  rolle: "Die Angabe wurde nicht gespeichert: Das ist nur Inhabern erlaubt.",
  allgemein:
    "Die Angabe wurde nicht gespeichert. Bitte später erneut versuchen.",
};

const KIND_LABEL: Record<PreparationStatement["kind"], string> = {
  baseline: "Ausgangswert",
  follow_up: "Folgeangabe",
};

const BASIS_LABEL: Record<PreparationStatement["basis"], string> = {
  estimate: "Schätzung",
  timed_sample: "Zeitmessung",
};

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
// "2 Std. 5 Min.", "3 Tage 4 Std.". Nothing finer than a minute is shown.
export function elapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return "unter 1 Min.";
  if (minutes < 60) return `${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest ? `${hours} Std. ${rest} Min.` : `${hours} Std.`;
  }
  const days = Math.floor(hours / 24);
  const rest = hours % 24;
  const unit = days === 1 ? "Tag" : "Tage";
  return rest ? `${days} ${unit} ${rest} Std.` : `${days} ${unit}`;
}

function basisText(statement: PreparationStatement): string {
  return statement.basis === "timed_sample"
    ? `Zeitmessung über ${statement.sample_size} Termine`
    : "Schätzung";
}

function Stated({
  title,
  statement,
  empty,
}: {
  title: string;
  statement: PreparationStatement | null;
  empty: string;
}) {
  return (
    <div style={{ ...cardStyle, flex: "1 1 260px" }}>
      <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
        {title}
      </div>
      {statement ? (
        <>
          <div style={figureStyle}>{statement.median_minutes} Min.</div>
          <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
            Median je Termin · {basisText(statement)}
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
            erfasst am{" "}
            <time dateTime={statement.recorded_at}>
              {clinicTime(statement.recorded_at)}
            </time>
            {statement.recorded_by
              ? ` von ${statement.recorded_by.display_name}`
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
}: {
  title: string;
  measured: PreparationMeasured;
  minimum: number;
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
          <div style={figureStyle}>{elapsed(measured.median_seconds!)}</div>
          <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
            Median vom ersten Entwurf bis zur ersten Genehmigung ·{" "}
            {measured.reports} Berichte
          </div>
          <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
            Mittlere Hälfte der Berichte: {elapsed(measured.q1_seconds!)} bis{" "}
            {elapsed(measured.q3_seconds!)}
          </div>
        </>
      ) : (
        <div style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
          {measured.reports === 0
            ? "Noch kein genehmigter Bericht in diesem Zeitraum."
            : `Genehmigte Berichte in diesem Zeitraum: ${measured.reports}. Ein Median wird ab ${minimum} Berichten angegeben.`}
        </div>
      )}
    </div>
  );
}

export function PreparationTimeContent({
  metric,
  outcome,
}: {
  metric: PreparationTime;
  outcome: Outcome;
}) {
  const { baseline, latest_follow_up: followUp } = metric;
  const difference =
    baseline && followUp
      ? followUp.median_minutes - baseline.median_minutes
      : null;

  return (
    <div style={{ maxWidth: "1040px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>
        Vorbereitungszeit
      </h1>
      <p style={{ ...leadStyle, fontSize: "13px" }}>
        Wie lange die Vorbereitung eines Termins dauert. Diese Seite hält zwei
        Dinge auseinander: was die Praxis selbst angibt, und was die Plattform
        aus dem Ablauf der Berichte misst. Sie enthält keine Daten von
        Patientinnen und Patienten. Zeiten in der Zeitzone {CLINIC_TIME_ZONE}.
      </p>

      {outcome.saved && (
        <p
          role="status"
          style={{ ...leadStyle, color: "var(--text-strong)", fontWeight: 600 }}
        >
          Die Angabe wurde gespeichert.
        </p>
      )}
      {outcome.failure && (
        <p
          role="alert"
          style={{ ...leadStyle, color: "var(--text-strong)", fontWeight: 600 }}
        >
          {FAILURE_TEXT[outcome.failure]}
        </p>
      )}

      <section aria-labelledby="angaben" style={{ marginBottom: "26px" }}>
        <h2 id="angaben" style={h2Style}>
          Angaben der Praxis
        </h2>
        <p style={leadStyle}>
          Der Median der Vorbereitungszeit je Termin, in Minuten, wie die Praxis
          ihn angibt: der Ausgangswert vor dem Einsatz der Plattform und spätere
          Folgeangaben. Die Plattform übernimmt diese Zahlen und prüft sie
          nicht.
        </p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "14px",
            marginBottom: "12px",
          }}
        >
          <Stated
            title="Ausgangswert"
            statement={baseline}
            empty="Noch kein Ausgangswert erfasst."
          />
          <Stated
            title="Letzte Folgeangabe"
            statement={followUp}
            empty="Noch keine Folgeangabe erfasst."
          />
        </div>
        {difference !== null && (
          <p style={{ ...leadStyle, color: "var(--text-body)" }}>
            {difference === 0
              ? "Die letzte Folgeangabe entspricht dem Ausgangswert."
              : `Die letzte Folgeangabe liegt ${Math.abs(difference)} Min. ${
                  difference < 0 ? "unter" : "über"
                } dem Ausgangswert.`}{" "}
            Beide Zahlen sind Angaben der Praxis.
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
            Art der Angabe
            <select name="kind" defaultValue="baseline" style={fieldStyle}>
              <option value="baseline">Ausgangswert</option>
              <option value="follow_up">Folgeangabe</option>
            </select>
          </label>
          <label style={labelStyle}>
            Median je Termin (Minuten)
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
            Grundlage
            <select name="basis" defaultValue="estimate" style={fieldStyle}>
              <option value="estimate">Schätzung</option>
              <option value="timed_sample">Zeitmessung</option>
            </select>
          </label>
          <label style={labelStyle}>
            Anzahl gemessener Termine (nur bei Zeitmessung)
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
            Angabe speichern
          </button>
          <p
            style={{
              flexBasis: "100%",
              margin: 0,
              fontSize: "11.5px",
              color: "var(--text-muted)",
            }}
          >
            Eine gespeicherte Angabe wird nicht geändert oder gelöscht. Eine
            Korrektur ist eine neue Angabe; die frühere bleibt im Verlauf
            stehen.
          </p>
        </form>

        {metric.statements.length > 0 && (
          <div style={{ ...cardStyle, padding: 0, marginTop: "14px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <caption className="sr-only">
                Verlauf der Angaben der Praxis, neueste zuerst
              </caption>
              <thead>
                <tr>
                  <th scope="col" style={{ ...thStyle, paddingLeft: "22px" }}>
                    Erfasst am
                  </th>
                  <th scope="col" style={thStyle}>
                    Art
                  </th>
                  <th scope="col" style={thStyle}>
                    Median je Termin
                  </th>
                  <th scope="col" style={thStyle}>
                    Grundlage
                  </th>
                  <th scope="col" style={thStyle}>
                    Erfasst von
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
                    <td style={tdStyle}>{KIND_LABEL[s.kind]}</td>
                    <td style={tdStyle}>{s.median_minutes} Min.</td>
                    <td style={tdStyle}>
                      {s.basis === "timed_sample"
                        ? `${BASIS_LABEL[s.basis]} über ${s.sample_size} Termine`
                        : BASIS_LABEL[s.basis]}
                    </td>
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
          Gemessen aus dem Ablauf der Berichte
        </h2>
        <p style={leadStyle}>
          Die Zeit vom ersten Entwurf eines Berichts bis zu seiner ersten
          klinischen Genehmigung, aus den Zeitpunkten, die die Plattform dabei
          ohnehin festhält. Das ist Durchlaufzeit, keine Arbeitszeit.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "14px" }}>
          <Measured
            title="Letzte 30 Tage"
            measured={metric.measured_last_30_days}
            minimum={metric.minimum_reports}
          />
          <Measured
            title="Alle Berichte der Praxis"
            measured={metric.measured_all_time}
            minimum={metric.minimum_reports}
          />
        </div>
      </section>

      <section aria-labelledby="grenzen">
        <h2 id="grenzen" style={h2Style}>
          Was diese Zahlen sind – und was nicht
        </h2>
        <ul
          style={{
            ...leadStyle,
            margin: "8px 0 0",
            paddingLeft: "18px",
          }}
        >
          <li>
            Die gemessene Zeit enthält jede Wartezeit zwischen Entwurf und
            Genehmigung – auch Nächte und Wochenenden. Was vor dem Entwurf
            geschieht (Werte sichten, Review-Einträge entscheiden,
            Interpretation erfassen), ist nicht enthalten.
          </li>
          <li>
            Sie wird deshalb nicht mit den Minuten-Angaben der Praxis
            verrechnet: Es sind zwei verschiedene Größen.
          </li>
          <li>
            Ein Bericht zählt einmal, zum Zeitpunkt seiner ersten Genehmigung –
            auch wenn er später überarbeitet und erneut genehmigt wird. Berichte
            ohne Genehmigung zählen nicht.
          </li>
          <li>
            Unter {metric.minimum_reports} Berichten wird kein Median angegeben:
            Er wäre eine Aussage über einzelne Personen, nicht über den Ablauf
            der Praxis.
          </li>
          <li>
            Die Kennzahl wird aus den vorhandenen Berichten gebildet. Wird eine
            Akte gelöscht, entfallen ihre Berichte auch hier.
          </li>
          <li>
            Das Lesen dieser Seite und jede erfasste Angabe stehen im
            Audit-Protokoll. Stand der Messvorschrift: {metric.definition}.
          </li>
        </ul>
      </section>
    </div>
  );
}
