"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties, type FormEvent } from "react";

import type { AuditEvent, AuditPage } from "@/lib/api";
import { AUDIT_CATEGORIES, actionLabel, targetLabel } from "@/lib/auditCopy";

// The audit trail as a table: when, who, what, on which record, with which details. Filters
// and the paging position are URL parameters (the server reads them), so the table itself
// holds no data of its own. Times are shown in the reader's own time zone once the page runs
// in the browser; until then in UTC, said so.

export interface AuditQuery {
  category?: string;
  target?: string;
  since?: string;
  until?: string;
  reads: boolean;
}

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
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

const mono: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "11px",
  color: "var(--text-faint)",
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

function href(query: AuditQuery, extra?: { cursor?: string }): string {
  const qs = new URLSearchParams();
  if (query.category) qs.set("category", query.category);
  if (query.target) qs.set("target", query.target);
  if (query.since) qs.set("since", query.since);
  if (query.until) qs.set("until", query.until);
  if (query.reads) qs.set("reads", "1");
  if (extra?.cursor) qs.set("cursor", extra.cursor);
  const text = qs.toString();
  return text ? `/einstellungen/audit?${text}` : "/einstellungen/audit";
}

// A calendar day in the reader's zone -> the instant it begins.
function dayStart(day: string, addDays = 0): string | undefined {
  const [y, m, d] = day.split("-").map(Number);
  if (!y || !m || !d) return undefined;
  const at = new Date(y, m - 1, d + addDays);
  return Number.isNaN(at.getTime()) ? undefined : at.toISOString();
}

