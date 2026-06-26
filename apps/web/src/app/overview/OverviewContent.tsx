"use client";

import { useMemo, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";

import { clickable } from "@/components/vitabahn/interactive";
import {
  ATTN_META,
  ERS30,
  SIG30,
  STATUS_META,
  WORK_ROWS,
  initials,
  type WorkStatus,
} from "@/lib/demo/dashboard";

// VitaBahn Overview (Übersicht) — ADR-0005. Faithful port of the comp's overview
// screen. Synthetic Alpha; the data-quality percentages here are a founder-approved
// surface (ADR-0005), not a domain verdict.

const MAX = 12;
const HERO_BARS = false; // comp default heroChart = "Fläche" (area)
const SHOW_SPARK = true;

interface Pt {
  x: number;
  y: number;
}
function series(values: number[]) {
  const W = 760,
    padL = 34,
    padR = 14,
    padT = 14,
    padB = 30,
    H = 230;
  const n = values.length;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const x = (i: number) => padL + (n <= 1 ? 0 : (innerW * i) / (n - 1));
  const y = (v: number) => padT + innerH * (1 - v / MAX);
  const pts: Pt[] = values.map((v, i) => ({
    x: +x(i).toFixed(2),
    y: +y(v).toFixed(2),
  }));
  const line = pts.map((p, i) => (i ? "L" : "M") + p.x + " " + p.y).join(" ");
  const first = pts[0]!;
  const lastP = pts[n - 1]!;
  const area =
    line +
    " L " +
    lastP.x +
    " " +
    (H - padB) +
    " L " +
    first.x +
    " " +
    (H - padB) +
    " Z";
  return { pts, line, area, x };
}

function qColor(q: number) {
  return q >= 90
    ? "var(--vital-500)"
    : q >= 70
      ? "var(--amber-500)"
      : "var(--rose-500)";
}

const TABS: { key: "alle" | WorkStatus; label: string }[] = [
  { key: "pruefung", label: "Offene Reviews" },
  { key: "entwurf", label: "Entwürfe" },
  { key: "genehmigt", label: "Genehmigt" },
  { key: "freigegeben", label: "Freigegeben" },
  { key: "alle", label: "Alle" },
];

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};
const colLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "10px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};
const sectionTitle: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 700,
  fontSize: "var(--text-lg)",
  color: "var(--text-strong)",
  margin: "0 0 3px",
  letterSpacing: "-0.01em",
};
const sectionSub: CSSProperties = {
  fontSize: "12.5px",
  color: "var(--text-muted)",
  margin: 0,
};
const WORK_GRID =
  "minmax(210px,1.9fr) minmax(190px,1.7fr) 104px 128px 116px 92px";

const upArrow = (
  <svg
    width="11"
    height="11"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M7 17L17 7M9 7h8v8" />
  </svg>
);

const KPIS = [
  {
    label: "Offene Reviews",
    value: "7",
    delta: "+3 heute",
    deltaColor: "var(--amber-500)",
    arrow: true,
    help: "Klinische Prüfung ausstehend",
    iconBg: "rgba(201,136,28,0.12)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--amber-500)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
    spark: "0,24 17,20 34,26 51,18 68,21 85,15 102,18 119,9",
    sparkStroke: "var(--amber-400)",
    sparkDot: "var(--amber-500)",
    dotY: 9,
  },
  {
    label: "Entwürfe",
    value: "12",
    delta: "+5 · 7 T",
    deltaColor: "var(--text-muted)",
    arrow: false,
    help: "Quellengebunden · nicht freigegeben",
    iconBg: "var(--surface-sunken)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--slate-500)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M16 13H8M16 17H8" />
      </svg>
    ),
    spark: "0,26 17,23 34,24 51,17 68,20 85,13 102,16 119,8",
    sparkStroke: "var(--slate-400)",
    sparkDot: "var(--slate-500)",
    dotY: 8,
  },
  {
    label: "Signiert · 7 Tage",
    value: "23",
    delta: "+18%",
    deltaColor: "var(--vital-500)",
    arrow: true,
    help: "Reviews signiert & freigabebereit",
    iconBg: "var(--brand-soft)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--teal-600)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <path d="M22 4L12 14.01l-3-3" />
      </svg>
    ),
    spark: "0,28 17,24 34,18 51,21 68,13 85,15 102,9 119,5",
    sparkStroke: "var(--vital-400)",
    sparkDot: "var(--vital-500)",
    dotY: 5,
  },
  {
    label: "Patienten",
    value: "148",
    delta: "+6",
    deltaColor: "var(--vital-500)",
    arrow: true,
    help: "Tenant-bezogen · RLS-geschützt",
    iconBg: "var(--brand-soft)",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--teal-600)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
    spark: "0,22 17,20 34,18 51,17 68,15 85,12 102,10 119,7",
    sparkStroke: "var(--teal-400)",
    sparkDot: "var(--teal-600)",
    dotY: 7,
  },
];

