import Link from "next/link";
import type { CSSProperties } from "react";

import type { AuditCategory, AuditEvent, AuditPage } from "@/lib/api";
import { actionLabel, auditCategories, targetLabel } from "@/lib/auditCopy";
import { CLINIC_TIME_ZONE, clinicTime } from "@/lib/clinicTime";
import { fill } from "@/lib/i18n/fill";
import type { Locale } from "@/lib/i18n/locales";
import type { Messages } from "@/lib/i18n/messages";

// The audit trail as a table: when, who, what, on which record, with which details. Rendered
// on the server — a production build sends only what is shown. Filters and the paging
// position are URL parameters the page has already validated; the filter is a plain GET form.
// Times are on the clinic's wall clock, and say so.
//
// The page follows the interface language (lib/i18n): its wording comes in from the route,
// the labels of events from lib/auditCopy.ts. Codes, identifiers, details, names and e-mail
// addresses are shown as recorded; times keep their form.
//
// The links of the table and of the paging are not prefetched (the shell's navigation links
// are, as on every page). A row carries up to two links and a page fifty rows; a prefetch asks
// the server for a page nobody chose to open. (Measured on the production build, Next 15.5:
// such a request is answered with the shell only and records no read. Not prefetching keeps
// the table from depending on that.)

export interface AuditQuery {
  category?: AuditCategory;
  target?: string;
  // Calendar days (YYYY-MM-DD) on the clinic's wall clock; `to` is the last day shown.
  from?: string;
  to?: string;
  hideReads: boolean;
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

const noteStyle: CSSProperties = { fontSize: "12.5px", margin: "0 0 12px" };

const PATH = "/einstellungen/audit";

function href(query: AuditQuery, extra?: { cursor?: string }): string {
  const qs = new URLSearchParams();
  if (query.category) qs.set("category", query.category);
  if (query.target) qs.set("target", query.target);
  if (query.from) qs.set("from", query.from);
  if (query.to) qs.set("to", query.to);
  if (query.hideReads) qs.set("reads", "0");
  if (extra?.cursor) qs.set("cursor", extra.cursor);
  const text = qs.toString();
  return text ? `${PATH}?${text}` : PATH;
}

type T = Messages["auditPage"];

function detailText(value: unknown, t: T): string {
  if (value === null) return "–";
  if (typeof value === "boolean") return value ? t.yes : t.no;
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  return JSON.stringify(value);
}

function Row({
  event,
  query,
  t,
  locale,
}: {
  event: AuditEvent;
  query: AuditQuery;
  t: T;
  locale: Locale;
}) {
  const details = Object.entries(event.detail);
  return (
    <tr>
      <td style={{ ...tdStyle, paddingLeft: "22px" }}>
        <time dateTime={event.occurred_at} style={{ whiteSpace: "nowrap" }}>
          {clinicTime(event.occurred_at)}
        </time>
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
          <span style={{ color: "var(--text-muted)" }}>{t.noActor}</span>
        )}
      </td>
      <td style={tdStyle}>
        <div style={{ color: "var(--text-strong)" }}>
          {actionLabel(event.action, locale)}
        </div>
        <div style={mono}>{event.action}</div>
      </td>
      <td style={tdStyle}>
        {event.target_id ? (
          <>
            <div>{targetLabel(event.target_type, locale)}</div>
            <div style={mono}>
              <Link
                href={href({ ...query, target: event.target_id })}
                prefetch={false}
                title={t.onlyThisTarget}
              >
                {event.target_id.slice(0, 8)}
              </Link>
              {event.target_type === "patient" && (
                <>
                  {" · "}
                  <Link href={`/patients/${event.target_id}`} prefetch={false}>
                    {t.openRecord}
                  </Link>
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
                {key}: {detailText(value, t)}
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
  t,
  title,
  locale,
}: {
  page: AuditPage;
  query: AuditQuery;
  continued: boolean;
  stalePosition: boolean;
  t: T;
  title: string;
  locale: Locale;
}) {
  const notShown = t.notShown;
  const filtered = Boolean(
    query.category || query.target || query.from || query.to || query.hideReads,
  );

  return (
    <div style={{ maxWidth: "1180px" }}>
      <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>{title}</h1>
      <p
        style={{
          color: "var(--text-muted)",
          fontSize: "13px",
          lineHeight: 1.55,
          margin: "0 0 10px",
          maxWidth: "92ch",
        }}
      >
        {fill(t.lead, { zone: CLINIC_TIME_ZONE })}
      </p>
      <details
        style={{
          color: "var(--text-muted)",
          fontSize: "12.5px",
          lineHeight: 1.55,
          margin: "0 0 18px",
          maxWidth: "92ch",
        }}
      >
        <summary style={{ cursor: "pointer", color: "var(--text-body)" }}>
          {notShown.title}
        </summary>
        <ul style={{ margin: "8px 0 0", paddingLeft: "18px" }}>
          <li>{notShown.tenantless}</li>
          <li>{notShown.notRecorded}</li>
          <li>{notShown.refusals}</li>
          <li>{notShown.linkRefusals}</li>
          <li>{notShown.byRecord}</li>
          <li>{notShown.lists}</li>
          <li>{notShown.erased}</li>
          <li>{notShown.sameTime}</li>
          <li>{notShown.paging}</li>
        </ul>
      </details>

      <form
        // The URL is the state: another selection re-mounts the form with its values.
        key={href(query)}
        method="get"
        action={PATH}
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
          {t.filter.category}
          <select
            name="category"
            defaultValue={query.category ?? ""}
            style={fieldStyle}
          >
            <option value="">{t.filter.allCategories}</option>
            {auditCategories(locale).map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label style={labelStyle}>
          {t.filter.from}
          <input
            type="date"
            name="from"
            defaultValue={query.from ?? ""}
            style={fieldStyle}
          />
        </label>
        <label style={labelStyle}>
          {t.filter.to}
          <input
            type="date"
            name="to"
            defaultValue={query.to ?? ""}
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
          <input
            type="checkbox"
            name="reads"
            value="0"
            defaultChecked={query.hideReads}
          />
          {t.filter.hideReads}
        </label>
        {query.target && (
          <input type="hidden" name="target" value={query.target} />
        )}
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
          {t.filter.apply}
        </button>
        {filtered && (
          <a href={PATH} style={{ fontSize: "12.5px", lineHeight: "36px" }}>
            {t.filter.reset}
          </a>
        )}
      </form>

      {query.target && (
        <p style={noteStyle}>
          {t.targetBefore} <span style={mono}>{query.target}</span>
          {t.targetAfter}{" "}
          <Link href={href({ ...query, target: undefined })} prefetch={false}>
            {t.allTargets}
          </Link>
        </p>
      )}
      {query.hideReads && (
        <p style={noteStyle}>
          {t.readsHidden}{" "}
          <Link href={href({ ...query, hideReads: false })} prefetch={false}>
            {t.showReads}
          </Link>
        </p>
      )}
      {stalePosition && (
        <p role="status" style={noteStyle}>
          {t.stalePosition}
        </p>
      )}

      <section
        style={{ ...cardStyle, overflow: "hidden" }}
        aria-labelledby="audit-heading"
      >
        <h2 id="audit-heading" className="sr-only">
          {t.entries}
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
            {filtered || continued ? t.emptyFiltered : t.empty}
          </p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{ width: "100%", borderCollapse: "collapse" }}
              aria-label={t.tableAria}
            >
              <thead>
                <tr>
                  <th scope="col" style={{ ...thStyle, paddingLeft: "22px" }}>
                    {t.columns.time}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.columns.who}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.columns.action}
                  </th>
                  <th scope="col" style={thStyle}>
                    {t.columns.target}
                  </th>
                  <th scope="col" style={{ ...thStyle, paddingRight: "22px" }}>
                    {t.columns.details}
                  </th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((event) => (
                  <Row
                    key={event.id}
                    event={event}
                    query={query}
                    t={t}
                    locale={locale}
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
          <Link
            href={href(query, { cursor: page.next_cursor })}
            prefetch={false}
          >
            {t.older}
          </Link>
        )}
        {continued && (
          <Link href={href(query)} prefetch={false}>
            {t.newest}
          </Link>
        )}
      </p>
    </div>
  );
}
