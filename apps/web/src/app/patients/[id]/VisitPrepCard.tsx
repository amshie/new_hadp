"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";

import { EmptyState } from "@/components/vitabahn/EmptyState";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { lageLabel } from "@/lib/lageCopy";
import type {
  DomainOverview,
  MarkerSeries,
} from "@/lib/presenters/domainOverview";
import {
  ACTIONABILITY_LABELS,
  ADEQUACY_LABELS,
  CIS_LABELS,
} from "@/lib/presenters/review";
import type {
  PrepCount,
  PrepTrendPoint,
  VisitPrep,
} from "@/lib/presenters/visitPrep";

import { UNASSIGNED_ID, axisLabel, sectionId } from "./DomainOverviewPanel";
import { GERMAN, LagePill } from "./MarkerParts";

// One line per domain, in the order the items already have (the catalog's).
function byAxis<T extends { axis: string }>(items: T[]): [string, T[]][] {
  const out: [string, T[]][] = [];
  for (const item of items) {
    const last = out[out.length - 1];
    if (last && last[0] === item.axis) last[1].push(item);
    else out.push([item.axis, [item]]);
  }
  return out;
}

// A marker's standing values on its interval band: a point per value, placed above, in or
// below the band by where the value lies against the laboratory's interval; a line only
// between two values the API found comparable. One value is one point and no line.
function Trend({ points, label }: { points: PrepTrendPoint[]; label: string }) {
  const W = 64;
  const H = 22;
  const y = (p: PrepTrendPoint) =>
    p.position === "above" ? 4 : p.position === "below" ? 18 : 11;
  const x = (i: number) =>
    points.length <= 1 ? W / 2 : 6 + (i * (W - 12)) / (points.length - 1);
  return (
    <svg
      role="img"
      aria-label={label}
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className="vb-prep-trend"
    >
      <rect x="0" y="7" width={W} height="8" rx="2" className="band" />
      {points.map((p, i) =>
        i > 0 && p.linked ? (
          <line
            key={`l-${p.id}`}
            x1={x(i - 1)}
            y1={y(points[i - 1]!)}
            x2={x(i)}
            y2={y(p)}
            className="link"
          />
        ) : null,
      )}
      {points.map((p, i) => (
        <circle
          key={p.id}
          cx={x(i)}
          cy={y(p)}
          r="3"
          className={
            p.position === "above" || p.position === "below" ? "out" : "in"
          }
        />
      ))}
    </svg>
  );
}

