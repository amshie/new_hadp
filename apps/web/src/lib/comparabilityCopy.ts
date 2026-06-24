// Comparability marker copy (ADR-0004 Slice 3, §9 non-merge).
//
// These strings describe the PROVENANCE of a longitudinal comparison — never the patient's state.
// They stay neutral and within the intended-use language boundary (see docs/FORBIDDEN_LANGUAGE and
// the project policy); none asserts anything clinical about the value. Initial locale is de-DE
// (CLAUDE.md); the EN variants are kept for localization-readiness. This file is the single home for
// the marker copy so it can be scanned by the forbidden-language guard
// (apps/api/tests/test_web_copy_language.py) — the gate ADR-0004 §0 names ("DE/EN labels through the
// language scan before any UI ships").

export interface ComparabilityNote {
  short: string; // terse cell label
  full: string; // full provenance sentence (title / screen-reader)
}

type Locale = "de" | "en";

// Keyed by the backend ComparabilityReason value. A note is shown ONLY for a withheld
// (not_comparable) delta; "comparable" and series-start (null) render no note.
const NOTES: Record<string, Record<Locale, ComparabilityNote>> = {
  context_differs: {
    de: {
      short: "Nicht direkt vergleichbar",
      full: "Nicht direkt vergleichbar — Messkontext unterschiedlich. Werte werden einzeln angezeigt.",
    },
    en: {
      short: "Not directly comparable",
      full: "Not directly comparable — measurement context differs. Values shown individually.",
    },
  },
  context_missing: {
    de: {
      short: "Verlaufsvergleich nicht möglich",
      full: "Verlaufsvergleich nicht möglich: Messkontext nicht dokumentiert. Werte werden einzeln angezeigt.",
    },
    en: {
      short: "Longitudinal comparison not available",
      full: "Longitudinal comparison not available: measurement context not documented. Values shown individually.",
    },
  },
  not_longitudinal: {
    de: {
      short: "Nicht im Verlauf vergleichbar",
      full: "Dieser Wert ist methodisch nicht im Verlauf vergleichbar. Werte werden einzeln angezeigt.",
    },
    en: {
      short: "Not longitudinally comparable",
      full: "This value is not designed for longitudinal comparison. Values shown individually.",
    },
  },
};

// Defensive fallback: state is not_comparable but the reason is absent (the API permits null).
const FALLBACK: Record<Locale, ComparabilityNote> = {
  de: {
    short: "Nicht direkt vergleichbar",
    full: "Nicht direkt vergleichbar. Werte werden einzeln angezeigt.",
  },
  en: {
    short: "Not directly comparable",
    full: "Not directly comparable. Values shown individually.",
  },
};

/**
 * The localized comparability note for a timeline point, or null when no note applies.
 * Returns a note ONLY when the delta was withheld (`comparability === "not_comparable"`); a
 * computed delta ("comparable") and a series-start point (null) both return null.
 */
export function comparabilityNote(
  comparability: string | null | undefined,
  reason: string | null | undefined,
  locale: Locale = "de",
): ComparabilityNote | null {
  if (comparability !== "not_comparable") return null;
  const entry = (reason != null && NOTES[reason]) || FALLBACK;
  return entry[locale];
}