const QUALITY_BARS = [
  { label: "Vollständigkeit", pct: 96, color: "var(--teal-500)" },
  { label: "Aktualität", pct: 91, color: "var(--teal-500)" },
  { label: "Quellenbindung", pct: 99, color: "var(--vital-500)" },
  { label: "Plausibilität", pct: 88, color: "var(--amber-500)" },
];

const ACTIVITY = [
  {
    iconBg: "rgba(20,169,130,0.12)",
    stroke: "var(--vital-500)",
    icon: (
      <>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <path d="M22 4L12 14.01l-3-3" />
      </>
    ),
    title: "Bericht freigegeben",
    ref: "MLX-0521",
    sub: "von Dr. S. Johnson",
    time: "vor 14 Min.",
  },
  {
    iconBg: "var(--brand-soft)",
    stroke: "var(--teal-600)",
    icon: (
      <>
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
      </>
    ),
    title: "Review signiert",
    ref: "MLX-0277",
    sub: "von Dr. S. Johnson",
    time: "vor 1 Std.",
  },
  {
    iconBg: "var(--surface-sunken)",
    stroke: "var(--slate-500)",
    icon: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
      </>
    ),
    title: "Berichtsentwurf erstellt",
    ref: "MLX-0463",
    sub: "quellengebunden · nicht freigegeben",
    time: "vor 2 Std.",
  },
  {
    iconBg: "rgba(63,164,201,0.12)",
    stroke: "var(--sky-400)",
    icon: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </>
    ),
    title: "Import abgeschlossen",
    ref: "Labcorp CSV",
    sub: "1.204 Beobachtungen",
    time: "vor 3 Std.",
  },
  {
    iconBg: "rgba(201,136,28,0.12)",
    stroke: "var(--amber-500)",
    icon: (
      <>
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </>
    ),
    title: "Datenqualitätsregel ausgelöst",
    ref: "MLX-0188",
    sub: "Vollständigkeit < 70 %",
    time: "vor 5 Std.",
  },
];

const IMPORTS = [
  {
    name: "Labcorp",
    meta: "Labordaten · HL7",
    count: "1.204",
    running: false,
    pct: 100,
    color: "var(--vital-500)",
  },
  {
    name: "Withings",
    meta: "Wearable-Sync",
    count: "842",
    running: false,
    pct: 100,
    color: "var(--vital-500)",
  },
  {
    name: "Dexcom",
    meta: "CGM-Stream",
    count: "läuft · 63%",
    running: true,
    pct: 63,
    color: "var(--amber-400)",
  },
];

