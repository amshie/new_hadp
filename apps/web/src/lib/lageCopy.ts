// "Lage zum Referenzintervall" copy (docs/notes/0009 out_of_source_interval visualization).
//
// These strings describe the PROVENANCE of a value's position relative to the LAB-provided
// reference interval — never the patient's state. They stay strictly positional ("über/unter
// Referenz", "im Intervall") and never assert a clinical verdict: no "normal"/"abnormal"/"optimal",
// no "Hoch"/"Niedrig". Initial locale is de-DE (CLAUDE.md); EN is kept for localization-readiness.
// This is the single scanned home for the copy, covered by apps/api/tests/test_web_copy_language.py.
//
// Keys mirror the backend ReferencePosition (and the planned RuleResultReason enum), so when the
// 0009 rules engine lands the UI sources the label from a recorded rule-evaluation with no rewrite.

import type { ReferencePosition } from "@/lib/referencePosition";

type Locale = "de" | "en";

export interface LageLabel {
  glyph: string; // ↑ ↓ – ⊘ — paired with the word; meaning is never carried by colour alone
  label: string; // terse pill text
  badge: string; // .badge variant — calm, non-alarm (never danger/warning)
  sentence: string; // clause for the full screen-reader / title sentence
}

const LABELS: Record<ReferencePosition, Record<Locale, LageLabel>> = {
  above: {
    de: {
      glyph: "↑",
      label: "Über Referenz",
      badge: "badge-info",
      sentence: "über dem Quellreferenzintervall",
    },
    en: {
      glyph: "↑",
      label: "Above reference",
      badge: "badge-info",
      sentence: "above the source reference interval",
    },
  },
  below: {
    de: {
      glyph: "↓",
      label: "Unter Referenz",
      badge: "badge-info",
      sentence: "unter dem Quellreferenzintervall",
    },
    en: {
      glyph: "↓",
      label: "Below reference",
      badge: "badge-info",
      sentence: "below the source reference interval",
    },
  },
  within: {
    de: {
      glyph: "–",
      label: "Im Intervall",
      badge: "badge-success",
      sentence: "innerhalb des Quellreferenzintervalls",
    },
    en: {
      glyph: "–",
      label: "Within reference",
      badge: "badge-success",
      sentence: "within the source reference interval",
    },
  },
  no_reference: {
    de: {
      glyph: "⊘",
      label: "Keine Referenz",
      badge: "badge-neutral",
      sentence: "kein Quellreferenzintervall hinterlegt — Lage nicht bestimmbar",
    },
    en: {
      glyph: "⊘",
      label: "No reference",
      badge: "badge-neutral",
      sentence: "no source reference interval on file — position not determinable",
    },
  },
  not_evaluable: {
    de: {
      glyph: "⊘",
      label: "Nicht bestimmbar",
      badge: "badge-neutral",
      sentence: "Lage relativ zum Referenzintervall nicht bestimmbar",
    },
    en: {
      glyph: "⊘",
      label: "Not determinable",
      badge: "badge-neutral",
      sentence: "position relative to the reference interval not determinable",
    },
  },
};

/** The localized pill label + screen-reader clause for a value's position. */
export function lageLabel(
  position: ReferencePosition,
  locale: Locale = "de",
): LageLabel {
  return LABELS[position][locale];
}
