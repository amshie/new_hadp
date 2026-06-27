"use client";

import { useState, type CSSProperties } from "react";

import type { ThroughputChartView } from "@/lib/presenters/dashboard";

// VitaBahn "Review-Durchsatz" (ADR-0006 follow-up). Renders the REAL per-day report-version
// throughput — Erstellt (versions created) vs Signiert (versions approved) — from persisted
// timestamps. The server loads the full 30-day window; the 14/30 toggle slices client-side and
// recomputes totals from the slice (no refetch). A real rate over time, not a fabricated trend.

const card: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
  padding: "20px 22px",
};
const titleStyle: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 700,
  fontSize: "var(--text-lg)",
  color: "var(--text-strong)",
  margin: "0 0 3px",
  letterSpacing: "-0.01em",
};

export function ThroughputTile({ view }: { view: ThroughputChartView }) {
  const [win, setWin] = useState<14 | 30>(14);
  const pts = view.points.slice(-win);
  const n = pts.length;

  const totalCreated = pts.reduce((s, p) => s + p.created, 0);
  const totalSigned = pts.reduce((s, p) => s + p.signed, 0);
  const avgSigned = n ? Math.round((totalSigned / n) * 10) / 10 : 0;
  const max = Math.max(1, ...pts.map((p) => Math.max(p.created, p.signed)));

  // Plot geometry (viewBox units; SVG scales to container width).
  const W = 600;
  const H = 210;
  const L = 40;
  const R = 12;
  const TOP = 12;
  const BOT = 26;
  const plotW = W - L - R;
  const plotH = H - TOP - BOT;
  const base = TOP + plotH;
  const xAt = (i: number) =>
    n <= 1 ? L + plotW / 2 : L + (plotW * i) / (n - 1);
  const yAt = (v: number) => base - (plotH * v) / max;
  const lineOf = (key: "created" | "signed") =>
    pts
      .map((p, i) => `${xAt(i).toFixed(1)},${yAt(p[key]).toFixed(1)}`)
      .join(" ");
  const signedLine = lineOf("signed");
  const createdLine = lineOf("created");
  const signedArea = n
    ? `${L},${base} ${signedLine} ${xAt(n - 1).toFixed(1)},${base}`
    : "";

  const yTicks = [0, Math.round(max / 2), max].filter(
    (v, i, a) => a.indexOf(v) === i,
  );
  const xLabelCount = Math.min(6, n);
  const xIdx =
    xLabelCount <= 1
      ? [Math.max(0, n - 1)]
      : Array.from({ length: xLabelCount }, (_, k) =>
          Math.round((k * (n - 1)) / (xLabelCount - 1)),
        );

  const ariaSummary = `Review-Durchsatz über ${win} Tage: ${totalSigned} signiert, ${totalCreated} erstellt, Ø ${avgSigned} signiert pro Tag.`;

  const toggleBtn = (active: boolean): CSSProperties => ({
    padding: "4px 11px",
    borderRadius: "var(--radius-sm)",
    fontFamily: "var(--font-mono)",
    fontSize: "11px",
    fontWeight: 600,
    cursor: "pointer",
    border: "1px solid " + (active ? "var(--brand-border)" : "transparent"),
    background: active ? "var(--brand-soft)" : "transparent",
    color: active ? "var(--brand)" : "var(--text-muted)",
  });

  return (
    <div style={card}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "12px",
          marginBottom: "10px",
        }}
      >
        <div>
          <h3 style={titleStyle}>Review-Durchsatz</h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: 0,
            }}
          >
            Entwürfe erstellt vs. Reviews signiert · echte Zeitstempel
          </p>
        </div>
        <div
          style={{
            display: "inline-flex",
            gap: "2px",
            padding: "2px",
            borderRadius: "var(--radius-md)",
            background: "var(--surface-sunken)",
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            style={toggleBtn(win === 14)}
            onClick={() => setWin(14)}
          >
            14 T
          </button>
          <button
            type="button"
            style={toggleBtn(win === 30)}
            onClick={() => setWin(30)}
          >
            30 T
          </button>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "6px" }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "11.5px",
            color: "var(--text-muted)",
          }}
        >
          <span
            style={{
              width: "14px",
              height: "2px",
              background: "var(--vital-500)",
              display: "inline-block",
            }}
          />
          Signiert
        </span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "11.5px",
            color: "var(--text-muted)",
          }}
        >
          <span
            style={{
              width: "14px",
              height: "0",
              borderTop: "2px dashed var(--text-faint)",
              display: "inline-block",
            }}
          />
          Erstellt
        </span>
      </div>

      <svg
        role="img"
        aria-label={ariaSummary}
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ display: "block", height: "auto" }}
      >
        {yTicks.map((v) => (
          <g key={v}>
            <line
              x1={L}
              y1={yAt(v)}
              x2={W - R}
              y2={yAt(v)}
              stroke="var(--border-subtle)"
              strokeWidth="1"
            />
            <text
              x={L - 8}
              y={yAt(v) + 3}
              textAnchor="end"
              fontSize="9"
              fontFamily="var(--font-mono)"
              fill="var(--text-faint)"
            >
              {v}
            </text>
          </g>
        ))}
        {signedArea && (
          <polygon points={signedArea} fill="var(--vital-500)" opacity="0.12" />
        )}
        {n > 1 && (
          <polyline
            points={createdLine}
            fill="none"
            stroke="var(--text-faint)"
            strokeWidth="1.6"
            strokeDasharray="4 3"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {n > 1 && (
          <polyline
            points={signedLine}
            fill="none"
            stroke="var(--vital-500)"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {pts.map((p, i) => (
          <circle
            key={p.date}
            cx={xAt(i)}
            cy={yAt(p.signed)}
            r={n <= 14 ? 2.2 : 1.4}
            fill="var(--vital-500)"
          />
        ))}
        {xIdx.map((idx) => (
          <text
            key={idx}
            x={xAt(idx)}
            y={H - 8}
            textAnchor="middle"
            fontSize="9"
            fontFamily="var(--font-mono)"
            fill="var(--text-faint)"
          >
            {pts[idx]?.label ?? ""}
          </text>
        ))}
      </svg>

      {/* Footer stats (real, over the visible window) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "8px",
          marginTop: "14px",
          paddingTop: "14px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        {[
          {
            label: "Signiert gesamt",
            value: totalSigned,
            accent: "var(--vital-500)",
          },
          {
            label: "Erstellt gesamt",
            value: totalCreated,
            accent: "var(--text-strong)",
          },
          {
            label: "Ø Signiert / Tag",
            value: avgSigned,
            accent: "var(--brand)",
          },
        ].map((s) => (
          <div key={s.label}>
            <div style={{ ...colLabel, marginBottom: "4px" }}>{s.label}</div>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "20px",
                lineHeight: 1,
                color: s.accent,
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Accessible textual alternative (WCAG: charts carry a data table) */}
      <details style={{ marginTop: "12px" }}>
        <summary
          style={{
            fontSize: "11.5px",
            color: "var(--text-muted)",
            cursor: "pointer",
          }}
        >
          Datentabelle anzeigen
        </summary>
        <table
          style={{
            width: "100%",
            marginTop: "8px",
            borderCollapse: "collapse",
            fontSize: "11.5px",
          }}
        >
          <thead>
            <tr>
              <th
                style={{ ...colLabel, textAlign: "left", padding: "4px 6px" }}
              >
                Tag
              </th>
              <th
                style={{ ...colLabel, textAlign: "right", padding: "4px 6px" }}
              >
                Erstellt
              </th>
              <th
                style={{ ...colLabel, textAlign: "right", padding: "4px 6px" }}
              >
                Signiert
              </th>
            </tr>
          </thead>
          <tbody>
            {pts.map((p) => (
              <tr key={p.date}>
                <td style={{ padding: "3px 6px", color: "var(--text-body)" }}>
                  {p.date}
                </td>
                <td
                  style={{
                    padding: "3px 6px",
                    textAlign: "right",
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-body)",
                  }}
                >
                  {p.created}
                </td>
                <td
                  style={{
                    padding: "3px 6px",
                    textAlign: "right",
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-body)",
                  }}
                >
                  {p.signed}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

const colLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "10px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};
