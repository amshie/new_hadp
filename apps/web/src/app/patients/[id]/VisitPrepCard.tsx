"use client";

import Link from "next/link";
import { useMemo, type ReactNode } from "react";

import { EmptyState } from "@/components/vitabahn/EmptyState";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { lageLabel } from "@/lib/lageCopy";
import type {
  DomainOverview,
  MarkerSeries,
} from "@/lib/presenters/domainOverview";
import type { VisitPrep } from "@/lib/presenters/visitPrep";

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

// The facts since the latest interpretation run, one line each, every line leading to its
// value (docs/notes/0022). On the patient page a marker's line opens its history; on the
// page of its own it leads back to the marker's domain. Nothing here is a verdict: the
// position names are the laboratory interval's sides, and the only verdicts named are the
// clinician's own, by their absence.
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

  const groups: ReactNode[] = [];
  if (prep.run && prep.newValues.length > 0) {
    groups.push(
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
                {fill(t.line.measured, { date: v.observedDay })}
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
    groups.push(
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
  if (prep.stale.length > 0) {
    groups.push(
      group(
        "stale",
        fill(byCount(t.groups.stale, prep.stale.length), {
          days: prep.staleAfterDays,
        }),
        null,
        <ul className="vb-prep-list">
          {byAxis(prep.stale).map(([axis, items]) => (
            <li key={axis}>
              <span className="vb-prep-domain" lang={GERMAN}>
                {axisLabel(axis)}
              </span>
              {items.map((s, i) => (
                <span key={s.latestId} className="vb-prep-item">
                  {marker(s.code, s.name, s.axis)}
                  <span className="vb-prep-meta"> ({s.observedDay})</span>
                  {i < items.length - 1 ? "," : ""}
                </span>
              ))}
            </li>
          ))}
        </ul>,
      ),
    );
  }
  if (prep.missing.length > 0) {
    groups.push(
      group(
        "missing",
        byCount(t.groups.missing, prep.missing.length),
        null,
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
        </ul>,
      ),
    );
  }
  if (prep.pending > 0) {
    groups.push(
      group(
        "pending",
        byCount(t.groups.pending, prep.pending),
        null,
        <p className="vb-prep-meta" style={{ margin: "0 0 6px" }}>
          {t.line.pendingNote}{" "}
          <Link href="/review-queue">{t.line.toQueue}</Link>
        </p>,
      ),
    );
  }
  if (prep.unassigned > 0) {
    groups.push(
      group(
        "unassigned",
        byCount(t.groups.unassigned, prep.unassigned),
        null,
        <p className="vb-prep-meta" style={{ margin: "0 0 6px" }}>
          {t.line.unassignedNote}
        </p>,
      ),
    );
  }
  if (prep.run && prep.domainsWithoutVerdict.length > 0) {
    groups.push(
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
    groups.push(
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
      {groups.length > 0 ? (
        groups
      ) : (
        <div className="vb-prep-quiet">
          <EmptyState quiet style={{ padding: 0 }}>
            {prep.run ? t.quiet : t.quietNoRun}
          </EmptyState>
        </div>
      )}
    </section>
  );
}
