// The geometry of a marker's history (docs/notes/0014, part 2): where each recorded value, its
// laboratory's interval and the lines between comparable values go on a chart. Drawing only:
//
// - A line joins two values exactly where the API computed a change between them
//   (`previous_observation_id` with a `delta_vs_previous`). The chart decides no comparability
//   of its own, and draws no trend, smoothing or forecast.
// - The source reference interval belongs to each value: the band steps where the laboratory
//   changes, and a one-sided interval stays open on its open side. No other range is drawn.
// - A value awaiting review is drawn hollow, a replaced one crossed out; neither is joined.
//   A rejected value, and a result that is no number, are not drawn (the table lists them).
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/history.spec.ts).

import type { MarkerSeries, TimeAxis, ValueView } from "./domainOverview";

export interface Box {
  width: number;
  height: number;
  padLeft: number;
  padRight: number;
  padTop: number;
  padBottom: number;
}

export type PointKind = "standing" | "pending" | "replaced";

export interface HistoryPoint {
  value: ValueView;
  x: number;
  y: number;
  kind: PointKind;
  outside: boolean;
}

export interface HistorySegment {
  fromId: string;
  toId: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface HistoryBand {
  x0: number;
  x1: number;
  // Top and bottom in pixels; an open side reaches the plot's edge and has no edge line.
  top: number;
  bottom: number;
  openTop: boolean;
  openBottom: boolean;
}

export interface Tick {
  at: number;
  pos: number;
  label: string;
}

export interface HistoryGeometry {
  points: HistoryPoint[];
  segments: HistorySegment[];
  bands: HistoryBand[];
  yTicks: Tick[];
  // The first day of each quarter (or of each year, on a long axis); `year` on a January.
  xTicks: { at: number; pos: number; month: number; year: number | null }[];
  todayX: number;
  plotTop: number;
  plotBottom: number;
  plotLeft: number;
  plotRight: number;
  // Values not drawn: rejected, or no one number the platform reads.
  notDrawn: number;
}

function num(v: string | null): number | null {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function kindOf(v: ValueView): PointKind {
  if (v.standing) return "standing";
  if (v.status === "pending") return "pending";
  return "replaced";
}

// Round tick values (1, 2 or 5 times a power of ten) covering [lo, hi].
export function niceTicks(lo: number, hi: number, count: number): number[] {
  if (!(hi > lo)) return [lo];
  const raw = (hi - lo) / Math.max(1, count);
  const power = Math.pow(10, Math.floor(Math.log10(raw)));
  const unit = raw / power;
  const step =
    (unit >= 7.5 ? 10 : unit >= 3.5 ? 5 : unit >= 1.5 ? 2 : 1) * power;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) {
    out.push(Number(v.toFixed(10)));
  }
  return out;
}

// Enough decimals to tell neighbouring ticks apart, and no more.
function tickLabel(value: number, ticks: number[]): string {
  const step = ticks.length > 1 ? Math.abs(ticks[1]! - ticks[0]!) : 1;
  const decimals = step >= 1 ? 0 : Math.min(6, Math.ceil(-Math.log10(step)));
  return value.toFixed(decimals);
}

export function historyGeometry(
  series: MarkerSeries,
  axis: TimeAxis,
  box: Box,
  yTickCount = 4,
): HistoryGeometry {
  const plotLeft = box.padLeft;
  const plotRight = box.width - box.padRight;
  const plotTop = box.padTop;
  const plotBottom = box.height - box.padBottom;
  const span = Math.max(1, axis.end - axis.start);
  const xOf = (t: number) =>
    plotLeft + ((t - axis.start) / span) * (plotRight - plotLeft);

  const drawable = series.values.filter(
    (v) => v.status !== "rejected" && num(v.value) != null,
  );
  const notDrawn = series.values.length - drawable.length;

  // The value scale covers every drawn value and the bounds of the intervals drawn.
  const scale: number[] = [];
  for (const v of drawable) {
    scale.push(num(v.value)!);
    if (kindOf(v) !== "replaced") {
      const lo = num(v.referenceLow);
      const hi = num(v.referenceHigh);
      if (lo != null) scale.push(lo);
      if (hi != null) scale.push(hi);
    }
  }
  let lo = scale.length ? Math.min(...scale) : 0;
  let hi = scale.length ? Math.max(...scale) : 1;
  if (lo === hi) {
    const pad = Math.abs(lo) * 0.1 || 1;
    lo -= pad;
    hi += pad;
  }
  const pad = (hi - lo) * 0.12;
  const allNonNegative = scale.every((v) => v >= 0);
  lo = allNonNegative ? Math.max(0, lo - pad) : lo - pad;
  hi += pad;
  const ticks = niceTicks(lo, hi, yTickCount);
  lo = Math.min(lo, ticks[0]!);
  hi = Math.max(hi, ticks[ticks.length - 1]!);
  const yOf = (v: number) =>
    plotBottom - ((v - lo) / (hi - lo)) * (plotBottom - plotTop);

  const points: HistoryPoint[] = drawable.map((v) => ({
    value: v,
    x: xOf(v.observedMs),
    y: yOf(num(v.value)!),
    kind: kindOf(v),
    outside: v.standing && (v.position === "above" || v.position === "below"),
  }));
  const byId = new Map(points.map((p) => [p.value.id, p]));

  // A line exactly where the API computed a change.
  const segments: HistorySegment[] = [];
  for (const p of points) {
    if (p.kind !== "standing" || p.value.delta == null) continue;
    const prev = p.value.previousId ? byId.get(p.value.previousId) : undefined;
    if (!prev || prev.kind !== "standing") continue;
    segments.push({
      fromId: prev.value.id,
      toId: p.value.id,
      x1: prev.x,
      y1: prev.y,
      x2: p.x,
      y2: p.y,
    });
  }

  // The interval of each value that has one, stepped from midpoint to midpoint.
  const banded = points
    .filter(
      (p) =>
        p.kind !== "replaced" &&
        (num(p.value.referenceLow) != null ||
          num(p.value.referenceHigh) != null),
    )
    .sort((a, b) => a.x - b.x);
  const edge = Math.max(4, Math.min(14, (plotRight - plotLeft) * 0.02));
  const bands: HistoryBand[] = banded.map((p, i) => {
    const prev = banded[i - 1];
    const next = banded[i + 1];
    const x0 = prev ? (prev.x + p.x) / 2 : Math.max(plotLeft, p.x - edge);
    const x1 = next ? (next.x + p.x) / 2 : Math.min(plotRight, p.x + edge);
    const low = num(p.value.referenceLow);
    const high = num(p.value.referenceHigh);
    return {
      x0,
      x1,
      top: high != null ? yOf(high) : plotTop,
      bottom: low != null ? yOf(low) : plotBottom,
      openTop: high == null,
      openBottom: low == null,
    };
  });

  // Quarters on an axis up to four years long, years beyond that.
  const first = new Date(axis.start);
  const yearly = span > 4 * 365.25 * 86_400_000;
  const xTicks: HistoryGeometry["xTicks"] = [];
  for (
    let y = first.getUTCFullYear(), m = 0;
    Date.UTC(y, m, 1) <= axis.end;
    m += yearly ? 12 : 3
  ) {
    if (m >= 12) {
      y += Math.floor(m / 12);
      m %= 12;
    }
    const at = Date.UTC(y, m, 1);
    if (at < axis.start) continue;
    xTicks.push({ at, pos: xOf(at), month: m, year: m === 0 ? y : null });
  }

  return {
    points,
    segments,
    bands,
    yTicks: ticks.map((v) => ({
      at: v,
      pos: yOf(v),
      label: tickLabel(v, ticks),
    })),
    xTicks,
    todayX: xOf(axis.end),
    plotTop,
    plotBottom,
    plotLeft,
    plotRight,
    notDrawn,
  };
}
