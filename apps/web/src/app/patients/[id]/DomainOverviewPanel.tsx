"use client";

import { useState, type CSSProperties } from "react";
import Link from "next/link";

import { clickable } from "@/components/vitabahn/interactive";
import { comparabilityNote } from "@/lib/comparabilityCopy";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import {
  deltaDirection,
  PREP_FILTERS,
  rowMatches,
  valueMatches,
  type DomainOverview,
  type DomainRow,
  type DomainSection,
  type MarkerSeries,
  type PrepFilter,
  type TimeAxis,
  type ValueView,
} from "@/lib/presenters/domainOverview";
import {
  ACTIONABILITY_LABELS,
  ADEQUACY_LABELS,
  CIS_LABELS,
  DOMAIN_AXIS_LABELS,
} from "@/lib/presenters/review";
import { referenceBar } from "@/lib/referencePosition";

import { Sparkline } from "./HistoryChart";
import { GERMAN, LagePill, ReferenceBar } from "./MarkerParts";

// The patient page's domain overview (docs/notes/0006, the domain timelines): the counts
// before a visit, a card per domain, and each domain's markers with their latest value. Values
// are placed by the KPI catalog; counts are counts; the only verdicts are the clinician's own,
// quoted from the latest run with its number and date. Nothing here is rated or scored
// (ADR-0003, ADR-0006).

type T = Messages["patientPage"];

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};
const colLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "9.5px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};
const heading: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 800,
  fontSize: "var(--text-xl)",
  color: "var(--text-strong)",
  margin: "0 0 3px",
  letterSpacing: "-0.02em",
};
const note: CSSProperties = {
  fontSize: "12.5px",
  color: "var(--text-muted)",
  margin: 0,
  maxWidth: "94ch",
  lineHeight: 1.5,
};
const chip: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "2px 9px",
  borderRadius: "999px",
  fontFamily: "var(--font-text)",
  fontSize: "11px",
  fontWeight: 600,
  color: "var(--text-muted)",
  background: "var(--surface-sunken)",
  border: "1px solid var(--border-subtle)",
  whiteSpace: "nowrap",
};
const warnChip: CSSProperties = {
  ...chip,
  color: "var(--amber-500)",
  background: "rgba(201,136,28,0.12)",
  border: "1px solid rgba(201,136,28,0.30)",
};
const EGRID =
  "minmax(160px,1.5fr) 132px minmax(110px,0.9fr) minmax(110px,1fr) 150px minmax(100px,0.8fr) 104px";

function axisLabel(axis: string): string {
  return DOMAIN_AXIS_LABELS[axis] ?? axis;
}

function sectionId(axis: string): string {
  return `vb-domain-${axis}`;
}

function ago(days: number, t: T["evidence"]["ago"]): string {
  if (days === 0) return t.today;
  if (days < 45) return byCount(t.days, days);
  return byCount(t.months, Math.round(days / 30.44));
}

function valueText(v: ValueView): string {
  if (v.value != null) return v.unit ? `${v.value} ${v.unit}` : v.value;
  return v.originalUnit
    ? `${v.originalValue} ${v.originalUnit}`
    : v.originalValue;
}

// The change the API computed, beside an arrow; a withheld change says why (a closed
// vocabulary, German); nothing to compare is a dash.
export function ChangeText({ v, t }: { v: ValueView; t: T["evidence"] }) {
  if (v.delta != null) {
    const dir = deltaDirection(v.delta);
    const magnitude = v.delta.replace(/^[-+]/, "");
    const sign = dir === "up" ? "+" : dir === "down" ? "−" : "";
    return (
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "12.5px",
          color: "var(--text-strong)",
          whiteSpace: "nowrap",
        }}
      >
        <span aria-hidden="true" style={{ color: "var(--text-muted)" }}>
          {dir === "up" ? "↑" : dir === "down" ? "↓" : "→"}{" "}
        </span>
        {sign}
        {magnitude}
        {v.unit ? ` ${v.unit}` : ""}
      </span>
    );
  }
  const withheld = comparabilityNote(v.comparability, v.comparabilityReason);
  if (withheld)
    return (
      <span
        lang={GERMAN}
        title={withheld.full}
        style={{ fontSize: "11.5px", color: "var(--text-muted)" }}
      >
        {withheld.short}
      </span>
    );
  return <span style={{ color: "var(--text-faint)" }}>{t.noChange}</span>;
}

