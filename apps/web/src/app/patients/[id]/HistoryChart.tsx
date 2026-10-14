"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent,
  type ReactNode,
} from "react";

import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { lageLabel } from "@/lib/lageCopy";
import type {
  MarkerSeries,
  TimeAxis,
  ValueView,
} from "@/lib/presenters/domainOverview";
import {
  historyGeometry,
  type HistoryGeometry,
  type HistoryPoint,
} from "@/lib/presenters/history";

import { GERMAN } from "./MarkerParts";

// A marker's history (docs/notes/0014, part 2): a sparkline in the domain list and a chart in
// the marker dialog, both on the page's one calendar axis. What is drawn, joined and banded is
// decided in lib/presenters/history.ts — this file only paints it. Recorded values only: no
// trend line, no smoothing, no forecast.

const MONO = "IBM Plex Mono, ui-monospace, monospace";

function chartBox(width: number) {
  return {
    width,
    height: width < 520 ? 210 : 240,
    padLeft: 46,
    padRight: 18,
    padTop: 22,
    padBottom: 36,
  };
}

function valueText(v: ValueView): string {
  const n = v.value ?? v.originalValue;
  const unit = v.value != null ? v.unit : v.originalUnit;
  return unit ? `${n} ${unit}` : n;
}

function Marks({
  g,
  small,
  active,
}: {
  g: HistoryGeometry;
  small: boolean;
  active: number | null;
}) {
  const r = small ? 2.2 : 4.5;
  return (
    <>
      {g.bands.map((b, i) => (
        <g key={`band-${i}`}>
          <rect
            x={b.x0}
            y={b.top}
            width={Math.max(1, b.x1 - b.x0)}
            height={Math.max(1, b.bottom - b.top)}
            fill="var(--brand-soft)"
          />
          {!small && !b.openTop && (
            <line
              x1={b.x0}
              x2={b.x1}
              y1={b.top}
              y2={b.top}
              stroke="var(--brand-border)"
              strokeWidth={1}
            />
          )}
          {!small && !b.openBottom && (
            <line
              x1={b.x0}
              x2={b.x1}
              y1={b.bottom}
              y2={b.bottom}
              stroke="var(--brand-border)"
              strokeWidth={1}
            />
          )}
        </g>
      ))}
      {g.segments.map((s) => (
        <line
          key={`${s.fromId}-${s.toId}`}
          x1={s.x1}
          y1={s.y1}
          x2={s.x2}
          y2={s.y2}
          stroke="var(--brand)"
          strokeWidth={small ? 1.5 : 2}
          strokeLinecap="round"
        />
      ))}
      {g.points.map((p) => {
        const on = active != null && Math.abs(p.x - active) < 0.5;
        if (p.kind === "replaced") {
          const s = small ? 2.5 : 4.5;
          return (
            <path
              key={p.value.id}
              d={`M${p.x - s} ${p.y - s}L${p.x + s} ${p.y + s}M${p.x + s} ${p.y - s}L${p.x - s} ${p.y + s}`}
              stroke="var(--text-faint)"
              strokeWidth={small ? 1.3 : 1.8}
              strokeLinecap="round"
              fill="none"
            />
          );
        }
        if (p.kind === "pending") {
          return (
            <circle
              key={p.value.id}
              cx={p.x}
              cy={p.y}
              r={r}
              fill="var(--surface-card)"
              stroke="var(--text-muted)"
              strokeWidth={small ? 1.3 : 2}
            />
          );
        }
        return (
          <g key={p.value.id}>
            {p.outside && !small && (
              <circle
                cx={p.x}
                cy={p.y}
                r={8}
                fill="none"
                stroke="var(--text-strong)"
                strokeWidth={1.3}
              />
            )}
            <circle
              cx={p.x}
              cy={p.y}
              r={on ? r + 1.5 : r}
              fill="var(--brand)"
              stroke="var(--surface-card)"
              strokeWidth={small ? 1 : 2}
            />
          </g>
        );
      })}
    </>
  );
}