// An instant -> the calendar day it falls on in the reader's zone (YYYY-MM-DD).
function localDay(iso: string | undefined, shiftMs = 0): string {
  if (!iso) return "";
  const at = new Date(new Date(iso).getTime() + shiftMs);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

function detailText(value: unknown): string {
  if (value === null) return "–";
  if (typeof value === "boolean") return value ? "ja" : "nein";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  return JSON.stringify(value);
}

function When({ iso, local }: { iso: string; local: boolean }) {
  const at = new Date(iso);
  const text = local
    ? `${at.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })}, ${at.toLocaleTimeString("de-DE")}`
    : `${iso.slice(0, 10)} ${iso.slice(11, 19)} UTC`;
  return (
    <time dateTime={iso} style={{ whiteSpace: "nowrap" }}>
      {text}
    </time>
  );
}

function Row({
  event,
  query,
  local,
}: {
  event: AuditEvent;
  query: AuditQuery;
  local: boolean;
}) {
  const details = Object.entries(event.detail);
  return (
    <tr>
      <td style={{ ...tdStyle, paddingLeft: "22px" }}>
        <When iso={event.occurred_at} local={local} />
      </td>
      <td style={tdStyle}>
        {event.actor ? (
          <>
            <div style={{ color: "var(--text-strong)", fontWeight: 600 }}>
              {event.actor.display_name}
            </div>
            <div style={mono}>{event.actor.email}</div>
          </>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>
            ohne angemeldete Person
          </span>
        )}
      </td>
      <td style={tdStyle}>
        <div style={{ color: "var(--text-strong)" }}>
          {actionLabel(event.action)}
        </div>
        <div style={mono}>{event.action}</div>
      </td>
      <td style={tdStyle}>
        {event.target_id ? (
          <>
            <div>{targetLabel(event.target_type)}</div>
            <div style={mono}>
              <Link
                href={href({ ...query, target: event.target_id })}
                title="Nur Einträge zu diesem Datensatz anzeigen"
              >
                {shortId(event.target_id)}
              </Link>
              {event.target_type === "patient" && (
                <>
                  {" · "}
                  <Link href={`/patients/${event.target_id}`}>Akte öffnen</Link>
                </>
              )}
            </div>
          </>
        ) : (
          "—"
        )}
      </td>
      <td style={{ ...tdStyle, paddingRight: "22px", ...mono }}>
        {details.length === 0
          ? "—"
          : details.map(([key, value]) => (
              <div key={key} style={{ overflowWrap: "anywhere" }}>
                {key}: {detailText(value)}
              </div>
            ))}
      </td>
    </tr>
  );
}

export function AuditContent({
  page,
  query,
  continued,
  stalePosition,
}: {
  page: AuditPage;
  query: AuditQuery;
  continued: boolean;
  stalePosition: boolean;
}) {
  const router = useRouter();
  // The reader's time zone is known only in the browser.
  const [local, setLocal] = useState(false);
  useEffect(() => setLocal(true), []);

  const apply = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const from = String(form.get("from") ?? "");
    const to = String(form.get("to") ?? "");
    router.push(
      href({
        category: String(form.get("category") ?? "") || undefined,
        target: query.target,
        since: from ? dayStart(from) : undefined,
        // "bis" is the last day shown: the window ends when the next day begins.
        until: to ? dayStart(to, 1) : undefined,
        reads: form.get("reads") === "on",
      }),
    );
  };

  const filtered = Boolean(
    query.category || query.target || query.since || query.until || query.reads,
  );

  return (
    <div style={{ maxWidth: "1180px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>Audit-Protokoll</h1>
      <p
        style={{
          color: "var(--text-muted)",
          fontSize: "13px",
          lineHeight: 1.55,
          margin: "0 0 18px",
          maxWidth: "92ch",
        }}
      >
        Was in dieser Praxis geschehen ist: wer, wann, welcher Vorgang, an
        welchem Datensatz. Das Protokoll enthält Kennungen, Codes und Zeitpunkte
        — keine Messwerte und keine Namen von Patientinnen und Patienten.
        Einträge werden nur angefügt, nie geändert oder gelöscht. Anmeldungen
        werden erfasst, bevor eine Praxis ausgewählt ist, und erscheinen deshalb
        hier nicht; der Eintritt in die Praxis schon.
      </p>

      <form
        // The URL is the state: a new filter set re-mounts the form with its values.
        key={href(query) + String(local)}
        onSubmit={apply}
        style={{
          ...cardStyle,
          padding: "16px 22px",
          marginBottom: "16px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-end",
          gap: "14px",
        }}
      >
        <label style={labelStyle}>
          Bereich
          <select
            name="category"
            defaultValue={query.category ?? ""}
            style={fieldStyle}
          >
            <option value="">Alle Bereiche</option>
            {AUDIT_CATEGORIES.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label style={labelStyle}>
          Von
          <input
            type="date"
            name="from"
            defaultValue={local ? localDay(query.since) : ""}
            style={fieldStyle}
          />
        </label>
        <label style={labelStyle}>
          Bis einschließlich
          <input
            type="date"
            name="to"
            // The window ends at the start of the next day; show the day before that.
            defaultValue={local ? localDay(query.until, -1) : ""}
            style={fieldStyle}
          />
        </label>
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            height: "36px",
            fontSize: "12.5px",
            color: "var(--text-body)",
          }}
        >
          <input type="checkbox" name="reads" defaultChecked={query.reads} />
          Lesezugriffe anzeigen
        </label>
        <button
          type="submit"
          style={{
            ...fieldStyle,
            padding: "0 14px",
            border: "1px solid var(--brand)",
            background: "var(--brand)",
            color: "var(--text-on-brand)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Anwenden
        </button>
        {filtered && (
          <Link
            href="/einstellungen/audit"
            style={{ fontSize: "12.5px", lineHeight: "36px" }}
          >
            Filter zurücksetzen
          </Link>
        )}
      </form>

      {query.target && (
        <p style={{ fontSize: "12.5px", margin: "0 0 12px" }}>
          Nur Einträge zum Datensatz <span style={mono}>{query.target}</span>.{" "}
          <Link href={href({ ...query, target: undefined })}>
            Alle Datensätze anzeigen
          </Link>
        </p>
      )}
      {stalePosition && (
        <p role="status" style={{ fontSize: "12.5px", margin: "0 0 12px" }}>
          Die aufgerufene Position ist nicht gültig. Angezeigt werden die
          neuesten Einträge.
        </p>
      )}

      <section
        style={{ ...cardStyle, overflow: "hidden" }}
        aria-labelledby="audit-heading"
      >
        <h2 id="audit-heading" className="sr-only">
          Einträge
        </h2>
        {page.items.length === 0 ? (
          <p
            style={{
              margin: 0,
              padding: "22px",
              fontSize: "12.5px",
              color: "var(--text-muted)",
            }}
          >
            {filtered || continued
              ? "Zu dieser Auswahl gibt es keine Einträge."
              : "Noch keine Einträge."}
          </p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{ width: "100%", borderCollapse: "collapse" }}
              aria-label="Audit-Protokoll, neueste Einträge zuerst"
            >
              <thead>
                <tr>
                  <th style={{ ...thStyle, paddingLeft: "22px" }}>Zeit</th>
                  <th style={thStyle}>Wer</th>
                  <th style={thStyle}>Vorgang</th>
                  <th style={thStyle}>Datensatz</th>
                  <th style={{ ...thStyle, paddingRight: "22px" }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((event) => (
                  <Row
                    key={event.id}
                    event={event}
                    query={query}
                    local={local}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p
        style={{
          margin: "14px 0 0",
          display: "flex",
          gap: "18px",
          fontSize: "12.5px",
        }}
      >
        {page.next_cursor && (
          <Link href={href(query, { cursor: page.next_cursor })}>
            Ältere Einträge
          </Link>
        )}
        {continued && <Link href={href(query)}>Zu den neuesten Einträgen</Link>}
      </p>
    </div>
  );
}
