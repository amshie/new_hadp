"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { AddPatientDialog } from "@/components/vitabahn/AddPatientDialog";
import { clickable } from "@/components/vitabahn/interactive";
import type {
  CoverageView,
  OverviewView,
  StatusSnapshotView,
  ThroughputChartView,
  WorkRowView,
} from "@/lib/presenters/dashboard";

import { ThroughputTile } from "./ThroughputTile";

// VitaBahn Übersicht (ADR-0006, real-data path). Consumes the governed OverviewView (real,
// deterministic counts + work-list over the API). Review-Durchsatz (per-day report-version
// throughput) and Datenlage (observation coverage) are now real, tenant-scoped tiles; the activity
// feed and imports panel still have NO backend source and stay honest gated states (deferred slices).

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
const WORK_GRID = "minmax(220px,2fr) minmax(160px,1.4fr) 140px 110px";

function GatedPanel({ title, reason }: { title: string; reason: string }) {
  return (
    <div
      style={{
        ...cardStyle,
        padding: "20px 22px",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <h3 style={sectionTitle}>{title}</h3>
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "120px",
          textAlign: "center",
          padding: "16px 8px",
        }}
      >
        <div>
          <div
            style={{
              display: "inline-flex",
              marginBottom: "8px",
              width: "32px",
              height: "32px",
              borderRadius: "999px",
              background: "var(--surface-sunken)",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg
              aria-hidden="true"
              focusable="false"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--text-faint)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v4l2 2" />
            </svg>
          </div>
          <div
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              maxWidth: "34ch",
              margin: "0 auto",
              lineHeight: 1.5,
            }}
          >
            {reason}
          </div>
        </div>
      </div>
    </div>
  );
}

// Real status snapshot (current bestand by latest report status). A momentaufnahme, NOT a
// throughput time series — the heading says so. Bars are share-of-total over real worklist rows.
function StatusSnapshotTile({ snapshot }: { snapshot: StatusSnapshotView }) {
  return (
    <div style={{ ...cardStyle, padding: "20px 22px" }}>
      <h3 style={sectionTitle}>Berichtsstatus</h3>
      <p
        style={{
          fontSize: "12.5px",
          color: "var(--text-muted)",
          margin: "0 0 16px",
        }}
      >
        Aktueller Bestand · Momentaufnahme · {snapshot.total}{" "}
        {snapshot.total === 1 ? "Patient" : "Patienten"}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {snapshot.buckets.map((b) => (
          <div key={b.key}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: "5px",
              }}
            >
              <span style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
                {b.label}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--text-strong)",
                }}
              >
                {b.count}
              </span>
            </div>
            <div
              style={{
                height: "7px",
                borderRadius: "999px",
                background: "var(--surface-sunken)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.round(b.share * 100)}%`,
                  background: b.color,
                  borderRadius: "999px",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Real tenant-wide observation coverage (ADR-0006). Counts/freshness, explicitly NOT a quality
// score — the caption says so. The donut shows the PUBLISHED share (a workflow state), never a
// merged "quality %".
function CoverageBar({
  label,
  pct,
  detail,
  color,
}: {
  label: string;
  pct: number;
  detail: string;
  color: string;
}) {
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "5px",
        }}
      >
        <span style={{ fontSize: "12.5px", color: "var(--text-body)" }}>
          {label}
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            fontWeight: 600,
            color: "var(--text-strong)",
          }}
        >
          {detail}
        </span>
      </div>
      <div
        style={{
          height: "7px",
          borderRadius: "999px",
          background: "var(--surface-sunken)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: "999px",
          }}
        />
      </div>
    </div>
  );
}