function PrepCard({
  overview,
  filter,
  setFilter,
  t,
}: {
  overview: DomainOverview;
  filter: PrepFilter | null;
  setFilter: (f: PrepFilter | null) => void;
  t: T["prep"];
}) {
  const coreTotal = overview.domains.reduce((n, d) => n + d.facts.coreTotal, 0);
  return (
    <section
      aria-labelledby="vb-prep-title"
      style={{ ...cardStyle, padding: "18px 22px 20px", marginBottom: "20px" }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px 16px",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: "14px",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h3 id="vb-prep-title" style={heading}>
            {t.title}
          </h3>
          <p style={note}>{t.note}</p>
        </div>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10.5px",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-faint)",
          }}
        >
          {overview.runNumber != null && overview.runRecordedDay != null
            ? fill(t.lastRun, {
                n: overview.runNumber,
                date: overview.runRecordedDay,
              })
            : t.noRun}
        </span>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "10px",
        }}
      >
        {PREP_FILTERS.map((key) => {
          const n = overview.counts[key];
          const fact = t.facts[key];
          const sub =
            key === "since_run"
              ? n == null
                ? t.facts.since_run.noRun
                : fill(t.facts.since_run.note, {
                    date: overview.runRecordedDay ?? "",
                  })
              : key === "missing"
                ? fill(t.facts.missing.note, { n: coreTotal })
                : t.facts[key].note;
          const body = (
            <>
              <span
                style={{
                  gridRow: "span 2",
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "26px",
                  lineHeight: 1,
                  color: "var(--text-strong)",
                  minWidth: "26px",
                }}
              >
                {n ?? "—"}
              </span>
              <span
                style={{
                  fontSize: "12.5px",
                  fontWeight: 600,
                  color: "var(--text-strong)",
                }}
              >
                {byCount(fact.label, n ?? 0)}
              </span>
              <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                {sub}
              </span>
            </>
          );
          const box: CSSProperties = {
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: "2px 11px",
            alignItems: "center",
            textAlign: "left",
            padding: "11px 14px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-subtle)",
            fontFamily: "var(--font-text)",
          };
          if (n == null)
            return (
              <div key={key} style={box}>
                {body}
              </div>
            );
          const pressed = filter === key;
          return (
            <button
              key={key}
              type="button"
              className="vb-prepfact"
              aria-pressed={pressed}
              onClick={() => setFilter(pressed ? null : key)}
              style={{
                ...box,
                cursor: "pointer",
                border:
                  "1px solid " +
                  (pressed ? "var(--brand)" : "var(--border-subtle)"),
                boxShadow: pressed ? "0 0 0 3px var(--brand-soft)" : "none",
                background: pressed
                  ? "var(--surface-card)"
                  : "var(--bg-subtle)",
              }}
            >
              {body}
            </button>
          );
        })}
      </div>
      {filter && (
        <p
          role="status"
          style={{
            ...note,
            marginTop: "12px",
            display: "flex",
            flexWrap: "wrap",
            gap: "4px 12px",
            alignItems: "center",
          }}
        >
          <span>{t.filtered[filter]}</span>
          <button
            type="button"
            onClick={() => setFilter(null)}
            style={{
              background: "none",
              border: 0,
              padding: 0,
              color: "var(--brand)",
              fontWeight: 600,
              fontSize: "12.5px",
              cursor: "pointer",
            }}
          >
            {t.showAll}
          </button>
        </p>
      )}
    </section>
  );
}

