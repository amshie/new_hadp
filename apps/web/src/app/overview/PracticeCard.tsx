"use client";

import { fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { PreparationTime, Throughput } from "@/lib/api";
import { presentWeeks } from "@/lib/presenters/today";

import { duration, shortDay } from "./format";
import { Card, CardHead, KeyValue } from "./parts";

// The clinic's last 30 days, per calendar week (docs/notes/0015): report drafts created and
// reviews signed, from the timestamps the platform records anyway. For the owner, below it,
// the two numbers the pilot is judged by — kept apart, because they are two different
// measures: the measured turnaround (first draft to approval) and the clinic's own baseline.

const W = 560;
const H = 160;
const L = 34;
const R = 8;
const TOP = 22;
const BOT = 26;

export function PracticeCard({
  throughput,
  preparation,
}: {
  throughput: Throughput | null;
  preparation: PreparationTime | null;
}) {
  const { locale, t } = useI18n();
  const p = t.overview.practice;

  if (!throughput) {
    return (
      <Card labelledBy="ov-practice">
        <CardHead id="ov-practice" title={fill(p.title, { days: 30 })} />
        <p className="vb-ov-unavailable">{p.unavailable}</p>
      </Card>
    );
  }

  const weeks = presentWeeks(throughput);
  const first = throughput.buckets[0]?.date;
  const last = throughput.buckets[throughput.buckets.length - 1]?.date;
  const max = Math.max(1, ...weeks.map((w) => Math.max(w.created, w.signed)));
  const plotW = W - L - R;
  const plotH = H - TOP - BOT;
  const base = TOP + plotH;
  const slot = plotW / Math.max(1, weeks.length);
  const bar = Math.min(20, slot / 3);
  const y = (v: number) => base - (plotH * v) / max;
  const ticks = [0, Math.ceil(max / 2), max].filter(
    (v, i, all) => all.indexOf(v) === i,
  );

  const measured = preparation?.measured_last_30_days ?? null;
  const minimum = preparation?.minimum_reports ?? 0;

  return (
    <Card labelledBy="ov-practice">
      <CardHead
        id="ov-practice"
        title={fill(p.title, { days: throughput.days })}
        note={p.note}
        aside={
          first && last ? (
            <span className="vb-ov-eyebrow">
              {fill(p.range, {
                from: shortDay(first, locale),
                to: shortDay(last, locale),
              })}
            </span>
          ) : undefined
        }
      />
      <div className="vb-ov-body">
        <svg
          role="img"
          aria-label={p.chartLabel}
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ display: "block", maxWidth: `${W}px` }}
        >
          <g
            fontFamily="var(--font-mono)"
            fontSize="10"
            fill="var(--text-muted)"
          >
            {ticks.map((v) => (
              <g key={v}>
                <line
                  x1={L}
                  x2={W - R}
                  y1={y(v)}
                  y2={y(v)}
                  stroke={
                    v === 0 ? "var(--border-default)" : "var(--coverage-track)"
                  }
                />
                <text x={L - 6} y={y(v) + 3} textAnchor="end">
                  {v}
                </text>
              </g>
            ))}
            {weeks.map((w, i) => (
              <text
                key={`${w.year}-${w.week}`}
                x={L + slot * i + slot / 2}
                y={H - 8}
                textAnchor="middle"
              >
                {fill(p.week, { week: w.week })}
              </text>
            ))}
          </g>
          {weeks.map((w, i) => {
            const cx = L + slot * i + slot / 2;
            return (
              <g key={`${w.year}-${w.week}`}>
                <rect
                  x={cx - bar - 1}
                  y={y(w.created)}
                  width={bar}
                  height={base - y(w.created)}
                  rx={3}
                  fill="var(--border-default)"
                />
                <rect
                  x={cx + 1}
                  y={y(w.signed)}
                  width={bar}
                  height={base - y(w.signed)}
                  rx={3}
                  fill="var(--vital-500)"
                />
                <g
                  fontFamily="var(--font-mono)"
                  fontSize="10.5"
                  fontWeight={600}
                  fill="var(--text-strong)"
                  textAnchor="middle"
                >
                  {w.created > 0 && (
                    <text x={cx - bar / 2 - 1} y={y(w.created) - 5}>
                      {w.created}
                    </text>
                  )}
                  {w.signed > 0 && (
                    <text x={cx + bar / 2 + 1} y={y(w.signed) - 5}>
                      {w.signed}
                    </text>
                  )}
                </g>
              </g>
            );
          })}
        </svg>
        <div className="vb-ov-legend">
          <span>
            <i style={{ background: "var(--border-default)" }} />
            {p.created}
          </span>
          <span>
            <i style={{ background: "var(--vital-500)" }} />
            {p.signed}
          </span>
        </div>
        <details className="vb-ov-details">
          <summary>{p.showTable}</summary>
          <div style={{ overflowX: "auto" }}>
            <table className="vb-ov-table">
              <thead>
                <tr>
                  <th scope="col">{p.columns.week}</th>
                  <th scope="col">{p.columns.days}</th>
                  <th scope="col">{p.created}</th>
                  <th scope="col">{p.signed}</th>
                  <th scope="col">{p.released}</th>
                </tr>
              </thead>
              <tbody>
                {weeks.map((w) => (
                  <tr key={`${w.year}-${w.week}`}>
                    <th scope="row">{fill(p.week, { week: w.week })}</th>
                    <td>
                      {fill(p.range, {
                        from: shortDay(w.from, locale),
                        to: shortDay(w.to, locale),
                      })}
                    </td>
                    <td>{w.created}</td>
                    <td>{w.signed}</td>
                    <td>{w.released}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        {preparation && (
          <div className="vb-ov-kvblock">
            <KeyValue
              label={p.median}
              note={p.medianNote}
              value={
                measured?.median_seconds != null
                  ? duration(
                      measured.median_seconds,
                      locale,
                      t.overview.duration,
                    )
                  : fill(p.tooFew, {
                      minimum,
                      n: measured?.reports ?? 0,
                    })
              }
            />
            <KeyValue
              label={p.baseline}
              note={p.baselineNote}
              value={
                preparation.baseline
                  ? fill(p.baselineValue, {
                      n: preparation.baseline.median_minutes,
                    })
                  : p.noBaseline
              }
            />
            <p className="vb-ov-foot">{p.foot}</p>
          </div>
        )}
      </div>
    </Card>
  );
}
