"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { useRouter } from "next/navigation";

import { clickable } from "@/components/vitabahn/interactive";
import {
  DOMAINS,
  DOMAIN_DESC,
  DOMAIN_HEALTH,
  OBSERVATIONS,
  initials,
  type Observation,
  type ObsStat,
} from "@/lib/demo/dashboard";

// VitaBahn patient Detail (ADR-0005). Synthetic Alpha. The per-domain A–E grade from
// the comp was removed by founder direction (ADR-0005); the observation status
// (Normal/Grenzwertig/Auffällig) is a founder-approved surface recorded in the ADR.

const STAT3: Record<ObsStat, { label: string; txt: string; accent: string }> = {
  abnormal: {
    label: "Auffällig",
    txt: "var(--rose-500)",
    accent: "var(--rose-400)",
  },
  borderline: {
    label: "Grenzwertig",
    txt: "var(--amber-500)",
    accent: "var(--amber-400)",
  },
  normal: {
    label: "Normal",
    txt: "var(--teal-600)",
    accent: "var(--vital-400)",
  },
};
const ORDER3: ObsStat[] = ["abnormal", "borderline", "normal"];
const TRD: Record<string, string> = {
  up: "M2 15 L11 12 L20 13 L29 7 L38 4",
  down: "M2 4 L11 8 L20 7 L29 12 L38 15",
  flat: "M3 10 L37 10",
};
const EGRID = "minmax(150px,1.7fr) 104px minmax(96px,0.9fr) 92px 124px 64px";

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};
const eColLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "9.5px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};

const parseNum = (val: string) => {
  const m = String(val).match(/-?\d+(?:[.,]\d+)?/);
  return m ? parseFloat(m[0].replace(",", ".")) : 0;
};
const refNumsOf = (r: string) =>
  (String(r).match(/\d+(?:[.,]\d+)?/g) || []).map((x) =>
    parseFloat(x.replace(",", ".")),
  );
function inRef(v: number, r: string): boolean {
  const str = String(r);
  const nn = refNumsOf(r);
  if (str.indexOf("–") >= 0 && nn.length >= 2)
    return v >= nn[0]! && v <= nn[1]!;
  if (!nn.length) return true;
  const a = nn[0]!;
  if (str.indexOf("≥") >= 0) return v >= a;
  if (str.indexOf("≤") >= 0) return v <= a;
  if (str.indexOf("<") >= 0) return v < a;
  if (str.indexOf(">") >= 0) return v > a;
  return true;
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mär",
  "Apr",
  "Mai",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Okt",
  "Nov",
  "Dez",
];
const SAMPLE_MAP: Record<string, number[]> = {
  visit: [0],
  "3": [0, 1, 2, 3],
  "6": [0, 1, 2, 3, 4, 5, 6],
  "12": [0, 2, 4, 6, 8, 10, 12],
  "24": [0, 4, 8, 12, 16, 20, 24],
};
const HIST_TABS: [string, string][] = [
  ["visit", "Letzter Besuch"],
  ["3", "3 M"],
  ["6", "6 M"],
  ["12", "12 M"],
  ["24", "24 M"],
];

interface AuditStep {
  label: string;
  sub: string;
  first?: boolean;
  last?: boolean;
}
const AUDIT_STEPS: AuditStep[] = [
  { label: "Datenerfassung", sub: "Vollständig", first: true },
  { label: "Entwurf erstellt", sub: "Quellengebunden" },
  { label: "Klinischer Review", sub: "Signiert" },
  { label: "Ärztliche Freigabe", sub: "Abgeschlossen" },
  { label: "Patientenfreigabe", sub: "Freigegeben", last: true },
];

const check = (size: number) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="#fff"
    strokeWidth="2.6"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

