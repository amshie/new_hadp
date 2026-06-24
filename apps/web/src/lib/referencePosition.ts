// TypeScript twin of `position_vs_source_interval`
// (apps/api/src/hadp_api/modules/observations/reference_position.py). It states only a
// deterministic FACT about the value versus the LAB-provided interval — never an introduced
// "optimal"/normal bound, never a verdict. Keep this truth table in sync with the Python twin;
// the authoritative cases live in apps/api/tests/test_reference_position.py.
//
// When the 0009 out_of_source_interval rule lands, this presenter-side computation is replaced by
// a read of the recorded RuleEvaluation — same positions, same copy keys, so it is a data-source
// swap, not a rewrite.

export type ReferencePosition =
  | "above"
  | "below"
  | "within"
  | "no_reference"
  | "not_evaluable";

export interface PositionBar {
  hasScale: boolean;
  bandStartPct: number;
  bandEndPct: number;
  dotPct: number | null;
}

function num(v: string | null | undefined): number | null {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Position of `value` relative to the lab interval `[low, high]`. Mirrors the Python twin. */
export function referencePosition(
  value: string | null | undefined,
  referenceLow: string | null | undefined,
  referenceHigh: string | null | undefined,
): ReferencePosition {
  const v = num(value);
  const lo = num(referenceLow);
  const hi = num(referenceHigh);
  if (v == null) return "not_evaluable";
  if (lo == null && hi == null) return "no_reference";
  if (hi != null && v > hi) return "above";
  if (lo != null && v < lo) return "below";
  if (lo != null && hi != null) return "within";
  return "not_evaluable";
}

// Cosmetic position bar derived ONLY from the lab bounds — never from the value's magnitude, so it
// can never imply a target the lab did not state. Padding is a fixed fraction of the interval span;
// a non-negative lower bound keeps the band flush-left (no impossible sub-zero space). The dot
// clamps to [0,100] so a far-outside value sits at the gutter rather than escaping the track. The
// bar is decorative-supportive: the pill + screen-reader sentence carry the meaning.
export function referenceBar(
  value: string | null | undefined,
  referenceLow: string | null | undefined,
  referenceHigh: string | null | undefined,
): PositionBar {
  const empty: PositionBar = {
    hasScale: false,
    bandStartPct: 0,
    bandEndPct: 0,
    dotPct: null,
  };
  const v = num(value);
  const lo = num(referenceLow);
  const hi = num(referenceHigh);
  // A two-sided, non-degenerate interval is required to draw a meaningful band.
  if (lo == null || hi == null || hi <= lo) return empty;

  const span = hi - lo;
  const pad = span * 0.4;
  let scaleMin = lo - pad;
  if (lo >= 0 && scaleMin < 0) scaleMin = 0;
  const scaleMax = hi + pad;
  const range = scaleMax - scaleMin;
  const pct = (x: number): number => {
    const p = ((x - scaleMin) / range) * 100;
    return p < 0 ? 0 : p > 100 ? 100 : p;
  };

  return {
    hasScale: true,
    bandStartPct: pct(lo),
    bandEndPct: pct(hi),
    dotPct: v == null ? null : pct(v),
  };
}