// The facts before a visit (docs/notes/0022, 0025): what stands today — every marker's
// latest value by where it lies against the laboratory's interval, and the clinician's
// own verdicts of the latest run — then what came since that run, then what is old or
// missing, grouped. Every line leads to its value. On the patient page a marker's line
// opens its history; on the page of its own it leads back to the marker's domain. Nothing
// here is a verdict of the platform's: the position names are the laboratory interval's
// sides, and the only verdicts shown are the clinician's, quoted.
export function VisitPrepCard({
  prep,
  overview,
  patientId,
  onOpen,
  standalone = false,
}: {
  prep: VisitPrep;
  overview: DomainOverview;
  patientId: string;
  onOpen?: (series: MarkerSeries) => void;
  standalone?: boolean;
}) {
  const t = useI18n().t.patientPage.visitPrep;
  const series = useMemo(() => {
    const byCode = new Map<string, MarkerSeries>();
    for (const d of overview.domains) {
      for (const row of d.rows)
        if (row.kind === "series") byCode.set(row.series.kpiCode, row.series);
    }
    return byCode;
  }, [overview]);
  const recordHref = `/patients/${patientId}`;
  // The printed page lists everything; on the screen the long lists wait behind a line.
  const [showStale, setShowStale] = useState(standalone);
  const [showMissing, setShowMissing] = useState(standalone);

  // The marker's name as the way to its value: a button that opens the history where the
  // page has one, a link to the marker's domain otherwise.
  const marker = (code: string | null, name: string, axis: string | null) => {
    const s = code ? series.get(code) : undefined;
    if (onOpen && s) {
      return (
        <button
          type="button"
          className="vb-prep-marker"
          aria-label={fill(t.line.open, { name })}
          onClick={() => onOpen(s)}
        >
          {name}
        </button>
      );
    }
    const target = axis ? `#${sectionId(axis)}` : `#${UNASSIGNED_ID}`;
    return (
      <Link
        href={`${recordHref}${target}`}
        className="vb-prep-marker"
        aria-label={fill(t.line.open, { name })}
      >
        {name}
      </Link>
    );
  };
  const reference = (
    low: string | null,
    high: string | null,
    unit: string | null,
  ) =>
    low != null || high != null
      ? fill(t.line.reference, {
          range: `${low ?? "—"}–${high ?? "—"}${unit ? ` ${unit}` : ""}`,
        })
      : t.line.noReference;
  const axes = (list: string[]) => (
    <div className="vb-prep-axes">
      {list.map((axis) => (
        <Link
          key={axis}
          href={`${recordHref}#${sectionId(axis)}`}
          className="vb-ov-tag"
          aria-label={fill(t.line.toDomain, { axis: axisLabel(axis) })}
        >
          <span lang={GERMAN}>{axisLabel(axis)}</span>
        </Link>
      ))}
    </div>
  );
  const group = (
    key: string,
    heading: string,
    sub: string | null,
    body: ReactNode,
  ) => (
    <section
      key={key}
      className="vb-prep-group"
      aria-labelledby={`vb-prep-${key}`}
    >
      <h4 id={`vb-prep-${key}`}>
        {heading}
        {sub && <small> · {sub}</small>}
      </h4>
      {body}
    </section>
  );
  const chips = (counts: PrepCount[]) => (
    <div className="vb-prep-chips">
      {counts.map((c) => (
        <span key={c.key} className="vb-prep-chip">
          <span lang={GERMAN}>{axisLabel(c.key)}</span> <b>{c.count}</b>
        </span>
      ))}
    </div>
  );
  const days = (counts: PrepCount[]) =>
    counts.length === 1
      ? fill(t.gaps.allFrom, { date: counts[0]!.key })
      : counts
          .map((c) => fill(t.gaps.from, { n: c.count, date: c.key }))
          .join(" · ");

  const today = prep.today;
  const coreTotal = prep.domains.reduce((n, d) => n + d.coreTotal, 0);
  const inadequate = prep.domains.filter(
    (d) => d.verdict?.followupAdequacy === "inadequate",
  ).length;
  const unassessed = prep.domains.filter(
    (d) => d.verdict?.followupAdequacy === "not_assessed",
  ).length;

  // --- Since the run: the lists when something came, one line when nothing did ----------
  const since: ReactNode[] = [];
  if (prep.run && prep.newValues.length > 0) {
    since.push(
      group(
        "new",
        fill(byCount(t.groups.newValues, prep.newValues.length), {
          run: prep.run.number,
        }),
        prep.newOutside > 0
          ? byCount(t.groups.newOutside, prep.newOutside)
          : null,
        <ul className="vb-prep-list">
          {prep.newValues.map((v) => (
            <li key={v.valueId}>
              {marker(v.code, v.name, v.axis)}
              <span className="vb-prep-value">
                {v.value ?? "—"}
                {v.unit ? ` ${v.unit}` : ""}
              </span>
              <span className="vb-prep-meta">
                {reference(v.referenceLow, v.referenceHigh, v.unit)}
              </span>
              <span className="vb-prep-meta">
                {fill(v.derived ? t.line.derived : t.line.measured, {
                  date: v.observedDay,
                })}
              </span>
              {v.axis == null && (
                <span className="vb-prep-meta">{t.line.unassigned}</span>
              )}
              <LagePill pos={v.position} />
            </li>
          ))}
        </ul>,
      ),
    );
  }
  if (prep.moved.length > 0) {
    since.push(
      group(
        "moved",
        byCount(t.groups.moved, prep.moved.length),
        null,
        <ul className="vb-prep-list">
          {prep.moved.map((m) => (
            <li key={m.latestId}>
              {marker(m.code, m.name, m.axis)}
              <span lang={GERMAN}>
                {fill(t.line.moved, {
                  from: lageLabel(m.from).label,
                  to: lageLabel(m.to).label,
                })}
              </span>
              <span className="vb-prep-value">
                {m.value ?? "—"}
                {m.unit ? ` ${m.unit}` : ""}
              </span>
              <span className="vb-prep-meta">
                {reference(m.referenceLow, m.referenceHigh, m.unit)}
              </span>
              <span className="vb-prep-meta">
                {fill(t.line.movedDays, {
                  previous: m.previousDay,
                  latest: m.latestDay,
                })}
              </span>
            </li>
          ))}
        </ul>,
      ),
    );
  }
  if (prep.run && prep.domainsWithoutVerdict.length > 0) {
    since.push(
      group(
        "noverdict",
        fill(byCount(t.groups.noVerdict, prep.domainsWithoutVerdict.length), {
          run: prep.run.number,
        }),
        null,
        axes(prep.domainsWithoutVerdict),
      ),
    );
  }
  if (prep.domainsCitingReplaced.length > 0) {
    since.push(
      group(
        "replaced",
        byCount(t.groups.citesReplaced, prep.domainsCitingReplaced.length),
        null,
        axes(prep.domainsCitingReplaced),
      ),
    );
  }

  return (
    <section
      className="vb-ov-card"
      aria-labelledby="vb-visitprep-title"
      style={{ marginBottom: "20px", overflow: "hidden" }}
    >
      <div className="vb-prep-head">
        <div style={{ minWidth: 0 }}>
          <span className="vb-ov-eyebrow">
            {prep.run
              ? fill(t.sinceRun, { n: prep.run.number, date: prep.run.day })
              : t.noRun}
          </span>
          <h3 id="vb-visitprep-title" className="vb-ov-h2">
            {t.title}
          </h3>
          <p className="vb-ov-note">{t.note}</p>
        </div>
        <div className="vb-prep-tools vb-noprint">
          {standalone ? (
            <>
              <button
                type="button"
                className="vb-ov-btn primary"
                onClick={() => window.print()}
              >
                {t.print}
              </button>
              <Link href={recordHref} className="vb-ov-btn">
                {t.backToRecord}
              </Link>
            </>
          ) : (
            <Link href={`${recordHref}/vorbereitung`} className="vb-ov-btn">
              {t.open}
            </Link>
          )}
        </div>
      </div>

      {/* 1 · What stands today: the counts in three seconds, then the two lists. */}
      <section className="vb-prep-today" aria-labelledby="vb-prep-today">
        <h4 id="vb-prep-today">
          {t.today.title}
          {today.latestDay && (
            <small> · {fill(t.today.asOf, { date: today.latestDay })}</small>
          )}
        </h4>
        {today.withValue === 0 ? (
          <div className="vb-prep-quiet">
            <EmptyState quiet style={{ padding: 0 }}>
              {t.today.noValues}
            </EmptyState>
          </div>
        ) : (
          <>
            <ul className="vb-prep-tally">
              <li>
                <b>{today.withValue}</b>
                <span>{t.today.tally.withValue}</span>
              </li>
              <li data-tone={today.outside.length > 0 ? "out" : undefined}>
                <b>{today.outside.length}</b>
                <span>{t.today.tally.outside}</span>
              </li>
              <li>
                <b>{today.within}</b>
                <span>{t.today.tally.within}</span>
              </li>
              <li>
                <b>{today.noReference}</b>
                <span>{t.today.tally.noReference}</span>
              </li>
              {today.derived > 0 && (
                <li>
                  <b>{today.derived}</b>
                  <span>{t.today.tally.derived}</span>
                </li>
              )}
              <li data-tone={prep.pending > 0 ? "wait" : undefined}>
                <b>{prep.pending}</b>
                <span>{t.today.tally.pending}</span>
              </li>
            </ul>
            <div className="vb-prep-cols">
              <div className="vb-prep-col">
                <h5>
                  {t.today.outsideTitle}
                  <span className="vb-prep-meta">
                    {fill(t.today.ofAll, {
                      n: today.outside.length,
                      total: today.withValue,
                    })}
                  </span>
                </h5>
                {today.outside.length === 0 ? (
                  <p className="vb-prep-meta vb-prep-para">
                    {t.today.noneOutside}
                  </p>
                ) : (
                  <div className="vb-team-scroll">
                    <table className="vb-team-table vb-prep-today-table">
                      <thead>
                        <tr>
                          <th scope="col">{t.today.columns.marker}</th>
                          <th scope="col">{t.today.columns.trend}</th>
                          <th scope="col" className="is-num">
                            {t.today.columns.value}
                          </th>
                          <th scope="col">{t.today.columns.reference}</th>
                          <th scope="col">{t.today.columns.position}</th>
                          <th scope="col">{t.today.columns.measured}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {today.outside.map((o) => (
                          <tr key={o.valueId}>
                            <td>
                              {marker(o.code, o.name, o.axis)}
                              <div className="vb-prep-meta" lang={GERMAN}>
                                {axisLabel(o.axis)}
                              </div>
                            </td>
                            <td>
                              <Trend
                                points={o.trend}
                                label={byCount(t.today.trend, o.trend.length)}
                              />
                              <div className="vb-prep-meta">
                                {byCount(t.today.measurements, o.trend.length)}
                              </div>
                            </td>
                            <td className="is-num">
                              {o.value ?? "—"}
                              {o.unit ? ` ${o.unit}` : ""}
                            </td>
                            <td className="vb-ov-mono">
                              {o.referenceLow ?? "—"}–{o.referenceHigh ?? "—"}
                            </td>
                            <td>
                              <LagePill pos={o.position} />
                            </td>
                            <td className="vb-ov-mono">{o.observedDay}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <p className="vb-prep-meta vb-prep-para">{t.today.trendNote}</p>
                {today.noReference > 0 && (
                  <p className="vb-prep-meta vb-prep-para">
                    {fill(t.today.noReferenceNote, { n: today.noReference })}{" "}
                    <Link href={`${recordHref}#werte`}>{t.today.toValues}</Link>
                  </p>
                )}
              </div>
              <div className="vb-prep-col">
                <h5>
                  {t.today.verdictsTitle}
                  <span className="vb-prep-meta">
                    {prep.run
                      ? fill(t.today.runMeta, {
                          n: prep.run.number,
                          date: prep.run.day,
                        })
                      : t.today.noRunMeta}
                  </span>
                </h5>
                <div className="vb-team-scroll">
                  <table className="vb-team-table vb-prep-today-table">
                    <thead>
                      <tr>
                        <th scope="col">{t.today.verdictColumns.domain}</th>
                        <th scope="col" className="is-num">
                          {t.today.verdictColumns.outside}
                        </th>
                        <th scope="col">{t.today.verdictColumns.cis}</th>
                        <th scope="col">
                          {t.today.verdictColumns.actionability}
                        </th>
                        <th scope="col">{t.today.verdictColumns.followup}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prep.domains.map((d) => (
                        <tr key={d.axis}>
                          <td>
                            <Link
                              href={`${recordHref}#${sectionId(d.axis)}`}
                              className="vb-prep-record"
                              aria-label={fill(t.line.toDomain, {
                                axis: axisLabel(d.axis),
                              })}
                            >
                              <span lang={GERMAN}>{axisLabel(d.axis)}</span>
                            </Link>
                            <div className="vb-prep-meta">
                              {fill(t.today.withValue, {
                                x: d.coreWithValue,
                                n: d.coreTotal,
                              })}
                            </div>
                          </td>
                          <td className="is-num">
                            {d.outside > 0 ? (
                              <span className="vb-prep-outn">{d.outside}</span>
                            ) : (
                              "0"
                            )}
                          </td>
                          {d.verdict ? (
                            <>
                              <td lang={GERMAN}>
                                {CIS_LABELS[d.verdict.cisStatus] ??
                                  d.verdict.cisStatus}
                              </td>
                              <td lang={GERMAN}>
                                {ACTIONABILITY_LABELS[
                                  d.verdict.actionabilityClass
                                ] ?? d.verdict.actionabilityClass}
                              </td>
                              <td lang={GERMAN}>
                                {ADEQUACY_LABELS[d.verdict.followupAdequacy] ??
                                  d.verdict.followupAdequacy}
                              </td>
                            </>
                          ) : (
                            <td colSpan={3} className="vb-prep-meta">
                              {t.today.noVerdict}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="vb-prep-meta vb-prep-para">
                  {t.today.verdictsNote}
                  {prep.run &&
                    (inadequate > 0 || unassessed > 0) &&
                    ` ${fill(t.today.verdictsCounts, { inadequate, unassessed })}`}
                </p>
              </div>
            </div>
          </>
        )}
      </section>

      {/* 2 · Since the run. */}
      {since.length > 0 ? (
        since
      ) : (
        <section className="vb-prep-group" aria-labelledby="vb-prep-since">
          <h4 id="vb-prep-since">
            {prep.run
              ? fill(t.since.title, { n: prep.run.number, date: prep.run.day })
              : t.since.noRunTitle}
          </h4>
          <div className="vb-prep-chips vb-prep-para">
            <span className="vb-prep-chip">
              {prep.run ? t.since.none : t.since.noRun}
            </span>
            {prep.pending > 0 && (
              <span className="vb-prep-chip">
                {byCount(t.groups.pending, prep.pending)} ·{" "}
                <Link href="/review-queue">{t.line.toQueue}</Link>
              </span>
            )}
            {prep.unassigned > 0 && (
              <span className="vb-prep-chip">
                {byCount(t.groups.unassigned, prep.unassigned)}
              </span>
            )}
          </div>
        </section>
      )}

      {/* 3 · Old and missing, grouped; the lists on request. */}
      <section className="vb-prep-group" aria-labelledby="vb-prep-gaps">
        <h4 id="vb-prep-gaps">
          {t.gaps.title}
          <small>
            {" "}
            · {fill(t.gaps.note, { n: coreTotal, days: prep.staleAfterDays })}
          </small>
        </h4>
        <div className="vb-prep-cols vb-prep-para">
          <div className="vb-prep-col">
            <h5>
              {fill(byCount(t.groups.stale, prep.stale.length), {
                days: prep.staleAfterDays,
              })}
              {prep.stale.length > 0 && (
                <span className="vb-prep-meta">{days(prep.staleByDay)}</span>
              )}
            </h5>
            {prep.stale.length === 0 ? (
              <p className="vb-prep-meta vb-prep-para">
                {fill(t.gaps.noneStale, { days: prep.staleAfterDays })}
              </p>
            ) : (
              <>
                {chips(prep.staleByAxis)}
                <button
                  type="button"
                  className="vb-prep-fold vb-noprint"
                  aria-expanded={showStale}
                  onClick={() => setShowStale((v) => !v)}
                >
                  {showStale
                    ? t.gaps.hide
                    : byCount(t.gaps.show, prep.stale.length)}
                </button>
                {showStale && (
                  <ul className="vb-prep-list">
                    {byAxis(prep.stale).map(([axis, items]) => (
                      <li key={axis}>
                        <span className="vb-prep-domain" lang={GERMAN}>
                          {axisLabel(axis)}
                        </span>
                        {items.map((s, i) => (
                          <span key={s.latestId} className="vb-prep-item">
                            {marker(s.code, s.name, s.axis)}
                            <span className="vb-prep-meta">
                              {" "}
                              ({s.observedDay})
                            </span>
                            {i < items.length - 1 ? "," : ""}
                          </span>
                        ))}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
          <div className="vb-prep-col">
            <h5>
              {byCount(t.groups.missing, prep.missing.length)}
              {prep.missing.length > 0 && (
                <span className="vb-prep-meta">{t.gaps.never}</span>
              )}
            </h5>
            {prep.missing.length === 0 ? (
              <p className="vb-prep-meta vb-prep-para">{t.gaps.noneMissing}</p>
            ) : (
              <>
                {chips(prep.missingByAxis)}
                <button
                  type="button"
                  className="vb-prep-fold vb-noprint"
                  aria-expanded={showMissing}
                  onClick={() => setShowMissing((v) => !v)}
                >
                  {showMissing
                    ? t.gaps.hide
                    : byCount(t.gaps.show, prep.missing.length)}
                </button>
                {showMissing && (
                  <ul className="vb-prep-list">
                    {byAxis(prep.missing).map(([axis, items]) => (
                      <li key={axis}>
                        <span className="vb-prep-domain" lang={GERMAN}>
                          {axisLabel(axis)}
                        </span>
                        {items.map((m, i) => (
                          <span key={m.code} className="vb-prep-item">
                            {marker(null, m.name, m.axis)}
                            {i < items.length - 1 ? "," : ""}
                          </span>
                        ))}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </section>
  );
}