export function OverviewContent() {
  const router = useRouter();
  const [range, setRange] = useState<14 | 30>(14);
  const [tab, setTab] = useState<"alle" | WorkStatus>("pruefung");
  const [term, setTerm] = useState("");

  const chart = useMemo(() => {
    const sig = SIG30.slice(-range);
    const ers = ERS30.slice(-range);
    const S = series(sig);
    const E = series(ers);
    const last = S.pts[S.pts.length - 1]!;
    const bw = ((760 - 34 - 14) / sig.length) * 0.5;
    const bars = sig.map((v, i) => {
      const cx = S.x(i);
      const yy = 14 + (230 - 14 - 30) * (1 - v / MAX);
      return {
        x: +(cx - bw / 2).toFixed(2),
        y: +yy.toFixed(2),
        w: +bw.toFixed(2),
        h: +(230 - 30 - yy).toFixed(2),
        fill: i === sig.length - 1 ? "var(--vital-500)" : "var(--teal-400)",
      };
    });
    const steps = 4;
    const xlabels: { x: number; label: string }[] = [];
    for (let k = 0; k < steps; k++) {
      const i = Math.round(((sig.length - 1) * k) / (steps - 1));
      const ago = sig.length - 1 - i;
      xlabels.push({
        x: +S.x(i).toFixed(2),
        label: ago === 0 ? "Heute" : "−" + ago + " T",
      });
    }
    const sigTotal = sig.reduce((a, b) => a + b, 0);
    const ersTotal = ers.reduce((a, b) => a + b, 0);
    const sigAvg = Math.round(sigTotal / range);
    return {
      sigLine: S.line,
      sigArea: S.area,
      ersLine: E.line,
      lastX: last.x,
      lastY: last.y,
      bars,
      xlabels,
      sigTotal,
      ersTotal,
      sigAvg,
    };
  }, [range]);

  const counts = useMemo(
    () => ({
      pruefung: WORK_ROWS.filter((r) => r.status === "pruefung").length,
      entwurf: WORK_ROWS.filter((r) => r.status === "entwurf").length,
      genehmigt: WORK_ROWS.filter((r) => r.status === "genehmigt").length,
      freigegeben: WORK_ROWS.filter((r) => r.status === "freigegeben").length,
      alle: WORK_ROWS.length,
    }),
    [],
  );

  const visible = useMemo(() => {
    const byTab =
      tab === "alle" ? WORK_ROWS : WORK_ROWS.filter((r) => r.status === tab);
    const q = term.toLowerCase();
    return byTab.filter((r) =>
      `${r.name} ${r.id} ${r.assess}`.toLowerCase().includes(q),
    );
  }, [tab, term]);

  const rangeBtn = (active: boolean): CSSProperties => ({
    padding: "6px 12px",
    borderRadius: "var(--radius-xs)",
    border: "none",
    cursor: "pointer",
    fontFamily: "var(--font-mono)",
    fontSize: "11px",
    fontWeight: 600,
    background: active ? "var(--surface-card)" : "transparent",
    color: active ? "var(--text-strong)" : "var(--text-muted)",
    boxShadow: active ? "var(--shadow-xs)" : "none",
  });
  const tabBtn = (active: boolean): CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "7px",
    padding: "7px 13px",
    borderRadius: "var(--radius-pill)",
    fontFamily: "var(--font-text)",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
    border: "1px solid " + (active ? "var(--brand-border)" : "transparent"),
    background: active ? "var(--brand-soft)" : "transparent",
    color: active ? "var(--brand)" : "var(--text-muted)",
  });
  const tabBadge = (active: boolean): CSSProperties => ({
    fontFamily: "var(--font-mono)",
    fontSize: "10.5px",
    fontWeight: 600,
    padding: "1px 7px",
    borderRadius: "var(--radius-pill)",
    background: active ? "var(--brand)" : "var(--surface-sunken)",
    color: active ? "var(--text-on-brand)" : "var(--text-muted)",
  });

  return (
    <>
      {/* header block */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "24px",
          flexWrap: "wrap",
          marginBottom: "28px",
        }}
      >
        <div style={{ minWidth: "280px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--brand)",
              fontWeight: 500,
              marginBottom: "10px",
            }}
          >
            Klinischer Arbeitsbereich
          </div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-3xl)",
              letterSpacing: "var(--tracking-tight)",
              color: "var(--text-strong)",
              margin: "0 0 10px",
              lineHeight: 1.05,
            }}
          >
            Guten Nachmittag, Dr. Johnson
          </h1>
          <p
            style={{
              fontSize: "var(--text-md)",
              lineHeight: 1.5,
              color: "var(--text-muted)",
              margin: 0,
              maxWidth: "62ch",
            }}
          >
            <span style={{ color: "var(--text-strong)", fontWeight: 600 }}>
              7 Assessments
            </span>{" "}
            warten auf Ihre Prüfung. Quellengebundene Entwürfe müssen vor jeder
            Freigabe geprüft werden.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", flexShrink: 0 }}>
          <button
            type="button"
            className="vb-btn-sec"
            title="Im Prototyp noch nicht umgesetzt"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "42px",
              padding: "0 16px",
              whiteSpace: "nowrap",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-card)",
              color: "var(--text-strong)",
              fontFamily: "var(--font-text)",
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
            Daten importieren
          </button>
          <button
            type="button"
            className="vb-btn-pri"
            title="Im Prototyp noch nicht umgesetzt"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "42px",
              padding: "0 18px",
              whiteSpace: "nowrap",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--brand)",
              background: "var(--brand)",
              color: "var(--text-on-brand)",
              fontFamily: "var(--font-text)",
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 1px 2px rgba(12,18,20,0.12)",
            }}
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
            Patient hinzufügen
          </button>
        </div>
      </div>

      {/* KPI ROW */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(212px, 1fr))",
          gap: "16px",
          marginBottom: "16px",
        }}
      >
        {KPIS.map((k) => (
          <div
            key={k.label}
            style={{ ...cardStyle, padding: "18px 18px 14px" }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "14px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10.5px",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  fontWeight: 500,
                }}
              >
                {k.label}
              </span>
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "var(--radius-sm)",
                  background: k.iconBg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {k.icon}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "9px",
                marginBottom: "6px",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "34px",
                  lineHeight: 1,
                  color: "var(--text-strong)",
                  letterSpacing: "-0.02em",
                }}
              >
                {k.value}
              </span>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "3px",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: k.deltaColor,
                  paddingBottom: "4px",
                }}
              >
                {k.arrow && upArrow}
                {k.delta}
              </span>
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                marginBottom: "10px",
              }}
            >
              {k.help}
            </div>
            {SHOW_SPARK && (
              <svg
                width="100%"
                height="30"
                viewBox="0 0 120 34"
                preserveAspectRatio="none"
                fill="none"
              >
                <polyline
                  points={k.spark}
                  stroke={k.sparkStroke}
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="119" cy={k.dotY} r="2.4" fill={k.sparkDot} />
              </svg>
            )}
          </div>
        ))}
      </div>

      {/* CHART ROW */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.7fr 1fr",
          gap: "16px",
          marginBottom: "16px",
        }}
      >
        {/* Throughput */}
        <div
          style={{
            ...cardStyle,
            padding: "20px 22px 16px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: "16px",
              marginBottom: "18px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <h3 style={sectionTitle}>Review-Durchsatz</h3>
              <p style={sectionSub}>Entwürfe erstellt vs. Reviews signiert</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "14px",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-muted)",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span
                    style={{
                      width: "10px",
                      height: "3px",
                      borderRadius: "2px",
                      background: "var(--vital-400)",
                    }}
                  />
                  Signiert
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span
                    style={{
                      width: "10px",
                      height: 0,
                      borderTop: "2px dashed var(--slate-400)",
                    }}
                  />
                  Erstellt
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  padding: "3px",
                  gap: "2px",
                  background: "var(--surface-sunken)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <button
                  type="button"
                  onClick={() => setRange(14)}
                  style={rangeBtn(range === 14)}
                >
                  14 T
                </button>
                <button
                  type="button"
                  onClick={() => setRange(30)}
                  style={rangeBtn(range === 30)}
                >
                  30 T
                </button>
              </div>
            </div>
          </div>

          <div style={{ flex: 1, minHeight: "200px" }}>
            <svg
              width="100%"
              viewBox="0 0 760 230"
              preserveAspectRatio="xMidYMid meet"
              style={{ display: "block", overflow: "visible" }}
            >
              <defs>
                <linearGradient id="vbSigFill" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor="var(--vital-400)"
                    stopOpacity="0.26"
                  />
                  <stop
                    offset="100%"
                    stopColor="var(--vital-400)"
                    stopOpacity="0.02"
                  />
                </linearGradient>
              </defs>
              <g stroke="var(--border-subtle)" strokeWidth="1">
                <line x1="34" y1="14" x2="746" y2="14" />
                <line x1="34" y1="76" x2="746" y2="76" />
                <line x1="34" y1="138" x2="746" y2="138" />
                <line x1="34" y1="200" x2="746" y2="200" />
              </g>
              <g
                fontFamily="var(--font-mono)"
                fontSize="10"
                fill="var(--text-faint)"
                textAnchor="end"
              >
                <text x="27" y="18">
                  12
                </text>
                <text x="27" y="80">
                  8
                </text>
                <text x="27" y="142">
                  4
                </text>
                <text x="27" y="204">
                  0
                </text>
              </g>

              {HERO_BARS ? (
                <g>
                  {chart.bars.map((b, i) => (
                    <rect
                      key={i}
                      x={b.x}
                      y={b.y}
                      width={b.w}
                      height={b.h}
                      rx="2"
                      fill={b.fill}
                    />
                  ))}
                  <path
                    d={chart.ersLine}
                    fill="none"
                    stroke="var(--slate-400)"
                    strokeWidth="1.6"
                    strokeDasharray="4 4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </g>
              ) : (
                <g>
                  <path
                    d={chart.sigArea}
                    fill="url(#vbSigFill)"
                    stroke="none"
                  />
                  <path
                    d={chart.ersLine}
                    fill="none"
                    stroke="var(--slate-400)"
                    strokeWidth="1.6"
                    strokeDasharray="4 4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d={chart.sigLine}
                    fill="none"
                    stroke="var(--vital-400)"
                    strokeWidth="2.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle
                    cx={chart.lastX}
                    cy={chart.lastY}
                    r="9"
                    fill="var(--vital-400)"
                    opacity="0.18"
                    style={{
                      transformBox: "fill-box",
                      transformOrigin: "center",
                      animation: "vb-ping 2.6s var(--ease-out) infinite",
                    }}
                  />
                  <circle
                    cx={chart.lastX}
                    cy={chart.lastY}
                    r="4"
                    fill="var(--vital-500)"
                    stroke="var(--surface-card)"
                    strokeWidth="2"
                  />
                </g>
              )}

              <g
                fontFamily="var(--font-mono)"
                fontSize="10"
                fill="var(--text-faint)"
                textAnchor="middle"
              >
                {chart.xlabels.map((x, i) => (
                  <text key={i} x={x.x} y="222">
                    {x.label}
                  </text>
                ))}
              </g>
            </svg>
          </div>

          <div
            style={{
              display: "flex",
              gap: "24px",
              paddingTop: "14px",
              marginTop: "6px",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-muted)",
                }}
              >
                Signiert gesamt
              </span>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                }}
              >
                {chart.sigTotal}
              </div>
            </div>
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-muted)",
                }}
              >
                Erstellt gesamt
              </span>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                }}
              >
                {chart.ersTotal}
              </div>
            </div>
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-muted)",
                }}
              >
                Ø Signiert / Tag
              </span>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--vital-500)",
                }}
              >
                {chart.sigAvg}
              </div>
            </div>
          </div>
        </div>

        {/* Data quality gauge (ADR-0005 founder-approved surface) */}
        <div style={{ ...cardStyle, padding: "20px 22px 18px" }}>
          <h3 style={{ ...sectionTitle, margin: "0 0 2px" }}>Datenqualität</h3>
          <p style={{ ...sectionSub, margin: "0 0 6px" }}>
            Verifizierte Beobachtungen · heute
          </p>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              margin: "2px 0 14px",
            }}
          >
            <div
              style={{ position: "relative", width: "172px", height: "172px" }}
            >
              <svg width="172" height="172" viewBox="0 0 180 180">
                <circle
                  cx="90"
                  cy="90"
                  r="70"
                  fill="none"
                  stroke="var(--surface-sunken)"
                  strokeWidth="14"
                />
                <circle
                  cx="90"
                  cy="90"
                  r="70"
                  fill="none"
                  stroke="var(--vital-400)"
                  strokeWidth="14"
                  strokeLinecap="round"
                  strokeDasharray="413.4 26.4"
                  transform="rotate(-90 90 90)"
                />
              </svg>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "40px",
                    lineHeight: 1,
                    color: "var(--text-strong)",
                    letterSpacing: "-0.02em",
                  }}
                >
                  94
                  <span
                    style={{ fontSize: "20px", color: "var(--text-muted)" }}
                  >
                    %
                  </span>
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "var(--vital-500)",
                    marginTop: "6px",
                    fontWeight: 600,
                  }}
                >
                  verifiziert
                </span>
              </div>
            </div>
          </div>

          <div
            style={{ display: "flex", flexDirection: "column", gap: "11px" }}
          >
            {QUALITY_BARS.map((b) => (
              <div key={b.label}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "12px",
                    marginBottom: "5px",
                  }}
                >
                  <span style={{ color: "var(--text-body)" }}>{b.label}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-strong)",
                      fontWeight: 600,
                    }}
                  >
                    {b.pct}%
                  </span>
                </div>
                <div
                  style={{
                    height: "6px",
                    borderRadius: "999px",
                    background: "var(--surface-sunken)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: b.pct + "%",
                      borderRadius: "999px",
                      background: b.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* WORK LIST */}
      <div style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}>
        <div style={{ padding: "20px 22px 0" }}>
          <h3 style={sectionTitle}>Klinische Arbeitsliste</h3>
          <p style={{ ...sectionSub, margin: "0 0 16px" }}>
            Nach Status sortiert · keine automatische Diagnose oder
            Therapieempfehlung.
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              flexWrap: "wrap",
              marginBottom: "4px",
            }}
          >
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {TABS.map((t) => {
                const active = tab === t.key;
                const c = t.key === "alle" ? counts.alle : counts[t.key];
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    style={tabBtn(active)}
                  >
                    {t.label} <span style={tabBadge(active)}>{c}</span>
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <svg
                  aria-hidden="true"
                  focusable="false"
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--text-faint)"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{
                    position: "absolute",
                    left: "11px",
                    pointerEvents: "none",
                  }}
                >
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <input
                  className="vb-input"
                  type="text"
                  aria-label="Patient oder ID suchen"
                  value={term}
                  onChange={(e) => setTerm(e.target.value)}
                  placeholder="Patient oder ID suchen"
                  style={{
                    height: "36px",
                    width: "220px",
                    padding: "0 12px 0 33px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    background: "var(--surface-sunken)",
                    color: "var(--text-strong)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>
              <button
                type="button"
                aria-label="Sortieren"
                className="vb-iconbtn"
                style={{
                  width: "36px",
                  height: "36px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--surface-card)",
                  cursor: "pointer",
                }}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--text-muted)"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3 6h11M3 12h8M3 18h5M18 8V5M18 19l3-3M18 19l-3-3M18 19V8" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <div style={{ minWidth: "1000px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: WORK_GRID,
                alignItems: "center",
                gap: "16px",
                padding: "14px 22px 10px",
                borderBottom: "1px solid var(--border-subtle)",
                marginTop: "14px",
              }}
            >
              <span style={colLabel}>Patient</span>
              <span style={colLabel}>Assessment</span>
              <span style={colLabel}>Priorität</span>
              <span style={colLabel}>Datenqualität</span>
              <span style={colLabel}>Status</span>
              <span style={{ ...colLabel, textAlign: "right" }}>
                Aktualisiert
              </span>
            </div>

            {visible.map((r) => {
              const sm = STATUS_META[r.status];
              const am = ATTN_META[r.attn];
              const qc = qColor(r.q);
              return (
                <div
                  key={r.id}
                  className="vb-row"
                  {...clickable(
                    () => router.push(`/patients/${r.id}`),
                    `Patient ${r.name}, ${r.id} öffnen`,
                  )}
                  style={{
                    display: "grid",
                    gridTemplateColumns: WORK_GRID,
                    alignItems: "center",
                    gap: "16px",
                    padding: "13px 22px",
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "11px",
                      minWidth: 0,
                    }}
                  >
                    <div
                      style={{
                        width: "34px",
                        height: "34px",
                        flexShrink: 0,
                        borderRadius: "999px",
                        background: "var(--brand-soft)",
                        border: "1px solid var(--brand-border)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--teal-600)",
                      }}
                    >
                      {initials(r.name)}
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: "13.5px",
                          fontWeight: 600,
                          color: "var(--text-strong)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {r.name}
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "var(--text-faint)",
                        }}
                      >
                        {r.id}
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: "13px",
                      color: "var(--text-body)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {r.assess}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "7px",
                    }}
                  >
                    <span
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "999px",
                        flexShrink: 0,
                        background: am.c,
                      }}
                    />
                    <span
                      style={{
                        fontSize: "12.5px",
                        fontWeight: 500,
                        color: am.c,
                      }}
                    >
                      {am.label}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "9px",
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        height: "6px",
                        borderRadius: "999px",
                        background: "var(--surface-sunken)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: "999px",
                          width: r.q + "%",
                          background: qc,
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        minWidth: "34px",
                        textAlign: "right",
                        color: qc,
                      }}
                    >
                      {r.q}%
                    </span>
                  </div>
                  <div>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        padding: "3px 10px",
                        borderRadius: "999px",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        color: sm.fg,
                        background: sm.bg,
                        border: "1px solid " + sm.bd,
                      }}
                    >
                      {sm.label}
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11.5px",
                      color: "var(--text-muted)",
                      textAlign: "right",
                    }}
                  >
                    {r.upd}
                  </div>
                </div>
              );
            })}

            {visible.length === 0 && (
              <div style={{ textAlign: "center", padding: "54px 20px" }}>
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "var(--text-lg)",
                    color: "var(--text-strong)",
                    marginBottom: "6px",
                  }}
                >
                  Keine passenden Vorgänge
                </div>
                <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                  Ändern Sie den Filter oder den Suchbegriff.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* BOTTOM ROW */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.5fr 1fr",
          gap: "16px",
        }}
      >
        {/* Activity */}
        <div style={{ ...cardStyle, padding: "20px 22px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "16px",
            }}
          >
            <div>
              <h3 style={{ ...sectionTitle, margin: "0 0 2px" }}>
                Letzte Aktivität
              </h3>
              <p style={sectionSub}>Audit-relevante Ereignisse</p>
            </div>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--brand)",
                fontWeight: 600,
                letterSpacing: "0.03em",
              }}
            >
              Audit-Protokoll →
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            {ACTIVITY.map((a, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "13px",
                  padding: "11px 0",
                  borderBottom:
                    i === ACTIVITY.length - 1
                      ? "none"
                      : "1px solid var(--border-subtle)",
                }}
              >
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    flexShrink: 0,
                    borderRadius: "var(--radius-sm)",
                    background: a.iconBg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={a.stroke}
                    strokeWidth="1.9"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {a.icon}
                  </svg>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{ fontSize: "13.5px", color: "var(--text-strong)" }}
                  >
                    <span style={{ fontWeight: 600 }}>{a.title}</span> ·{" "}
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                        color: "var(--text-muted)",
                      }}
                    >
                      {a.ref}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: "var(--text-muted)",
                      marginTop: "2px",
                    }}
                  >
                    {a.sub}
                  </div>
                </div>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-faint)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {a.time}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Imports & sources */}
        <div
          style={{
            ...cardStyle,
            padding: "20px 22px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <h3 style={{ ...sectionTitle, margin: "0 0 2px" }}>
            Importe &amp; Quellen
          </h3>
          <p style={{ ...sectionSub, margin: "0 0 16px" }}>
            Deterministische Pipeline · heute
          </p>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "14px",
              flex: 1,
            }}
          >
            {IMPORTS.map((im) => (
              <div key={im.name}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: "7px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "var(--text-strong)",
                      }}
                    >
                      {im.name}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10.5px",
                        color: "var(--text-faint)",
                      }}
                    >
                      {im.meta}
                    </span>
                  </div>
                  {im.running ? (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "5px",
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--amber-500)",
                      }}
                    >
                      <span
                        style={{
                          width: "6px",
                          height: "6px",
                          borderRadius: "999px",
                          background: "var(--amber-400)",
                          animation: "vb-pulse 1.6s ease-in-out infinite",
                        }}
                      />
                      {im.count}
                    </span>
                  ) : (
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--vital-500)",
                      }}
                    >
                      {im.count}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    height: "6px",
                    borderRadius: "999px",
                    background: "var(--surface-sunken)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: im.pct + "%",
                      borderRadius: "999px",
                      background: im.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            className="vb-btn-next"
            style={{
              marginTop: "18px",
              width: "100%",
              height: "40px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-card)",
              color: "var(--text-strong)",
              fontFamily: "var(--font-text)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Importprüfung öffnen
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.9"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
