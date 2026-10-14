// The one figure the pilot is judged by (CLAUDE.md, "Metrics and instrumentation"; docs/notes/
// 0025): how far the clinic's latest stated preparation time per appointment lies from the
// baseline it stated before the platform, as a percentage. Both numbers are the clinic's own
// statements; the platform computes the difference and nothing else — it does not mix in
// the turnaround it measures, which is a different quantity.
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/patient-tabs.spec.ts).

import type { PreparationTime } from "../api";

// The pilot's success criterion: at least this much less than the baseline.
export const PILOT_TARGET_PERCENT = 50;

export interface StatedChange {
  baselineMinutes: number;
  followUpMinutes: number;
  // Minutes and percent, negative when the follow-up lies below the baseline. The percent is
  // rounded to a whole number; null when the baseline is 0, as nothing can be measured
  // against it.
  minutes: number;
  percent: number | null;
  // Whether the pilot's criterion is met by the stated numbers.
  targetMet: boolean;
}

export function statedChange(
  metric: Pick<PreparationTime, "baseline" | "latest_follow_up">,
): StatedChange | null {
  const base = metric.baseline?.median_minutes;
  const follow = metric.latest_follow_up?.median_minutes;
  if (base == null || follow == null) return null;
  const minutes = follow - base;
  const percent = base > 0 ? Math.round((minutes / base) * 100) : null;
  return {
    baselineMinutes: base,
    followUpMinutes: follow,
    minutes,
    percent,
    targetMet: percent != null && percent <= -PILOT_TARGET_PERCENT,
  };
}

// "−33 %", "+10 %", "±0 %": a sign on every figure, the minus a real minus.
export function percentText(percent: number): string {
  const sign = percent < 0 ? "−" : percent > 0 ? "+" : "±";
  return `${sign}${Math.abs(percent)}\u00a0%`;
}
