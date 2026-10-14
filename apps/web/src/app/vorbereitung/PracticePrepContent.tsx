"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/vitabahn/EmptyState";
import type { Preparation, PreparationRow } from "@/lib/api";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { dayOf } from "@/lib/presenters/domainOverview";
import {
  PREP_FILTERS,
  presentPracticePrep,
  type PrepColumn,
  type PrepFilter,
  type PrepSort,
} from "@/lib/presenters/practicePrep";
import { reportStatusLabel } from "@/lib/presenters/review";

// The practice view (docs/notes/0023): every record of the clinic with the counts the page
// before a visit shows for it. Ordered by workflow; a person may filter by a fact and sort by
// a column. A record's name leads to its own preparation page. Nothing here is a rating.
const COLUMNS: readonly PrepColumn[] = [
  "patient",
  "status",
  "run",
  "newValues",
  "outside",
  "stale",
  "missing",
  "pending",
  "noVerdict",
];
const NUMERIC = new Set<PrepColumn>([
  "newValues",
  "outside",
  "stale",
  "missing",
  "pending",
  "noVerdict",
]);

export function PracticePrepContent({
  data,
  tenantName,
}: {
  data: Preparation;
  tenantName: string;
}) {
  const { t: messages } = useI18n();
  const t = messages.practicePrep;
  const statusWords = messages.patientPage.reportStatus;
  const [filter, setFilter] = useState<PrepFilter | null>(null);
  const [sort, setSort] = useState<PrepSort | null>(null);
  const [query, setQuery] = useState("");
  const view = useMemo(
    () => presentPracticePrep(data.rows, { filter, sort, query }),
    [data.rows, filter, sort, query],
  );
  const days = data.stale_after_days;

  const columnLabel = (c: PrepColumn): string =>
    c === "stale" ? fill(t.columns.stale, { days }) : t.columns[c];
  const toggleSort = (column: PrepColumn) =>
    setSort((s) =>
      s?.column !== column
        ? { column, direction: NUMERIC.has(column) ? "desc" : "asc" }
        : s.direction === "desc"
          ? { column, direction: "asc" }
          : null,
    );
  const filterLabel = (f: PrepFilter): string =>
    f === "stale" ? fill(t.filters.stale, { days }) : t.filters[f];

  const runCell = (r: PreparationRow) =>
    r.latest_run_number != null && r.latest_run_at
      ? fill(t.run, {
          n: r.latest_run_number,
          date: dayOf(r.latest_run_at, false),
        })
      : t.noRun;

  return (
    <>
      <div className="vb-ov-pagehead" style={{ marginBottom: "22px" }}>
        <div style={{ minWidth: 0 }}>
          <div className="vb-ov-eyebrow">
            {fill(t.kicker, { clinic: tenantName })}
          </div>
          <h1 className="vb-ov-h1">{t.title}</h1>
          <p className="vb-ov-lead">
            <b>{byCount(t.count, view.total)}</b> {t.lead}
          </p>
        </div>
      </div>

      <section
        className="vb-ov-card"
        aria-labelledby="vb-practiceprep-title"
        style={{ overflow: "hidden" }}
      >
        <div className="vb-ov-head">
          <div style={{ minWidth: 0 }}>
            <h2 id="vb-practiceprep-title" className="vb-ov-h2">
              {fill(t.shown, { shown: view.rows.length, total: view.total })}
            </h2>
            <p className="vb-ov-note">{t.note}</p>
          </div>
          <div className="vb-ov-wltools">
            <div className="vb-ov-tabs" role="group" aria-label={t.title}>
              <button
                type="button"
                className="vb-ov-tab"
                aria-pressed={filter == null}
                onClick={() => setFilter(null)}
              >
                {t.filters.all}{" "}
                <span className="vb-ov-tab-n">{view.total}</span>
              </button>
              {PREP_FILTERS.map((f) => (
                <button
                  key={f}
                  type="button"
                  className="vb-ov-tab"
                  aria-pressed={filter === f}
                  onClick={() => setFilter(filter === f ? null : f)}
                >
                  {filterLabel(f)}{" "}
                  <span className="vb-ov-tab-n">{view.counts[f]}</span>
                </button>
              ))}
            </div>
            <input
              className="vb-input vb-ov-search"
              type="text"
              aria-label={t.search}
              placeholder={t.search}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>

        {data.rows.length === 0 ? (
          <EmptyState>{t.none}</EmptyState>
        ) : view.rows.length === 0 ? (
          <EmptyState>{t.empty}</EmptyState>
        ) : (
          <div className="vb-team-scroll">
            <table className="vb-team-table vb-prep-table">
              <thead>
                <tr>
                  {COLUMNS.map((c) => {
                    const active = sort?.column === c;
                    return (
                      <th
                        key={c}
                        scope="col"
                        aria-sort={
                          active
                            ? sort.direction === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                        className={NUMERIC.has(c) ? "is-num" : undefined}
                      >
                        <button
                          type="button"
                          className="vb-prep-sort"
                          aria-label={fill(t.sort, { column: columnLabel(c) })}
                          aria-pressed={active}
                          onClick={() => toggleSort(c)}
                        >
                          {columnLabel(c)}
                          {active && (
                            <span aria-hidden="true">
                              {sort.direction === "asc" ? " ↑" : " ↓"}
                            </span>
                          )}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {view.rows.map((r) => (
                  <tr key={r.patient_id}>
                    <td>
                      <Link
                        href={`/patients/${r.patient_id}/vorbereitung`}
                        className="vb-prep-record"
                        aria-label={fill(t.open, { name: r.display_name })}
                      >
                        {r.display_name}
                      </Link>
                      <div
                        className="vb-ov-mono"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {r.external_ref ?? "—"}
                      </div>
                    </td>
                    <td>
                      {r.report_status
                        ? reportStatusLabel(r.report_status, statusWords)
                        : statusWords.none}
                    </td>
                    <td className="vb-ov-mono">{runCell(r)}</td>
                    <td className="is-num">
                      {r.latest_run_number == null ? (
                        "—"
                      ) : (
                        <>
                          {r.new_since_run}
                          {r.new_outside > 0 && (
                            <span className="vb-prep-meta">
                              {" "}
                              ({fill(t.newOutside, { n: r.new_outside })})
                            </span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="is-num">{r.outside}</td>
                    <td className="is-num">{r.stale_core}</td>
                    <td className="is-num">{r.missing_core}</td>
                    <td className="is-num">{r.values_pending}</td>
                    <td className="is-num">
                      {r.domains_without_verdict == null
                        ? "—"
                        : r.domains_without_verdict}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="vb-ov-note" style={{ padding: "12px 22px 16px" }}>
          {fill(t.coreNote, { n: data.core_markers })}
        </p>
      </section>
    </>
  );
}