const SPARK = {
  width: 132,
  height: 30,
  padLeft: 3,
  padRight: 3,
  padTop: 4,
  padBottom: 4,
};

// Decorative: the row beside it carries the latest value in text.
export function Sparkline({
  series,
  axis,
}: {
  series: MarkerSeries;
  axis: TimeAxis;
}) {
  const g = useMemo(
    () => historyGeometry(series, axis, SPARK, 2),
    [series, axis],
  );
  return (
    <svg
      width={SPARK.width}
      height={SPARK.height}
      viewBox={`0 0 ${SPARK.width} ${SPARK.height}`}
      aria-hidden="true"
      focusable="false"
      style={{ display: "block" }}
    >
      <line
        x1={g.todayX}
        x2={g.todayX}
        y1={1}
        y2={SPARK.height - 1}
        stroke="var(--border-default)"
        strokeWidth={1}
      />
      <Marks g={g} small active={null} />
    </svg>
  );
}

function useWidth(fallback: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const read = () => setWidth(Math.max(280, Math.floor(el.clientWidth)));
    read();
    const observer = new ResizeObserver(read);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

export function HistoryChart({
  series,
  axis,
}: {
  series: MarkerSeries;
  axis: TimeAxis;
}) {
  const { locale, t: all } = useI18n();
  const t = all.patientPage.history;
  const status: Record<string, string> = all.patientPage.valueStatus;
  const { ref, width } = useWidth(640);
  const narrow = width < 520;
  const box = chartBox(width);
  const g = useMemo(
    () => historyGeometry(series, axis, chartBox(width), width < 520 ? 3 : 4),
    [series, axis, width],
  );
  const month = useMemo(
    () =>
      new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "de-DE", {
        month: "short",
        timeZone: "UTC",
      }),
    [locale],
  );

  // The dates that carry a drawn value, left to right: what the crosshair snaps to.
  const dates = useMemo(() => {
    const xs = Array.from(new Set(g.points.map((p) => p.x)));
    return xs.sort((a, b) => a - b);
  }, [g]);
  const [active, setActive] = useState<number | null>(null);
  const activeX = active != null ? (dates[active] ?? null) : null;
  const at: HistoryPoint[] =
    activeX == null
      ? []
      : g.points.filter((p) => Math.abs(p.x - activeX) < 0.5);

  const standing = series.values.filter((v) => v.standing);
  const replaced = series.values.filter(
    (v) => v.superseded || v.inputReplaced,
  ).length;
  const summary = [
    standing.length === 0
      ? fill(t.summary.none, { name: series.name })
      : standing.length === 1
        ? fill(t.summary.one, {
            name: series.name,
            to: standing[0]!.observedDay,
            value: valueText(standing[0]!),
          })
        : fill(t.summary.other, {
            name: series.name,
            n: standing.length,
            from: standing[0]!.observedDay,
            to: standing[standing.length - 1]!.observedDay,
            value: valueText(series.latest ?? standing[standing.length - 1]!),
          }),
    series.pending > 0 ? byCount(t.pending, series.pending) : null,
    replaced > 0 ? byCount(t.replaced, replaced) : null,
    g.notDrawn > 0 ? byCount(t.notDrawn, g.notDrawn) : null,
  ]
    .filter(Boolean)
    .join(" ");

  const onMove = (e: PointerEvent<SVGRectElement>) => {
    const bounds = e.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!bounds || dates.length === 0) return;
    const px = e.clientX - bounds.left;
    let best = 0;
    dates.forEach((x, i) => {
      if (Math.abs(x - px) < Math.abs(dates[best]! - px)) best = i;
    });
    setActive(best);
  };

  const hasBand = g.bands.length > 0;
  const hasOutside = g.points.some((p) => p.outside);
  const hasPending = g.points.some((p) => p.kind === "pending");
  const hasReplaced = g.points.some((p) => p.kind === "replaced");
  const summaryId = `vb-history-${series.kpiCode.replace(/\W/g, "-")}`;
  const tipLeft =
    activeX == null ? 0 : activeX + 260 > width ? activeX - 262 : activeX + 14;

  const legendItem = (icon: ReactNode, label: string) => (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
      <svg width={20} height={12} aria-hidden="true" focusable="false">
        {icon}
      </svg>
      {label}
    </span>
  );

  return (
    <div style={{ marginTop: "18px" }}>
      <h4
        style={{
          margin: "0 0 6px",
          fontSize: "13px",
          fontWeight: 700,
          color: "var(--text-strong)",
        }}
      >
        {t.title}
      </h4>
      <p
        id={summaryId}
        style={{
          margin: "0 0 10px",
          fontSize: "12.5px",
          lineHeight: 1.5,
          color: "var(--text-body)",
        }}
      >
        {summary}
      </p>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "4px 16px",
          fontSize: "11.5px",
          color: "var(--text-body)",
          marginBottom: "6px",
        }}
      >
        {legendItem(
          <>
            <line
              x1={1}
              x2={19}
              y1={6}
              y2={6}
              stroke="var(--brand)"
              strokeWidth={2}
            />
            <circle cx={10} cy={6} r={3.5} fill="var(--brand)" />
          </>,
          `${t.legend.value} · ${t.legend.joined}`,
        )}
        {hasBand &&
          legendItem(
            <rect
              x={1}
              y={1}
              width={18}
              height={10}
              fill="var(--brand-soft)"
              stroke="var(--brand-border)"
            />,
            t.legend.interval,
          )}
        {hasOutside &&
          legendItem(
            <>
              <circle
                cx={10}
                cy={6}
                r={5}
                fill="none"
                stroke="var(--text-strong)"
                strokeWidth={1.2}
              />
              <circle cx={10} cy={6} r={2.5} fill="var(--brand)" />
            </>,
            t.legend.outside,
          )}
        {hasPending &&
          legendItem(
            <circle
              cx={10}
              cy={6}
              r={4}
              fill="var(--surface-card)"
              stroke="var(--text-muted)"
              strokeWidth={2}
            />,
            t.legend.pending,
          )}
        {hasReplaced &&
          legendItem(
            <path
              d="M6 2L14 10M14 2L6 10"
              stroke="var(--text-faint)"
              strokeWidth={1.6}
              strokeLinecap="round"
            />,
            t.legend.replaced,
          )}
      </div>
      <div ref={ref} style={{ position: "relative", width: "100%" }}>
        {/* An image with its summary: every value it draws is in the table beneath, so the
            hover readout is a convenience, never the only way to a value. */}
        <svg
          width={width}
          height={box.height}
          viewBox={`0 0 ${width} ${box.height}`}
          role="img"
          aria-label={fill(t.chartLabel, { name: series.name })}
          aria-describedby={summaryId}
          focusable="false"
          style={{ display: "block" }}
        >
          {g.yTicks.map((tick) => (
            <g key={tick.at}>
              <line
                x1={g.plotLeft}
                x2={g.plotRight}
                y1={tick.pos}
                y2={tick.pos}
                stroke="var(--border-subtle)"
                strokeWidth={1}
              />
              <text
                x={g.plotLeft - 8}
                y={tick.pos + 3.5}
                textAnchor="end"
                fill="var(--text-muted)"
                fontSize={10.5}
                fontFamily={MONO}
              >
                {tick.label}
              </text>
            </g>
          ))}
          <text
            x={g.plotLeft - 8}
            y={11}
            textAnchor="end"
            fill="var(--text-faint)"
            fontSize={10}
            fontFamily={MONO}
          >
            {series.latest?.unit ?? series.values[0]?.unit ?? ""}
          </text>
          <line
            x1={g.plotLeft}
            x2={g.plotRight}
            y1={g.plotBottom}
            y2={g.plotBottom}
            stroke="var(--border-default)"
            strokeWidth={1}
          />
          {g.xTicks.map((tick) => {
            const labelled = !narrow || tick.month % 6 === 0;
            return (
              <g key={tick.at}>
                <line
                  x1={tick.pos}
                  x2={tick.pos}
                  y1={g.plotBottom}
                  y2={g.plotBottom + 4}
                  stroke="var(--border-default)"
                  strokeWidth={1}
                />
                {labelled && (
                  <text
                    x={tick.pos}
                    y={g.plotBottom + 15}
                    textAnchor="middle"
                    fill="var(--text-muted)"
                    fontSize={10}
                    fontFamily={MONO}
                  >
                    {month.format(new Date(tick.at))}
                  </text>
                )}
                {tick.year != null && (
                  <text
                    x={tick.pos}
                    y={g.plotBottom + 28}
                    textAnchor="middle"
                    fill="var(--text-strong)"
                    fontSize={10}
                    fontWeight={600}
                    fontFamily={MONO}
                  >
                    {tick.year}
                  </text>
                )}
              </g>
            );
          })}
          <line
            x1={g.todayX}
            x2={g.todayX}
            y1={g.plotTop - 6}
            y2={g.plotBottom}
            stroke="var(--border-default)"
            strokeWidth={1}
          />
          <text
            x={g.todayX}
            y={g.plotTop - 10}
            textAnchor="end"
            fill="var(--text-faint)"
            fontSize={10}
            fontFamily={MONO}
          >
            {t.today}
          </text>
          <Marks g={g} small={false} active={activeX} />
          {activeX != null && (
            <line
              x1={activeX}
              x2={activeX}
              y1={g.plotTop}
              y2={g.plotBottom}
              stroke="var(--text-muted)"
              strokeWidth={1}
            />
          )}
          <rect
            x={g.plotLeft}
            y={0}
            width={Math.max(0, g.plotRight - g.plotLeft)}
            height={box.height}
            fill="transparent"
            onPointerMove={onMove}
            onPointerLeave={() => setActive(null)}
          />
        </svg>
        {at.length > 0 && activeX != null && (
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: `${g.plotTop}px`,
              left: `${Math.max(0, tipLeft)}px`,
              width: "248px",
              pointerEvents: "none",
              background: "var(--surface-card)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-md)",
              padding: "9px 11px",
              fontSize: "11.5px",
              color: "var(--text-body)",
              zIndex: 2,
            }}
          >
            <div
              style={{
                fontFamily: MONO,
                fontSize: "11px",
                color: "var(--text-muted)",
                marginBottom: "4px",
              }}
            >
              {at[0]!.value.observedDay}
            </div>
            {at.map((p) => (
              <div
                key={p.value.id}
                style={{
                  borderTop: "1px solid var(--border-subtle)",
                  padding: "5px 0 2px",
                }}
              >
                <div
                  style={{
                    fontFamily: MONO,
                    fontWeight: 600,
                    fontSize: "13px",
                    color:
                      p.kind === "replaced"
                        ? "var(--text-faint)"
                        : "var(--text-strong)",
                    textDecoration:
                      p.kind === "replaced" ? "line-through" : "none",
                  }}
                >
                  {valueText(p.value)}
                </div>
                <div>
                  {p.kind === "replaced"
                    ? all.patientPage.evidence.superseded
                    : (status[p.value.status] ?? p.value.status)}
                </div>
                {p.kind === "standing" && (
                  <div lang={GERMAN}>{lageLabel(p.value.position).label}</div>
                )}
                {(p.value.referenceLow != null ||
                  p.value.referenceHigh != null) && (
                  <div style={{ fontFamily: MONO, color: "var(--text-muted)" }}>
                    {`${p.value.referenceLow ?? "—"}–${p.value.referenceHigh ?? "—"}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <p
        style={{
          margin: "8px 0 0",
          fontSize: "11.5px",
          lineHeight: 1.5,
          color: "var(--text-faint)",
        }}
      >
        {t.foot}
      </p>
    </div>
  );
}
