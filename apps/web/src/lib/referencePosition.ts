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
  midPct: number; // band midpoint — the reference tick + "Referenz x–y" label sit here
  dotPct: number | null;
  scaleMax: number; // right-hand scale-end value (left end is always 0)
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

// Position bar geometry (the Claude Design "Lage zur Referenz" comp). Scale is [0, scaleMax] —
// natural for lab values (≥ 0). scaleMax fits the larger of the upper reference bound and the value
// (+ a little headroom) so the value dot is always on-scale and "how far outside" stays readable.
// The reference BAND reflects ONLY the lab-provided interval — never an introduced "optimal"/normal
// bound, never a clinical target; the axis extent is a cosmetic choice, not a bound. The bar is
// decorative: the pill + screen-reader sentence carry the meaning (never colour alone).
export function referenceBar(
  value: string | null | undefined,
  referenceLow: string | null | undefined,
  referenceHigh: string | null | undefined,
): PositionBar {
  const empty: PositionBar = {
    hasScale: false,
    bandStartPct: 0,
    bandEndPct: 0,
    midPct: 0,
    dotPct: null,
    scaleMax: 0,
  };
  const v = num(value);
  const lo = num(referenceLow);
  const hi = num(referenceHigh);
  // A two-sided, non-degenerate interval is required to draw a meaningful band.
  if (lo == null || hi == null || hi <= lo) return empty;

  const top = Math.max(hi, v ?? hi);
  const scaleMax = top * 1.07; // headroom so the dot/end never sits flush against the edge
  const pct = (x: number): number => {
    const p = (x / scaleMax) * 100;
    return p < 0 ? 0 : p > 100 ? 100 : p;
  };

  return {
    hasScale: true,
    bandStartPct: pct(lo),
    bandEndPct: pct(hi),
    midPct: pct((lo + hi) / 2),
    dotPct: v == null ? null : pct(v),
    scaleMax,
  };
}