function CoverageTile({ coverage }: { coverage: CoverageView }) {
  return (
    <div style={{ ...cardStyle, padding: "20px 22px" }}>
      <h3 style={sectionTitle}>Datenlage</h3>
      <p
        style={{
          fontSize: "12.5px",
          color: "var(--text-muted)",
          margin: "0 0 16px",
        }}
      >
        Abdeckung über {coverage.total} reale{" "}
        {coverage.total === 1 ? "Beobachtung" : "Beobachtungen"} · keine
        Qualitätsbewertung
      </p>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "18px",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: "118px",
            height: "118px",
            borderRadius: "50%",
            flexShrink: 0,
            background: `conic-gradient(var(--vital-500) ${coverage.publishedPct}%, var(--surface-sunken) ${coverage.publishedPct}% 100%)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: "88px",
              height: "88px",
              borderRadius: "50%",
              background: "var(--surface-card)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "26px",
                lineHeight: 1,
                color: "var(--text-strong)",
              }}
            >
              {coverage.publishedPct}%
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "9px",
                letterSpacing: "0.1em",
                color: "var(--text-faint)",
                marginTop: "4px",
              }}
            >
              PUBLIZIERT
            </div>
          </div>
        </div>
        <div
          style={{
            flex: 1,
            minWidth: "150px",
            display: "flex",
            flexDirection: "column",
            gap: "11px",
          }}
        >
          <CoverageBar
            label="Publiziert"
            pct={coverage.publishedPct}
            detail={`${coverage.published}/${coverage.total}`}
            color="var(--vital-500)"
          />
          <CoverageBar
            label="Mit Referenzintervall"
            pct={coverage.referencePct}
            detail={`${coverage.withReference}/${coverage.total}`}
            color="var(--brand)"
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "12.5px",
            }}
          >
            <span style={{ color: "var(--text-body)" }}>
              Neueste Beobachtung
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-muted)",
              }}
            >
              {coverage.latestAgeLabel}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

const TABS: { key: string; label: string }[] = [
  { key: "offen", label: "Offene Reviews" },
  { key: "genehmigt", label: "Genehmigt" },
  { key: "freigegeben", label: "Freigegeben" },
  { key: "alle", label: "Alle" },
];

function rowGroup(r: WorkRowView): string {
  if (r.statusLabel === "In Prüfung") return "offen";
  if (r.statusLabel === "Genehmigt") return "genehmigt";
  if (r.statusLabel === "Freigegeben") return "freigegeben";
  return "andere";
}

export function OverviewContent({
  view,
  coverage,
  throughput,
}: {
  view: OverviewView;
  coverage: CoverageView | null;
  throughput: ThroughputChartView | null;
}) {
  const router = useRouter();
  const [tab, setTab] = useState("alle");
  const [term, setTerm] = useState("");

  const counts = useMemo(
    () => ({
      offen: view.kpis.openReviews,
      genehmigt: view.kpis.approved,
      freigegeben: view.kpis.released,
      alle: view.rows.length,
    }),
    [view],
  );

  const visible = useMemo(() => {
    const q = term.toLowerCase();
    return view.rows.filter((r) => {
      const matchTab = tab === "alle" || rowGroup(r) === tab;
      const hay = `${r.name} ${r.ref} ${r.assessment}`.toLowerCase();
      return matchTab && hay.includes(q);
    });
  }, [view.rows, tab, term]);

  const kpis: {
    value: number;
    label: string;
    help: string;
    iconBg: string;
    icon: ReactNode;
  }[] = [
    {
      value: view.kpis.openReviews,
      label: "Offene Reviews",
      help: "Klinische Prüfung ausstehend",
      iconBg: "rgba(201,136,28,0.12)",
      icon: (
        <svg
          aria-hidden="true"
          focusable="false"
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
    },
    {
      value: view.kpis.approved,
      label: "Genehmigt",
      help: "Warten auf ärztliche Freigabe",
      iconBg: "rgba(63,164,201,0.12)",
      icon: (
        <svg
          aria-hidden="true"
          focusable="false"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--sky-400)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <path d="M22 4L12 14.01l-3-3" />
        </svg>
      ),
    },
    {
      value: view.kpis.released,
      label: "Freigegeben",
      help: "An die Patientin freigegeben",
      iconBg: "var(--brand-soft)",
      icon: (
        <svg
          aria-hidden="true"
          focusable="false"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--teal-600)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      ),
    },
    {
      value: view.kpis.patients,
      label: "Patienten",
      help: "Tenant-bezogen · RLS-geschützt",
      iconBg: "var(--brand-soft)",
      icon: (
        <svg
          aria-hidden="true"
          focusable="false"
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
    },
  ];

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
      <div
        style={{
          marginBottom: "28px",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "20px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ minWidth: 0 }}>
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
            Übersicht
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
              {view.kpis.openReviews}{" "}
              {view.kpis.openReviews === 1 ? "Review" : "Reviews"}
            </span>{" "}
            {view.kpis.openReviews === 1 ? "wartet" : "warten"} auf Ihre
            Prüfung. Quellengebundene Entwürfe müssen vor jeder Freigabe geprüft
            werden. Synthetische Beispieldaten.
          </p>
        </div>
        <AddPatientDialog />
      </div>

      {/* KPI ROW (real counts) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(212px, 1fr))",
          gap: "16px",
          marginBottom: "16px",
        }}
      >
        {kpis.map((k) => (
          <div key={k.label} style={{ ...cardStyle, padding: "18px" }}>
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
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "34px",
                lineHeight: 1,
                color: "var(--text-strong)",
                letterSpacing: "-0.02em",
                marginBottom: "6px",
              }}
            >
              {k.value}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {k.help}
            </div>
          </div>
        ))}
      </div>

      {/* WORK LIST (real worklist) */}
      <div style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}>
        <div style={{ padding: "20px 22px 0" }}>
          <h3 style={sectionTitle}>Klinische Arbeitsliste</h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: "0 0 16px",
            }}
          >
            Nach Berichtsstatus · keine automatische Diagnose oder
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
                const c =
                  t.key === "alle"
                    ? counts.alle
                    : (counts[t.key as keyof typeof counts] ?? 0);
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
          </div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <div style={{ minWidth: "720px" }}>
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
              <span style={colLabel}>Status</span>
              <span style={{ ...colLabel, textAlign: "right" }}>
                Aktualisiert
              </span>
            </div>
            {visible.map((r) => {
              const sm = r.statusBadge;
              return (
                <div
                  key={r.patientId}
                  className="vb-row"
                  {...clickable(
                    () => router.push(`/patients/${r.patientId}`),
                    `Patient ${r.name}, ${r.ref} öffnen`,
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
                      {r.initials}
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
                        {r.ref}
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
                    {r.assessment}
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
                    {r.updatedLabel}
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

      {/* Row 1 — real Review-Durchsatz (wide) + Datenlage coverage */}
      <div className="vb-dash-split" style={{ marginBottom: "16px" }}>
        {throughput ? (
          <ThroughputTile view={throughput} />
        ) : (
          <GatedPanel
            title="Review-Durchsatz"
            reason="Durchsatz-Zeitreihe ist derzeit nicht abrufbar. Eigener Backend-Slice (report_versions nach Status)."
          />
        )}
        {coverage ? (
          <CoverageTile coverage={coverage} />
        ) : (
          <GatedPanel
            title="Datenlage"
            reason="Abdeckung über die Beobachtungen ist derzeit nicht abrufbar. Pro Patient zeigt die Detailansicht die reale Datenlage."
          />
        )}
      </div>

      {/* Row 2 — real Berichtsstatus snapshot + still-gated panels (deferred backend slices) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "16px",
        }}
      >
        <StatusSnapshotTile snapshot={view.statusSnapshot} />
        <GatedPanel
          title="Letzte Aktivität"
          reason="Audit-Feed benötigt einen tenant-scoped Lese-Endpoint über die Append-only-Events. Eigener Backend-Slice."
        />
        <GatedPanel
          title="Importe & Quellen"
          reason="Import-Status benötigt einen Lese-Endpoint über import_jobs. Eigener Backend-Slice."
        />
      </div>
    </>
  );
}