export function PatientDetailContent({
  name,
  id,
  age,
}: {
  name: string;
  id: string;
  age: string;
}) {
  const router = useRouter();
  const [domainKey, setDomainKey] = useState("kardio");
  const [openMarker, setOpenMarker] = useState<Observation | null>(null);
  const [histRange, setHistRange] = useState("6");
  const lastFocusedRef = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const openObs = (o: Observation) => {
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    setOpenMarker(o);
  };
  const closeObs = () => setOpenMarker(null);

  // Modal a11y: close on Escape, move focus into the dialog on open, restore it to the
  // triggering row on close (WCAG 2.1.2 / 2.4.3 / 4.1.2).
  useEffect(() => {
    if (!openMarker) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeObs();
    };
    document.addEventListener("keydown", onKey);
    closeBtnRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      lastFocusedRef.current?.focus?.();
    };
  }, [openMarker]);

  const curHealth = DOMAIN_HEALTH[domainKey] ?? domainKey;
  const curDesc = DOMAIN_DESC[domainKey] ?? "";
  const curDomName = DOMAINS.find((d) => d.key === domainKey)?.name ?? "";

  const evidenceGroups = useMemo(() => {
    const all = OBSERVATIONS[domainKey] ?? [];
    return ORDER3.map((k) => {
      const items = all.filter((o) => o.stat === k);
      return items.length ? { key: k, bandLabel: STAT3[k].label, items } : null;
    }).filter(
      (g): g is { key: ObsStat; bandLabel: string; items: Observation[] } =>
        g !== null,
    );
  }, [domainKey]);

  const modal = useMemo(() => {
    const om = openMarker;
    if (!om) return null;
    const s3 = STAT3[om.stat] ?? STAT3.normal;
    const cur = parseNum(om.value);
    const dir = om.trend === "up" ? 1 : om.trend === "down" ? -1 : 0;
    const baseY = 2025,
      baseM = 5;
    const monLabel = (ago: number) => {
      let m = baseM - ago,
        y = baseY;
      while (m < 0) {
        m += 12;
        y--;
      }
      return MONTHS[m] + " ’" + ("0" + (y % 100)).slice(-2);
    };
    const spread = Math.abs(cur) * 0.22 + (cur === 0 ? 1 : 0.5);
    const vAt = (ago: number) =>
      cur - dir * spread * (ago / 24) + Math.sin(ago * 0.9) * spread * 0.08;
    const agos = (SAMPLE_MAP[histRange] ?? SAMPLE_MAP["6"] ?? [0])
      .slice()
      .reverse();
    const vals = agos.map(vAt);
    const labels = agos.map(monLabel);
    const n = vals.length;
    vals[n - 1] = cur;
    const W = 520,
      H = 150,
      padL = 12,
      padR = 12,
      padT = 16,
      padB = 18;
    const lo = Math.min(...vals),
      hi = Math.max(...vals);
    const pdv = (hi - lo) * 0.32 || Math.abs(hi) * 0.12 || 1;
    const yMin = lo - pdv,
      yMax = hi + pdv;
    const xx = (i: number) =>
      n <= 1 ? W / 2 : padL + (W - padL - padR) * (i / (n - 1));
    const yy = (v: number) =>
      padT + (H - padT - padB) * (1 - (v - yMin) / (yMax - yMin || 1));
    const pts = vals.map((v, i) => ({
      x: +xx(i).toFixed(1),
      y: +yy(v).toFixed(1),
    }));
    const chartLine =
      n <= 1
        ? ""
        : pts.map((p, i) => (i ? "L" : "M") + p.x + " " + p.y).join(" ");
    const chartArea =
      n <= 1
        ? ""
        : chartLine +
          " L " +
          pts[n - 1]!.x +
          " " +
          (H - padB) +
          " L " +
          pts[0]!.x +
          " " +
          (H - padB) +
          " Z";
    const dots = pts.map((p, i) => ({
      cx: p.x,
      cy: p.y,
      r: i === n - 1 ? 4.5 : 3,
      fill: i === n - 1 ? s3.accent : "var(--surface-card)",
      stroke: s3.accent,
    }));
    const rnums = refNumsOf(om.ref);
    const isRange = String(om.ref).indexOf("–") >= 0;
    let refY = 0,
      hasRefLine = false;
    if (
      !isRange &&
      rnums.length === 1 &&
      rnums[0]! >= yMin &&
      rnums[0]! <= yMax
    ) {
      refY = +yy(rnums[0]!).toFixed(1);
      hasRefLine = true;
    }
    const refPool = rnums.length ? rnums.concat([cur]) : [cur];
    const scaleMax = Math.max(...refPool) * 1.5 || 1;
    const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
    const GC = 84,
      GCY = 90,
      GR = 66;
    const Apt = (f: number): [number, number] => {
      const th = ((180 - 180 * clamp01(f)) * Math.PI) / 180;
      return [GC + GR * Math.cos(th), GCY - GR * Math.sin(th)];
    };
    const arcP = (f0: number, f1: number) => {
      const a = Apt(f0),
        b = Apt(f1);
      return (
        "M " +
        a[0].toFixed(1) +
        " " +
        a[1].toFixed(1) +
        " A " +
        GR +
        " " +
        GR +
        " 0 0 1 " +
        b[0].toFixed(1) +
        " " +
        b[1].toFixed(1)
      );
    };
    const gaugeTrack = arcP(0, 1);
    const zc = {
      good: "var(--vital-400)",
      warn: "var(--amber-400)",
      bad: "var(--rose-400)",
    };
    let zoneDefs: [number, number, string][];
    if (isRange && rnums.length >= 2) {
      const fa = clamp01(rnums[0]! / scaleMax),
        fb = clamp01(rnums[1]! / scaleMax);
      zoneDefs = [
        [0, fa, zc.warn],
        [fa, fb, zc.good],
        [fb, 1, zc.warn],
      ];
    } else if (!rnums.length) {
      zoneDefs = [[0, 1, zc.good]];
    } else {
      const fx = clamp01(rnums[0]! / scaleMax);
      const greater =
        String(om.ref).indexOf(">") >= 0 || String(om.ref).indexOf("≥") >= 0;
      if (greater) {
        const fw = clamp01(fx * 0.7);
        zoneDefs = [
          [0, fw, zc.bad],
          [fw, fx, zc.warn],
          [fx, 1, zc.good],
        ];
      } else {
        const fw = clamp01(fx + (1 - fx) * 0.4);
        zoneDefs = [
          [0, fx, zc.good],
          [fx, fw, zc.warn],
          [fw, 1, zc.bad],
        ];
      }
    }
    const zones = zoneDefs
      .filter((z) => z[1] > z[0] + 0.002)
      .map((z) => ({ d: arcP(z[0], z[1]), c: z[2] }));
    const fv = clamp01(cur / scaleMax);
    const nth = ((180 - 180 * fv) * Math.PI) / 180;
    const needleX = +(GC + (GR - 4) * Math.cos(nth)).toFixed(1);
    const needleY = +(GCY - (GR - 4) * Math.sin(nth)).toFixed(1);
    const numPart = (String(om.value).match(/-?\d+(?:[.,]\d+)?(?:\/\d+)?/) || [
      om.value,
    ])[0];
    const unitPart = String(om.value).replace(numPart, "").trim();
    const rows = vals
      .map((v, i) => {
        const prev = i > 0 ? vals[i - 1] : null;
        const d = prev == null ? 0 : v - prev;
        const ok = inRef(v, om.ref);
        const ad = Math.abs(d);
        return {
          date: labels[i],
          val: (Math.round(v * 10) / 10).toString().replace(".", ","),
          delta:
            prev == null
              ? "—"
              : (d > 0.05 ? "▲ " : d < -0.05 ? "▼ " : "–") +
                (ad < 0.05
                  ? ""
                  : (Math.round(ad * 10) / 10).toString().replace(".", ",")),
          dotColor: ok ? "var(--vital-500)" : "var(--amber-500)",
          highlight: i === n - 1,
        };
      })
      .reverse();
    return {
      name: om.marker,
      cat: om.cat,
      ref: om.ref,
      value: om.value,
      statLabel: s3.label,
      accent: s3.accent,
      statTxt: s3.txt,
      gaugeTrack,
      zones,
      needleX,
      needleY,
      ringVal: numPart,
      ringUnit: unitPart,
      chartLine,
      chartArea,
      dots,
      hasRefLine,
      refY,
      refCaption: "Referenz " + om.ref + (isRange ? " (Intervall)" : ""),
      dateLabels: labels,
      rows,
      summaryTxt:
        (dir > 0
          ? "Tendenz steigend"
          : dir < 0
            ? "Tendenz fallend"
            : "Stabil") + " über die letzten Messungen.",
    };
  }, [openMarker, histRange]);

  const detTab = (active: boolean): CSSProperties => ({
    padding: "13px 4px",
    marginRight: "20px",
    fontSize: "13px",
    fontWeight: active ? 600 : 500,
    color: active ? "var(--brand)" : "var(--text-muted)",
    borderBottom: "2px solid " + (active ? "var(--brand)" : "transparent"),
    whiteSpace: "nowrap",
    cursor: "pointer",
  });

  return (
    <>
      <button
        onClick={() => router.push("/patients")}
        type="button"
        className="vb-crumblink"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "7px",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          marginBottom: "18px",
          fontFamily: "var(--font-mono)",
          fontSize: "12px",
          color: "var(--text-muted)",
          letterSpacing: "0.03em",
        }}
      >
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
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Zurück zu Patienten
      </button>

      {/* identity */}
      <div
        style={{ ...cardStyle, padding: "22px 24px 0", marginBottom: "20px" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "24px",
            flexWrap: "wrap",
            paddingBottom: "18px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
              flex: "1 1 300px",
              minWidth: 0,
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                flexShrink: 0,
                borderRadius: "var(--radius-md)",
                background: "var(--brand-soft)",
                border: "1px solid var(--brand-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-mono)",
                fontSize: "17px",
                fontWeight: 600,
                color: "var(--teal-600)",
              }}
            >
              {initials(name)}
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "5px",
                  flexWrap: "wrap",
                }}
              >
                <h1
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "var(--text-2xl)",
                    letterSpacing: "var(--tracking-tight)",
                    color: "var(--text-strong)",
                    margin: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  {name}
                </h1>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "3px 11px",
                    borderRadius: "999px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--vital-500)",
                    background: "rgba(20,169,130,0.12)",
                    border: "1px solid rgba(20,169,130,0.30)",
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "999px",
                      background: "var(--vital-500)",
                    }}
                  />
                  Freigegeben
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  flexWrap: "wrap",
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                }}
              >
                <span>{id}</span>
                <span
                  style={{
                    width: "3px",
                    height: "3px",
                    borderRadius: "999px",
                    background: "var(--border-strong)",
                  }}
                />
                <span>{age} Jahre</span>
                <span
                  style={{
                    width: "3px",
                    height: "3px",
                    borderRadius: "999px",
                    background: "var(--border-strong)",
                  }}
                />
                <span>Bericht · v1</span>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: "10px", flexShrink: 0 }}>
            <button
              type="button"
              className="vb-btn-sec"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                height: "40px",
                padding: "0 15px",
                whiteSpace: "nowrap",
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
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <path d="M14 2v6h6" />
              </svg>
              Quelldokumente
            </button>
            <button
              type="button"
              className="vb-btn-sec"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                height: "40px",
                padding: "0 15px",
                whiteSpace: "nowrap",
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
              Mehr
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            gap: "4px",
            borderTop: "1px solid var(--border-subtle)",
            overflowX: "auto",
          }}
        >
          <div style={detTab(true)}>Assessment</div>
          {["Laborwerte", "Verlauf", "Dokumente", "Bericht"].map((t, i, a) => (
            <div
              key={t}
              className="vb-tab-text"
              style={{
                ...detTab(false),
                marginRight: i === a.length - 1 ? 0 : "20px",
              }}
            >
              {t}
            </div>
          ))}
        </div>
      </div>

      {/* domain cards (no A–E grade — ADR-0005) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(258px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        {DOMAINS.map((d) => {
          const sel = d.key === domainKey;
          return (
            <div
              key={d.key}
              className="vb-domaincard"
              {...clickable(
                () => setDomainKey(d.key),
                `Domäne ${d.name} auswählen`,
              )}
              aria-pressed={sel}
              style={{
                background: "var(--surface-card)",
                borderRadius: "var(--radius-lg)",
                padding: "16px 18px",
                border:
                  "1.5px solid " +
                  (sel ? "var(--brand)" : "var(--border-subtle)"),
                boxShadow: sel
                  ? "0 0 0 3px var(--brand-soft)"
                  : "var(--shadow-xs)",
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: "10px",
                  marginBottom: "11px",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "var(--text-md)",
                    color: "var(--text-strong)",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {d.name}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "var(--text-faint)",
                    flexShrink: 0,
                    marginTop: "4px",
                  }}
                >
                  Entwurf
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Follow-up-Adäquanz: {d.followUp}
              </div>
              {sel ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    marginTop: "10px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--vital-500)",
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  Biomarker im Beobachtungsnachweis
                </div>
              ) : (
                <div
                  style={{
                    marginTop: "10px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--brand)",
                  }}
                >
                  Biomarker ansehen ({d.count})
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Beobachtungsnachweis */}
      <div style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}>
        <div style={{ padding: "18px 22px 6px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "9px",
              marginBottom: "9px",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "27px",
                height: "27px",
                flexShrink: 0,
                borderRadius: "8px",
                background:
                  "color-mix(in oklch, var(--rose-400) 17%, var(--surface-card))",
              }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="var(--rose-500)"
                stroke="none"
              >
                <path d="M12 21s-7.6-4.7-10-9.4C.3 8.2 2 5 5.2 5c2 0 3.3 1.1 4 2.4C9.9 6.1 11.2 5 13.2 5 16.4 5 18.1 8.2 16.4 11.6 14 16.3 12 21 12 21z" />
              </svg>
            </span>
            <h3
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 800,
                fontSize: "var(--text-xl)",
                color: "var(--text-strong)",
                margin: 0,
                letterSpacing: "-0.02em",
              }}
            >
              {curHealth}
            </h3>
          </div>
          <p
            style={{
              fontSize: "13px",
              lineHeight: 1.6,
              color: "var(--text-body)",
              margin: 0,
              maxWidth: "94ch",
              textWrap: "pretty",
            }}
          >
            {curDesc}
          </p>
        </div>

        <div style={{ overflowX: "auto", marginTop: "10px" }}>
          <div style={{ minWidth: "720px" }}>
            {evidenceGroups.map((g) => (
              <div key={g.key}>
                <div
                  style={{
                    padding: "9px 22px",
                    background: "var(--surface-sunken)",
                    borderTop: "1px solid var(--border-subtle)",
                    borderBottom: "1px solid var(--border-subtle)",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10.5px",
                      fontWeight: 700,
                      letterSpacing: "0.12em",
                      textTransform: "uppercase",
                      color: "var(--text-muted)",
                    }}
                  >
                    {g.bandLabel}
                  </span>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: EGRID,
                    alignItems: "center",
                    gap: "14px",
                    padding: "9px 22px",
                    borderBottom: "1px solid var(--border-subtle)",
                  }}
                >
                  <span style={eColLabel}>Marker</span>
                  <span style={eColLabel}>Kategorie</span>
                  <span style={eColLabel}>Wert</span>
                  <span style={eColLabel}>Referenz</span>
                  <span style={eColLabel}>Status</span>
                  <span style={{ ...eColLabel, textAlign: "right" }}>
                    Trend
                  </span>
                </div>
                {g.items.map((o, i) => {
                  const s = STAT3[o.stat] ?? STAT3.normal;
                  return (
                    <div
                      key={o.marker + i}
                      className="vb-erow"
                      {...clickable(
                        () => openObs(o),
                        `Marker ${o.marker} öffnen`,
                      )}
                      style={{
                        display: "grid",
                        gridTemplateColumns: EGRID,
                        alignItems: "center",
                        gap: "14px",
                        padding: "13px 22px",
                        borderBottom: "1px solid var(--border-subtle)",
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "13.5px",
                          fontWeight: 600,
                          color: "var(--text-strong)",
                          lineHeight: 1.3,
                        }}
                      >
                        {o.marker}
                      </span>
                      <span>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "2px 9px",
                            borderRadius: "999px",
                            fontFamily: "var(--font-text)",
                            fontSize: "11px",
                            fontWeight: 600,
                            color: "var(--text-muted)",
                            background: "var(--surface-sunken)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          {o.cat}
                        </span>
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "13px",
                          fontWeight: 600,
                          color: "var(--text-strong)",
                        }}
                      >
                        {o.value}
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "12px",
                          color: "var(--text-muted)",
                        }}
                      >
                        {o.ref || "—"}
                      </span>
                      <span>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "3px 11px",
                            borderRadius: "999px",
                            fontFamily: "var(--font-text)",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: s.txt,
                            background:
                              "color-mix(in oklch, " +
                              s.accent +
                              " 17%, var(--surface-card))",
                            border:
                              "1px solid color-mix(in oklch, " +
                              s.accent +
                              " 30%, transparent)",
                          }}
                        >
                          <span
                            style={{
                              width: "6px",
                              height: "6px",
                              borderRadius: "999px",
                              flexShrink: 0,
                              background: s.accent,
                            }}
                          />
                          {s.label}
                        </span>
                      </span>
                      <span
                        style={{ display: "flex", justifyContent: "flex-end" }}
                      >
                        <svg
                          width="42"
                          height="18"
                          viewBox="0 0 40 18"
                          fill="none"
                        >
                          <path
                            d={TRD[o.trend] || TRD.flat}
                            stroke={s.accent}
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Audit-Status */}
      <div
        style={{
          ...cardStyle,
          padding: "20px 22px 22px",
          marginBottom: "16px",
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-lg)",
            color: "var(--text-strong)",
            margin: "0 0 3px",
            letterSpacing: "-0.01em",
          }}
        >
          Audit-Status
        </h3>
        <p
          style={{
            fontSize: "12.5px",
            color: "var(--text-muted)",
            margin: "0 0 18px",
          }}
        >
          Fortschritt von Datenerfassung bis Patientenfreigabe (Live-Status).
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            minWidth: "560px",
          }}
        >
          {AUDIT_STEPS.map((s) => (
            <div
              key={s.label}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                textAlign: "center",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", width: "100%" }}
              >
                <div
                  style={{
                    flex: 1,
                    height: "2px",
                    background: s.first ? "transparent" : "var(--teal-300)",
                  }}
                />
                <div
                  style={{
                    width: "26px",
                    height: "26px",
                    flexShrink: 0,
                    borderRadius: "999px",
                    background: "var(--vital-500)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {check(14)}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: "2px",
                    background: s.last ? "transparent" : "var(--teal-300)",
                  }}
                />
              </div>
              <div style={{ marginTop: "9px" }}>
                <div
                  style={{
                    fontSize: "12.5px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                  }}
                >
                  {s.label}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10.5px",
                    color: "var(--text-muted)",
                    marginTop: "2px",
                  }}
                >
                  {s.sub}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* report bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "20px",
          flexWrap: "wrap",
          ...cardStyle,
          padding: "18px 22px",
        }}
      >
        <div style={{ flex: 1, minWidth: "280px" }}>
          <div
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "var(--text-strong)",
            }}
          >
            Bericht v1 · Status: Freigegeben
          </div>
          <div
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              marginTop: "3px",
              maxWidth: "78ch",
            }}
          >
            Die Signatur ist noch nicht an den Freigabe-Lifecycle angebunden
            (Gate G2); sie veröffentlicht keinen Bericht an die Patientin.
          </div>
        </div>
        <div style={{ display: "flex", gap: "10px", flexShrink: 0 }}>
          <button
            type="button"
            className="vb-btn-sec"
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: "40px",
              padding: "0 16px",
              whiteSpace: "nowrap",
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
            Zurückstellen
          </button>
          <button
            type="button"
            className="vb-btn-pri"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              height: "40px",
              padding: "0 18px",
              whiteSpace: "nowrap",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--brand)",
              background: "var(--brand)",
              color: "var(--text-on-brand)",
              fontFamily: "var(--font-text)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 1px 2px rgba(12,18,20,0.12)",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 6L9 17l-5-5" />
            </svg>
            Review signieren
          </button>
        </div>
      </div>

      {/* Marker modal */}
      {modal && (
        <div
          onClick={closeObs}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="vb-marker-title"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "620px",
              maxWidth: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              background: "var(--surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              boxShadow: "var(--shadow-xl)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
                padding: "20px 22px 16px",
                borderBottom: "1px solid var(--border-subtle)",
              }}
            >
              <div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    color: "var(--text-faint)",
                    marginBottom: "6px",
                  }}
                >
                  Marker-Detail · {modal.cat}
                </div>
                <h3
                  id="vb-marker-title"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 800,
                    fontSize: "var(--text-2xl)",
                    color: "var(--text-strong)",
                    margin: 0,
                    letterSpacing: "-0.02em",
                  }}
                >
                  {modal.name}
                </h3>
              </div>
              <button
                type="button"
                ref={closeBtnRef}
                onClick={closeObs}
                aria-label="Schließen"
                className="vb-closebtn"
                style={{
                  width: "34px",
                  height: "34px",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "8px",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--surface-card)",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div style={{ padding: "20px 22px 22px" }}>
              <div
                style={{
                  display: "flex",
                  gap: "24px",
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <div
                  style={{ flexShrink: 0, width: "182px", textAlign: "center" }}
                >
                  <svg
                    viewBox="0 0 168 104"
                    style={{ display: "block", width: "100%", height: "auto" }}
                  >
                    <path
                      d={modal.gaugeTrack}
                      fill="none"
                      stroke="var(--surface-sunken)"
                      strokeWidth="13"
                      strokeLinecap="round"
                    />
                    {modal.zones.map((z, i) => (
                      <path
                        key={i}
                        d={z.d}
                        fill="none"
                        stroke={z.c}
                        strokeWidth="13"
                      />
                    ))}
                    <line
                      x1="84"
                      y1="90"
                      x2={modal.needleX}
                      y2={modal.needleY}
                      stroke="var(--text-strong)"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                    <circle cx="84" cy="90" r="5.5" fill="var(--text-strong)" />
                  </svg>
                  <div style={{ marginTop: "2px", lineHeight: 1 }}>
                    <span
                      style={{
                        fontFamily: "var(--font-display)",
                        fontWeight: 800,
                        fontSize: "24px",
                        color: "var(--text-strong)",
                        letterSpacing: "-0.02em",
                      }}
                    >
                      {modal.ringVal}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--text-muted)",
                        marginLeft: "4px",
                      }}
                    >
                      {modal.ringUnit}
                    </span>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: "190px" }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "4px 12px",
                      borderRadius: "999px",
                      fontFamily: "var(--font-text)",
                      fontSize: "12.5px",
                      fontWeight: 600,
                      color: modal.statTxt,
                      background:
                        "color-mix(in oklch, " +
                        modal.accent +
                        " 17%, var(--surface-card))",
                      border:
                        "1px solid color-mix(in oklch, " +
                        modal.accent +
                        " 30%, transparent)",
                    }}
                  >
                    <span
                      style={{
                        width: "7px",
                        height: "7px",
                        borderRadius: "999px",
                        flexShrink: 0,
                        background: modal.accent,
                      }}
                    />
                    {modal.statLabel}
                  </span>
                  <div
                    style={{
                      marginTop: "13px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "7px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        fontSize: "12.5px",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>
                        Aktueller Wert
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontWeight: 600,
                          color: "var(--text-strong)",
                        }}
                      >
                        {modal.value}
                      </span>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        fontSize: "12.5px",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>
                        Referenz
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          color: "var(--text-body)",
                        }}
                      >
                        {modal.ref}
                      </span>
                    </div>
                  </div>
                  <p
                    style={{
                      margin: "12px 0 0",
                      fontSize: "12.5px",
                      lineHeight: 1.5,
                      color: "var(--text-muted)",
                    }}
                  >
                    {modal.summaryTxt}
                  </p>
                </div>
              </div>
              <div style={{ marginTop: "22px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                    flexWrap: "wrap",
                    marginBottom: "10px",
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      letterSpacing: "0.12em",
                      textTransform: "uppercase",
                      color: "var(--text-faint)",
                      fontWeight: 600,
                    }}
                  >
                    Verlauf
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "3px",
                      background: "var(--surface-sunken)",
                      borderRadius: "999px",
                      padding: "3px",
                    }}
                  >
                    {HIST_TABS.map(([key, label]) => {
                      const active = histRange === key;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setHistRange(key)}
                          className="vb-tab-text"
                          style={{
                            border: "none",
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                            borderRadius: "999px",
                            padding: "5px 11px",
                            fontFamily: "var(--font-text)",
                            fontSize: "11.5px",
                            fontWeight: 600,
                            background: active
                              ? "var(--surface-card)"
                              : "transparent",
                            color: active
                              ? "var(--text-strong)"
                              : "var(--text-muted)",
                            boxShadow: active ? "var(--shadow-xs)" : "none",
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <svg
                  viewBox="0 0 520 150"
                  style={{ display: "block", width: "100%", height: "auto" }}
                >
                  {modal.hasRefLine && (
                    <line
                      x1="12"
                      y1={modal.refY}
                      x2="508"
                      y2={modal.refY}
                      stroke="var(--text-faint)"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                    />
                  )}
                  <path
                    d={modal.chartArea}
                    fill={modal.accent}
                    fillOpacity="0.12"
                  />
                  <path
                    d={modal.chartLine}
                    fill="none"
                    stroke={modal.accent}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  {modal.dots.map((d, i) => (
                    <circle
                      key={i}
                      cx={d.cx}
                      cy={d.cy}
                      r={d.r}
                      fill={d.fill}
                      stroke={d.stroke}
                      strokeWidth="2"
                    />
                  ))}
                </svg>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginTop: "3px",
                    padding: "0 6px",
                  }}
                >
                  {modal.dateLabels.map((dl, i) => (
                    <span
                      key={i}
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "9.5px",
                        color: "var(--text-faint)",
                      }}
                    >
                      {dl}
                    </span>
                  ))}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    color: "var(--text-faint)",
                    marginTop: "8px",
                  }}
                >
                  {modal.refCaption}
                </div>
              </div>
              <div style={{ marginTop: "22px" }}>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    color: "var(--text-faint)",
                    fontWeight: 600,
                    marginBottom: "6px",
                  }}
                >
                  Frühere Tests
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 90px 78px 18px",
                    gap: "14px",
                    padding: "0 4px 8px",
                    borderBottom: "1px solid var(--border-subtle)",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "9.5px",
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: "var(--text-faint)",
                    }}
                  >
                    Datum
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "9.5px",
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: "var(--text-faint)",
                      textAlign: "right",
                    }}
                  >
                    Wert
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "9.5px",
                      letterSpacing: "0.1em",
                      textTransform: "uppercase",
                      color: "var(--text-faint)",
                      textAlign: "right",
                    }}
                  >
                    Δ
                  </span>
                  <span />
                </div>
                {modal.rows.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 90px 78px 18px",
                      alignItems: "center",
                      gap: "14px",
                      padding: "9px 4px",
                      borderBottom: "1px solid var(--border-subtle)",
                      background: r.highlight
                        ? "color-mix(in oklch, " +
                          modal.accent +
                          " 9%, var(--surface-card))"
                        : "transparent",
                    }}
                  >
                    <span
                      style={{ fontSize: "12.5px", color: "var(--text-body)" }}
                    >
                      {r.date}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "12.5px",
                        fontWeight: 600,
                        color: "var(--text-strong)",
                        textAlign: "right",
                      }}
                    >
                      {r.val}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11.5px",
                        color: "var(--text-muted)",
                        textAlign: "right",
                      }}
                    >
                      {r.delta}
                    </span>
                    <span
                      style={{
                        display: "block",
                        width: "7px",
                        height: "7px",
                        borderRadius: "999px",
                        margin: "0 auto",
                        background: r.dotColor,
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
