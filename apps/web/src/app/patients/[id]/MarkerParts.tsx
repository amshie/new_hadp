"use client";

import { useI18n } from "@/lib/i18n/I18nProvider";
import { fill } from "@/lib/i18n/fill";
import { lageLabel } from "@/lib/lageCopy";
import type { PositionBar, ReferencePosition } from "@/lib/referencePosition";

// Pieces of a marker shown in the domain lists and in the marker dialog (ADR-0006): the
// laboratory's reference bar and the positional Lage pill. Neither is a verdict: the band is
// the source's own interval, and the pill names where the value lies against it.

// The values of closed vocabularies stay German and say so (ADR-0007).
export const GERMAN = "de";

// Calm, non-alarm colours for the positional Lage pill (never a verdict).
function lageVita(pos: ReferencePosition): {
  fg: string;
  bg: string;
  bd: string;
} {
  if (pos === "within")
    return {
      fg: "var(--vital-500)",
      bg: "rgba(20,169,130,0.12)",
      bd: "rgba(20,169,130,0.30)",
    };
  if (pos === "above" || pos === "below")
    return {
      fg: "var(--sky-400)",
      bg: "rgba(63,164,201,0.12)",
      bd: "rgba(63,164,201,0.30)",
    };
  return {
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
  };
}

export function ReferenceBar({
  bar,
  range,
}: {
  bar: PositionBar;
  range: string | null;
}) {
  const t = useI18n().t.patientPage.evidence;
  if (!bar.hasScale)
    return (
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "10.5px",
          color: "var(--text-faint)",
        }}
      >
        {t.noScale}
      </span>
    );
  return (
    <div aria-hidden="true" style={{ width: "100%" }}>
      <div
        style={{
          position: "relative",
          height: "8px",
          borderRadius: "999px",
          background: "var(--w-sand)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: bar.bandStartPct + "%",
            width: bar.bandEndPct - bar.bandStartPct + "%",
            background:
              "linear-gradient(90deg, var(--teal-300), var(--teal-500))",
            opacity: 0.55,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "-2px",
            bottom: "-2px",
            left: bar.midPct + "%",
            width: "1.5px",
            background: "var(--teal-700)",
            transform: "translateX(-50%)",
          }}
        />
        {bar.dotPct != null && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: bar.dotPct + "%",
              width: "9px",
              height: "9px",
              borderRadius: "999px",
              background:
                "radial-gradient(circle at 35% 35%, var(--amber-400), var(--amber-500))",
              transform: "translate(-50%,-50%)",
              boxShadow: "0 0 0 2px var(--surface-card)",
            }}
          />
        )}
      </div>
      {range && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            color: "var(--text-faint)",
            marginTop: "3px",
          }}
        >
          {fill(t.reference, { range })}
        </div>
      )}
    </div>
  );
}

export function LagePill({ pos }: { pos: ReferencePosition }) {
  const l = lageLabel(pos);
  const c = lageVita(pos);
  return (
    // The German name, until the English one is confirmed (ADR-0007).
    <span
      lang={GERMAN}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "3px 10px",
        borderRadius: "999px",
        fontFamily: "var(--font-text)",
        fontSize: "11.5px",
        fontWeight: 600,
        whiteSpace: "nowrap",
        color: c.fg,
        background: c.bg,
        border: "1px solid " + c.bd,
      }}
    >
      <span aria-hidden="true">{l.glyph}</span>
      {l.label}
      <span className="sr-only">{l.sentence}</span>
    </span>
  );
}
