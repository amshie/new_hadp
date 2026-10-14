// A value the platform computed from other values of the record, by a versioned formula — no
// source reported it (ADR-0004 §8/§10; CLAUDE.md: "Distinguish measured, normalized, and
// derived values"). What it was computed from, as the record holds those values, so a page can
// say so wherever the value is shown and a computed value never reads as a measured one.
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/derivation.spec.ts).

import type { TimelinePoint } from "./api";

export interface DerivedInput {
  id: string;
  // The input's part in the formula ("total_cholesterol", "hdl").
  role: string;
  // The input as this record holds it — the number the platform holds and its unit, or the
  // source's writing; all null when the input is not among the record's values.
  name: string | null;
  value: string | null;
  unit: string | null;
}

export interface Derivation {
  // The formula and its version, as frozen on the value ("non_hdl_c.v1").
  formulaId: string | null;
  inputs: DerivedInput[];
}

export function derivationOf(
  p: TimelinePoint,
  byId: ReadonlyMap<string, TimelinePoint>,
): Derivation | null {
  if (p.derived !== true) return null;
  return {
    formulaId: p.formula_id ?? null,
    inputs: (p.derived_from ?? []).map((i) => {
      const input = byId.get(i.observation_id);
      const held = input?.value != null;
      return {
        id: i.observation_id,
        role: i.role,
        name: input?.original_name ?? null,
        value: input ? (held ? input.value : input.original_value) : null,
        unit: input
          ? ((held ? input.unit : input.original_unit) ?? null)
          : null,
      };
    }),
  };
}

// The inputs in a line of text ("Gesamtcholesterin 5.2 mmol/L und HDL 1.3 mmol/L"), or null
// when any of them is not among the record's values — the page then names none of them rather
// than some.
export function derivedInputsText(d: Derivation, and: string): string | null {
  if (d.inputs.length === 0 || d.inputs.some((i) => i.name == null))
    return null;
  const parts = d.inputs.map((i) =>
    [i.name, i.value, i.unit].filter((s) => s != null && s !== "").join(" "),
  );
  const last = parts.pop() ?? "";
  return parts.length === 0 ? last : `${parts.join(", ")} ${and} ${last}`;
}