function DomainCard({
  domain,
  overview,
  t,
}: {
  domain: DomainSection;
  overview: DomainOverview;
  t: T["domains"];
}) {
  const f = domain.facts;
  const v = domain.verdict;
  const factRow = (glyph: string, text: string, quiet: boolean) => (
    <li
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: "7px",
        color: quiet ? "var(--text-faint)" : "var(--text-body)",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: "14px",
          textAlign: "center",
          color: "var(--text-muted)",
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        {glyph}
      </span>
      <span>{text}</span>
    </li>
  );
  return (
    <div
      className="vb-domaincard"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        background: "var(--surface-card)",
        borderRadius: "var(--radius-lg)",
        padding: "15px 17px 14px",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-xs)",
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: "10px",
        }}
      >
        <a
          href={`#${sectionId(domain.axis)}`}
          aria-label={fill(t.go, { axis: axisLabel(domain.axis) })}
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-md)",
            color: "var(--text-strong)",
            letterSpacing: "-0.01em",
            textDecoration: "none",
          }}
        >
          <span lang={GERMAN}>{axisLabel(domain.axis)}</span>
        </a>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10.5px",
            color: "var(--text-faint)",
            whiteSpace: "nowrap",
          }}
        >
          {f.coreTotal > 0 ? byCount(t.coreMarkers, f.coreTotal) : t.noCore}
        </span>
      </div>
      {f.coreTotal > 0 && (
        <div>
          {/* One segment per core marker: filled once it has a published value. */}
          <div
            aria-hidden="true"
            style={{ display: "flex", gap: "2px", height: "7px" }}
          >
            {domain.rows
              .filter((r) => r.kind === "missing" || r.series.core)
              .map((r) => (
                <i
                  key={r.kind === "missing" ? r.marker.code : r.series.kpiCode}
                  style={{
                    flex: 1,
                    borderRadius: "2px",
                    background:
                      r.kind === "series" && r.series.latest != null
                        ? "var(--teal-500)"
                        : "var(--border-subtle)",
                  }}
                />
              ))}
          </div>
          <div
            style={{
              fontSize: "11.5px",
              color: "var(--text-muted)",
              marginTop: "5px",
            }}
          >
            {fill(t.coverage, { x: f.coreWithValue, n: f.coreTotal })}
          </div>
        </div>
      )}
      <ul
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          fontSize: "12.5px",
        }}
      >
        {f.latestObservedAt == null ? (
          factRow("⊘", t.noValue, true)
        ) : (
          <>
            {factRow(
              "↕",
              f.outside > 0 ? byCount(t.outside, f.outside) : t.outsideNone,
              f.outside === 0,
            )}
            {factRow(
              "◷",
              f.pending > 0 ? byCount(t.pending, f.pending) : t.pendingNone,
              f.pending === 0,
            )}
            {factRow(
              "▤",
              fill(t.latest, { date: f.latestObservedDay ?? "" }),
              false,
            )}
          </>
        )}
      </ul>
      <div
        style={{
          borderTop: "1px solid var(--border-subtle)",
          paddingTop: "10px",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "8px",
            alignItems: "baseline",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            {t.interpretation}
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            {v ? (v.reviewed ? t.reviewed : t.draft) : t.none}
          </span>
        </div>
        {v ? (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {[
                CIS_LABELS[v.cisStatus] ?? v.cisStatus,
                ACTIONABILITY_LABELS[v.actionabilityClass] ??
                  v.actionabilityClass,
              ].map((label) => (
                // Neutral on purpose: the clinician's own words, never styled as a grade.
                <span
                  key={label}
                  lang={GERMAN}
                  style={{
                    fontSize: "11.5px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                    border: "1px solid var(--border-default)",
                    background: "var(--surface-card)",
                    borderRadius: "6px",
                    padding: "2px 8px",
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {t.adequacy}{" "}
              <span lang={GERMAN}>
                {ADEQUACY_LABELS[v.followupAdequacy] ?? v.followupAdequacy}
              </span>
            </div>
            {overview.runNumber != null && overview.runRecordedDay != null && (
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {fill(t.run, {
                  n: overview.runNumber,
                  date: overview.runRecordedDay,
                })}
              </div>
            )}
            {f.receivedSinceRun > 0 && (
              <div
                style={{
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "var(--amber-500)",
                }}
              >
                <span aria-hidden="true">◷ </span>
                {byCount(t.sinceRun, f.receivedSinceRun)}
              </div>
            )}
            {v.citesReplaced && (
              <div style={{ fontSize: "12px", color: "var(--danger)" }}>
                {t.citesReplaced}
              </div>
            )}
          </>
        ) : (
          <div style={{ fontSize: "12px", color: "var(--text-faint)" }}>
            {t.notInterpreted}
          </div>
        )}
      </div>
    </div>
  );
}

function SeriesRow({
  series,
  axis,
  onOpen,
  t,
  showDomain,
}: {
  series: MarkerSeries;
  axis: TimeAxis | null;
  onOpen: (s: MarkerSeries) => void;
  t: T;
  showDomain: boolean;
}) {
  const e = t.evidence;
  // The latest standing value — or, before any is published, the newest value there is.
  const shown = series.latest ?? series.values[series.values.length - 1];
  if (!shown) return null;
  const standing = series.latest != null;
  return (
    <div
      className="vb-erow"
      {...clickable(() => onOpen(series), fill(e.open, { name: series.name }))}
      style={{
        display: "grid",
        gridTemplateColumns: EGRID,
        alignItems: "center",
        gap: "14px",
        padding: "12px 22px",
        borderBottom: "1px solid var(--border-subtle)",
        cursor: "pointer",
      }}
    >
      <span style={{ minWidth: 0 }}>
        <span
          style={{
            display: "block",
            fontSize: "13.5px",
            fontWeight: 600,
            color: "var(--text-strong)",
            lineHeight: 1.3,
          }}
        >
          {series.name}
        </span>
        <span
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "5px",
            marginTop: "5px",
          }}
        >
          {showDomain && (
            <span style={chip}>
              <span lang={GERMAN}>{axisLabel(series.primaryDomain)}</span>
            </span>
          )}
          {series.pending > 0 && (
            <span style={warnChip}>
              <span aria-hidden="true">◷&nbsp;</span>
              {byCount(e.pending, series.pending)}
            </span>
          )}
          {series.corrected && <span style={chip}>{e.corrected}</span>}
        </span>
      </span>
      <span>{axis && <Sparkline series={series} axis={axis} />}</span>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "13px",
          fontWeight: 600,
          color: standing ? "var(--text-strong)" : "var(--text-muted)",
          overflowWrap: "anywhere",
        }}
      >
        {valueText(shown)}
        {/* Before any value is published, the newest one shows as what it is. */}
        {!standing && (
          <span
            style={{
              display: "block",
              fontFamily: "var(--font-text)",
              fontSize: "11px",
              fontWeight: 600,
              color: "var(--text-body)",
            }}
          >
            {(t.valueStatus as Record<string, string>)[shown.status] ??
              shown.status}
          </span>
        )}
      </span>
      <span>{standing ? <ChangeText v={shown} t={e} /> : null}</span>
      <span>{standing ? <LagePill pos={shown.position} /> : "—"}</span>
      <span>
        {standing ? (
          <ReferenceBar
            bar={referenceBar(
              shown.value,
              shown.referenceLow,
              shown.referenceHigh,
            )}
            range={
              shown.referenceLow != null && shown.referenceHigh != null
                ? `${shown.referenceLow}–${shown.referenceHigh}`
                : null
            }
          />
        ) : null}
      </span>
      <span>
        <span
          style={{
            display: "block",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            color: "var(--text-body)",
          }}
        >
          {shown.observedDay}
        </span>
        <span
          style={{
            display: "block",
            fontSize: "11px",
            color: "var(--text-faint)",
          }}
        >
          {ago(shown.ageDays, e.ago)}
        </span>
      </span>
    </div>
  );
}

function MissingRow({
  row,
  t,
}: {
  row: Extract<DomainRow, { kind: "missing" }>;
  t: T["evidence"];
}) {
  const classes: Record<string, string> = t.measurementClass;
  return (
    <div
      className="vb-missingrow"
      style={{
        display: "grid",
        gridTemplateColumns: EGRID,
        alignItems: "center",
        gap: "14px",
        padding: "12px 22px",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <span style={{ minWidth: 0 }}>
        {/* The catalog's name: no source has named this marker for the record. */}
        <span
          lang="en"
          title={t.catalogName}
          style={{
            display: "block",
            fontSize: "13.5px",
            fontWeight: 500,
            color: "var(--text-muted)",
            lineHeight: 1.3,
          }}
        >
          {row.marker.name}
        </span>
        <span style={{ display: "flex", marginTop: "5px" }}>
          <span style={chip}>
            {classes[row.marker.measurementClass] ??
              row.marker.measurementClass}
          </span>
        </span>
      </span>
      <span
        style={{
          gridColumn: "2 / -1",
          fontSize: "12.5px",
          color: "var(--text-faint)",
        }}
      >
        {t.missing}
      </span>
    </div>
  );
}

function DomainSectionCard({
  domain,
  axis,
  filter,
  onOpen,
  t,
}: {
  domain: DomainSection;
  axis: TimeAxis | null;
  filter: PrepFilter | null;
  onOpen: (s: MarkerSeries) => void;
  t: T;
}) {
  const e = t.evidence;
  const rows = domain.rows.filter((r) => rowMatches(r, filter));
  const also = domain.alsoRelevant.filter((s) =>
    rowMatches({ kind: "series", series: s }, filter),
  );
  const shown = rows.length + also.length;
  return (
    <section
      id={sectionId(domain.axis)}
      aria-labelledby={`${sectionId(domain.axis)}-title`}
      style={{
        ...cardStyle,
        marginBottom: "16px",
        overflow: "hidden",
        scrollMarginTop: "16px",
      }}
    >
      <div
        style={{
          padding: "16px 22px 10px",
          display: "flex",
          flexWrap: "wrap",
          gap: "6px 16px",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--text-faint)",
            }}
          >
            {e.eyebrow}
          </div>
          <h3 id={`${sectionId(domain.axis)}-title`} style={heading}>
            <span lang={GERMAN}>{axisLabel(domain.axis)}</span>
          </h3>
          <p style={note}>{e.note}</p>
        </div>
        <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
          {domain.facts.coreTotal > 0 &&
            fill(e.counts, {
              x: domain.facts.coreWithValue,
              n: domain.facts.coreTotal,
            })}
          {filter && (
            <>
              {domain.facts.coreTotal > 0 && " · "}
              {byCount(e.filteredCount, shown)}
            </>
          )}
        </span>
      </div>
      {shown === 0 ? (
        <p style={{ ...note, padding: "6px 22px 18px" }}>
          {filter ? e.emptyFilter : e.empty}
        </p>
      ) : (
        // Relative: the rows' screen-reader sentences (.sr-only, absolute) are held in this
        // scroller — otherwise they reach past a narrow screen and widen the whole page.
        <div style={{ position: "relative", overflowX: "auto" }}>
          <div style={{ minWidth: "880px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: EGRID,
                alignItems: "center",
                gap: "14px",
                padding: "9px 22px",
                borderTop: "1px solid var(--border-subtle)",
                borderBottom: "1px solid var(--border-subtle)",
                background: "var(--surface-sunken)",
              }}
            >
              <span style={colLabel}>{e.columns.marker}</span>
              <span style={colLabel}>{t.history.column}</span>
              <span style={colLabel}>{e.columns.value}</span>
              <span style={colLabel}>{e.columns.change}</span>
              <span style={colLabel}>{e.columns.position}</span>
              <span style={colLabel}>{e.columns.bar}</span>
              <span style={colLabel}>{e.columns.measured}</span>
            </div>
            {rows.map((r) =>
              r.kind === "series" ? (
                <SeriesRow
                  key={r.series.kpiCode}
                  series={r.series}
                  axis={axis}
                  onOpen={onOpen}
                  t={t}
                  showDomain={false}
                />
              ) : (
                <MissingRow key={r.marker.code} row={r} t={e} />
              ),
            )}
            {also.length > 0 && (
              <>
                <div
                  style={{
                    padding: "12px 22px 8px",
                    borderBottom: "1px solid var(--border-subtle)",
                    background: "var(--bg-subtle)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "12.5px",
                      fontWeight: 700,
                      color: "var(--text-strong)",
                    }}
                  >
                    {e.alsoRelevant}
                  </div>
                  <div
                    style={{ fontSize: "11.5px", color: "var(--text-muted)" }}
                  >
                    {e.alsoRelevantNote}
                  </div>
                </div>
                {also.map((s) => (
                  <SeriesRow
                    key={`also-${s.kpiCode}`}
                    series={s}
                    axis={axis}
                    onOpen={onOpen}
                    t={t}
                    showDomain
                  />
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function UnassignedCard({
  values,
  filter,
  t,
}: {
  values: ValueView[];
  filter: PrepFilter | null;
  t: T;
}) {
  const shown = values.filter((v) => valueMatches(v, filter));
  if (shown.length === 0) return null;
  const status: Record<string, string> = t.valueStatus;
  return (
    <section
      aria-labelledby="vb-unassigned-title"
      style={{ ...cardStyle, padding: "16px 22px 18px", marginBottom: "16px" }}
    >
      <h3 id="vb-unassigned-title" style={heading}>
        {t.unassigned.title}
      </h3>
      <p style={{ ...note, marginBottom: "12px" }}>{t.unassigned.note}</p>
      <ul
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        {shown.map((v) => (
          <li
            key={v.id}
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "8px 18px",
              padding: "10px 14px",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              background: "var(--bg-subtle)",
            }}
          >
            <span
              style={{
                fontWeight: 600,
                fontSize: "13.5px",
                color: "var(--text-strong)",
                minWidth: "140px",
              }}
            >
              {v.name}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--text-strong)",
              }}
            >
              {valueText(v)}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-body)",
              }}
            >
              {v.observedDay}
            </span>
            <span style={v.status === "pending" ? warnChip : chip}>
              {status[v.status] ?? v.status}
            </span>
            {v.status === "pending" && (
              <Link
                href="/review-queue"
                style={{
                  marginLeft: "auto",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  color: "var(--brand)",
                }}
              >
                {t.unassigned.openQueue}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DomainOverviewPanel({
  overview,
  onOpen,
}: {
  overview: DomainOverview;
  onOpen: (s: MarkerSeries) => void;
}) {
  const t = useI18n().t.patientPage;
  const [filter, setFilter] = useState<PrepFilter | null>(null);
  return (
    <>
      <PrepCard
        overview={overview}
        filter={filter}
        setFilter={setFilter}
        t={t.prep}
      />
      <section
        aria-labelledby="vb-domains-title"
        style={{ marginBottom: "20px" }}
      >
        <h3 id="vb-domains-title" style={heading}>
          {t.domains.title}
        </h3>
        <p style={{ ...note, marginBottom: "12px" }}>{t.domains.note}</p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(258px, 1fr))",
            gap: "14px",
          }}
        >
          {overview.domains.map((d) => (
            <DomainCard
              key={d.axis}
              domain={d}
              overview={overview}
              t={t.domains}
            />
          ))}
        </div>
      </section>
      {overview.domains.map((d) => (
        <DomainSectionCard
          key={d.axis}
          domain={d}
          axis={overview.timeAxis}
          filter={filter}
          onOpen={onOpen}
          t={t}
        />
      ))}
      <UnassignedCard values={overview.unassigned} filter={filter} t={t} />
    </>
  );
}

// Every value of one marker, newest first, in the marker dialog: what the latest value stands
// on — including what was replaced, rejected, or is still in review, each saying so.
export function SeriesValues({ series, t }: { series: MarkerSeries; t: T }) {
  const m = t.marker;
  const status: Record<string, string> = t.valueStatus;
  const cell: CSSProperties = {
    padding: "8px 10px",
    borderBottom: "1px solid var(--border-subtle)",
    verticalAlign: "top",
    fontSize: "12.5px",
  };
  return (
    <div style={{ marginTop: "18px" }}>
      <h4
        style={{
          margin: "0 0 8px",
          fontSize: "13px",
          fontWeight: 700,
          color: "var(--text-strong)",
        }}
      >
        {m.values}
      </h4>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            minWidth: "620px",
          }}
        >
          <thead>
            <tr>
              {[
                m.valueColumns.measured,
                m.valueColumns.value,
                m.valueColumns.asReported,
                m.valueColumns.reference,
                m.valueColumns.status,
                m.valueColumns.change,
              ].map((h) => (
                <th
                  key={h}
                  scope="col"
                  style={{
                    ...colLabel,
                    textAlign: "left",
                    padding: "6px 10px",
                    borderBottom: "1px solid var(--border-subtle)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {series.values
              .slice()
              .reverse()
              .map((v) => {
                const replaced = v.superseded || v.inputReplaced;
                return (
                  <tr key={v.id}>
                    <td style={{ ...cell, fontFamily: "var(--font-mono)" }}>
                      {v.observedDay}
                    </td>
                    <td
                      style={{
                        ...cell,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: replaced
                          ? "var(--text-faint)"
                          : "var(--text-strong)",
                        textDecoration: replaced ? "line-through" : "none",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {valueText(v)}
                    </td>
                    <td style={{ ...cell, fontFamily: "var(--font-mono)" }}>
                      {v.originalUnit
                        ? `${v.originalValue} ${v.originalUnit}`
                        : v.originalValue}
                    </td>
                    <td style={{ ...cell, fontFamily: "var(--font-mono)" }}>
                      {v.referenceLow != null || v.referenceHigh != null
                        ? `${v.referenceLow ?? "—"}–${v.referenceHigh ?? "—"}`
                        : "—"}
                    </td>
                    <td style={cell}>
                      {status[v.status] ?? v.status}
                      {v.superseded && (
                        <span
                          style={{
                            display: "block",
                            fontSize: "11px",
                            color: "var(--text-muted)",
                          }}
                        >
                          {t.evidence.superseded}
                        </span>
                      )}
                      {v.inputReplaced && (
                        <span
                          style={{
                            display: "block",
                            fontSize: "11px",
                            color: "var(--text-muted)",
                          }}
                        >
                          {t.evidence.inputReplaced}
                        </span>
                      )}
                    </td>
                    <td style={cell}>
                      {v.standing ? <ChangeText v={v} t={t.evidence} /> : "—"}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
