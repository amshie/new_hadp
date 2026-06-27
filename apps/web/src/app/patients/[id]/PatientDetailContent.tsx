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
import { lageLabel } from "@/lib/lageCopy";
import type { ReferencePosition } from "@/lib/referencePosition";
import type { DetailView } from "@/lib/presenters/patientDetail";
import type { MarkerView } from "@/lib/presenters/review";

// VitaBahn patient Detail (ADR-0005, real-data path). Consumes the governed DetailView
// (presentReview + a real data-completeness stat). NO A–E grade (doctrine). Observation Status
// is the verdict-free positional Lage (Über/Unter Referenz · Im Intervall · Keine Referenz),
// NOT a Normal/Grenzwertig/Auffällig verdict — that has no real source and crosses the MDR
// boundary. The marker modal uses the lab-only reference bar, not a heuristic severity gauge.

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
};
const colLabel: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "9.5px",
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--text-faint)",
  fontWeight: 500,
};
const EGRID =
  "minmax(150px,1.6fr) 110px minmax(96px,0.9fr) 96px minmax(150px,1.2fr) 132px";

function statusVita(
  status: string,
  label: string,
): {
  fg: string;
  bg: string;
  bd: string;
  text: string;
} {
  if (status === "released")
    return {
      fg: "var(--vital-500)",
      bg: "rgba(20,169,130,0.12)",
      bd: "rgba(20,169,130,0.30)",
      text: label,
    };
  if (status === "approved")
    return {
      fg: "var(--sky-400)",
      bg: "rgba(63,164,201,0.12)",
      bd: "rgba(63,164,201,0.30)",
      text: label,
    };
  if (status === "draft_generated" || status === "draft_edited")
    return {
      fg: "var(--amber-500)",
      bg: "rgba(201,136,28,0.12)",
      bd: "rgba(201,136,28,0.30)",
      text: label,
    };
  if (status === "rejected")
    return {
      fg: "var(--rose-500)",
      bg: "rgba(194,74,74,0.12)",
      bd: "rgba(194,74,74,0.30)",
      text: label,
    };
  return {
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
    text: "Kein Entwurf",
  };
}

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

function initialsOf(name: string): string {
  return (name.match(/[A-ZÀ-Þ]/g) || [name[0] ?? "–"]).slice(0, 2).join("");
}

function ReferenceBar({ marker }: { marker: MarkerView }) {
  const bar = marker.lageBar;
  if (!bar.hasScale)
    return (
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "10.5px",
          color: "var(--text-faint)",
        }}
      >
        keine Skala
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
      {marker.referenceRange && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            color: "var(--text-faint)",
            marginTop: "3px",
          }}
        >
          Ref {marker.referenceRange}
        </div>
      )}
    </div>
  );
}

function LagePill({ pos }: { pos: ReferencePosition }) {
  const l = lageLabel(pos);
  const c = lageVita(pos);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "3px 10px",
        borderRadius: "999px",
        fontFamily: "var(--font-text)",
        fontSize: "11.5px",
        fontWeight: 600,
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

export function PatientDetailContent({ view }: { view: DetailView }) {
  const router = useRouter();
  const { review, completeness } = view;
  const domains = review.domains;

  const firstWithMarkers =
    domains.find((d) => d.markerCodes.length > 0)?.domainAxis ??
    domains[0]?.domainAxis ??
    "";
  const [domainAxis, setDomainAxis] = useState(firstWithMarkers);
  const [openMarker, setOpenMarker] = useState<MarkerView | null>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const openObs = (m: MarkerView) => {
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    setOpenMarker(m);
  };
  const closeObs = () => setOpenMarker(null);

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

  const curDomain = domains.find((d) => d.domainAxis === domainAxis) ?? null;
  const evidence = useMemo(() => {
    if (!curDomain) return [];
    const codes = new Set(curDomain.markerCodes);
    return review.markers.filter(
      (m) => codes.has(m.code) || m.primaryDomainLabel === curDomain.axisLabel,
    );
  }, [curDomain, review.markers]);

  const sb = statusVita(review.status, review.statusLabel);
  const idBadge = sb;

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
          aria-hidden="true"
          focusable="false"
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
              {initialsOf(review.patientName)}
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
                  {review.patientName}
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
                    color: idBadge.fg,
                    background: idBadge.bg,
                    border: "1px solid " + idBadge.bd,
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "999px",
                      background: idBadge.fg,
                    }}
                  />
                  {idBadge.text}
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
                <span>{review.ref}</span>
                <span
                  style={{
                    width: "3px",
                    height: "3px",
                    borderRadius: "999px",
                    background: "var(--border-strong)",
                  }}
                />
                <span>{review.ageProfile}</span>
                <span
                  style={{
                    width: "3px",
                    height: "3px",
                    borderRadius: "999px",
                    background: "var(--border-strong)",
                  }}
                />
                <span>
                  {review.status === "none"
                    ? "Kein Bericht"
                    : `Bericht · v${review.versionNo}`}
                </span>
              </div>
            </div>
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
          {["Laborwerte", "Verlauf", "Bericht"].map((t, i, a) => (
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

      {/* data completeness (real, deterministic — the compliant replacement for the comp's quality gauge) */}
      <div style={{ ...cardStyle, padding: "16px 22px", marginBottom: "20px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h3
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: "var(--text-md)",
                color: "var(--text-strong)",
                margin: "0 0 2px",
                letterSpacing: "-0.01em",
              }}
            >
              Datenlage
            </h3>
            <p
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                margin: 0,
              }}
            >
              Deterministisch aus den Beobachtungen · keine klinische
              Qualitätsbewertung.
            </p>
          </div>
          <div style={{ display: "flex", gap: "26px", flexWrap: "wrap" }}>
            {[
              { v: String(completeness.total), l: "Beobachtungen" },
              {
                v: `${completeness.published}/${completeness.total}`,
                l: "veröffentlicht",
              },
              {
                v: `${completeness.withReference}/${completeness.total}`,
                l: "mit Referenz",
              },
              {
                v:
                  completeness.latestAgeDays == null
                    ? "—"
                    : completeness.latestAgeDays === 0
                      ? "heute"
                      : `${completeness.latestAgeDays} T`,
                l: "letzte Messung",
              },
            ].map((s) => (
              <div key={s.l}>
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 700,
                    fontSize: "var(--text-lg)",
                    color: "var(--text-strong)",
                  }}
                >
                  {s.v}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10.5px",
                    color: "var(--text-muted)",
                  }}
                >
                  {s.l}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* domain cards (no A–E grade — doctrine) */}
      {domains.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(258px, 1fr))",
            gap: "14px",
            marginBottom: "20px",
          }}
        >
          {domains.map((d) => {
            const sel = d.domainAxis === domainAxis;
            return (
              <div
                key={d.domainAxis}
                className="vb-domaincard"
                {...clickable(
                  () => setDomainAxis(d.domainAxis),
                  `Domäne ${d.axisLabel} auswählen`,
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
                    {d.axisLabel}
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
                    {d.reviewed ? "Geprüft" : "Entwurf"}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Follow-up-Adäquanz: {d.adequacyLabel}
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
                      aria-hidden="true"
                      focusable="false"
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
                    Biomarker ansehen ({d.markerCodes.length})
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div
          style={{
            ...cardStyle,
            padding: "28px 22px",
            marginBottom: "20px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-md)",
              color: "var(--text-strong)",
              marginBottom: "4px",
            }}
          >
            Keine Interpretation vorhanden
          </div>
          <div style={{ fontSize: "12.5px", color: "var(--text-muted)" }}>
            Für diese Patientin liegt noch kein Interpretationslauf vor.
          </div>
        </div>
      )}

      {/* Beobachtungsnachweis (real observations, positional Lage status) */}
      <div style={{ ...cardStyle, marginBottom: "16px", overflow: "hidden" }}>
        <div style={{ padding: "18px 22px 6px" }}>
          <h3
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: "var(--text-xl)",
              color: "var(--text-strong)",
              margin: "0 0 3px",
              letterSpacing: "-0.02em",
            }}
          >
            Beobachtungsnachweis{curDomain ? ` · ${curDomain.axisLabel}` : ""}
          </h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: 0,
              maxWidth: "94ch",
            }}
          >
            Quellengebundene Beobachtungen · Lage relativ zum
            Quellreferenzintervall (keine Diagnose, keine Bewertung).
          </p>
        </div>
        <div style={{ overflowX: "auto", marginTop: "10px" }}>
          <div style={{ minWidth: "760px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: EGRID,
                alignItems: "center",
                gap: "14px",
                padding: "9px 22px",
                borderTop: "1px solid var(--border-subtle)",
                borderBottom: "1px solid var(--border-subtle)",
                background: "var(--surface-sunken)",
              }}
            >
              <span style={colLabel}>Marker</span>
              <span style={colLabel}>Kategorie</span>
              <span style={colLabel}>Wert</span>
              <span style={colLabel}>Δ</span>
              <span style={colLabel}>Lage z. Referenz</span>
              <span style={colLabel}>Referenzlage</span>
            </div>
            {evidence.map((m, i) => (
              <div
                key={m.code + m.name + i}
                className="vb-erow"
                {...clickable(() => openObs(m), `Marker ${m.name} öffnen`)}
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
                  {m.name}
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
                    {m.primaryDomainLabel ?? "—"}
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
                  {m.current}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "12px",
                    color: "var(--text-muted)",
                  }}
                >
                  {m.change}
                </span>
                <span>
                  <LagePill pos={m.lagePosition} />
                </span>
                <span>
                  <ReferenceBar marker={m} />
                </span>
              </div>
            ))}
            {evidence.length === 0 && (
              <div
                style={{
                  padding: "28px 22px",
                  textAlign: "center",
                  fontSize: "13px",
                  color: "var(--text-muted)",
                }}
              >
                Keine Beobachtungen in dieser Domäne.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Audit stepper (real, from report status) */}
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
          Fortschritt von Datenerfassung bis Patientenfreigabe (aus dem
          Berichtsstatus abgeleitet).
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            minWidth: "560px",
          }}
        >
          {review.auditSteps.map((s, i, a) => {
            const done = s.state === "done";
            const active = s.state === "active";
            const dotBg = done
              ? "var(--vital-500)"
              : active
                ? "var(--amber-400)"
                : "var(--surface-sunken)";
            const dotFg = done || active ? "#fff" : "var(--text-faint)";
            return (
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
                  style={{
                    display: "flex",
                    alignItems: "center",
                    width: "100%",
                  }}
                >
                  <div
                    style={{
                      flex: 1,
                      height: "2px",
                      background: i === 0 ? "transparent" : "var(--teal-300)",
                    }}
                  />
                  <div
                    style={{
                      width: "26px",
                      height: "26px",
                      flexShrink: 0,
                      borderRadius: "999px",
                      background: dotBg,
                      color: dotFg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {done ? (
                      <svg
                        aria-hidden="true"
                        focusable="false"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#fff"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                    ) : (
                      s.dot
                    )}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      height: "2px",
                      background:
                        i === a.length - 1 ? "transparent" : "var(--teal-300)",
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
            );
          })}
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
            {review.status === "none"
              ? "Kein Berichtsentwurf"
              : `Bericht v${review.versionNo} · Status: ${idBadge.text}`}
          </div>
          <div
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              marginTop: "3px",
              maxWidth: "82ch",
            }}
          >
            Freigabe & Signatur laufen über die autoritative Review-Ansicht
            (rollen- und einwilligungsgebunden); hier werden sie nur angezeigt.
          </div>
        </div>
        {view.reportLink && (
          <a
            href={view.reportLink}
            className="vb-btn-next"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
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
              textDecoration: "none",
            }}
          >
            Zur Review-Ansicht
            <svg
              aria-hidden="true"
              focusable="false"
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
          </a>
        )}
      </div>

      {/* Marker modal — compliant (lab reference bar + positional Lage; no severity gauge) */}
      {openMarker && (
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
              width: "560px",
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
                  Marker-Detail ·{" "}
                  {openMarker.primaryDomainLabel ?? openMarker.code}
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
                  {openMarker.name}
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
                  aria-hidden="true"
                  focusable="false"
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
                  alignItems: "center",
                  gap: "12px",
                  flexWrap: "wrap",
                  marginBottom: "16px",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "22px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                  }}
                >
                  {openMarker.current}
                </span>
                <LagePill pos={openMarker.lagePosition} />
              </div>
              <div style={{ marginBottom: "16px" }}>
                <ReferenceBar marker={openMarker} />
              </div>
              <div
                style={{ display: "flex", flexDirection: "column", gap: "7px" }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    fontSize: "12.5px",
                  }}
                >
                  <span style={{ color: "var(--text-muted)" }}>Referenz</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-body)",
                    }}
                  >
                    {openMarker.reference}
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
                    Veränderung
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-body)",
                    }}
                  >
                    {openMarker.change}
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
                    Quelle / Code
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-body)",
                    }}
                  >
                    {openMarker.code}
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
                    Review-Status
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-body)",
                    }}
                  >
                    {openMarker.status}
                  </span>
                </div>
              </div>
              {openMarker.comparabilityFull && (
                <p
                  style={{
                    margin: "14px 0 0",
                    fontSize: "12px",
                    lineHeight: 1.5,
                    color: "var(--text-muted)",
                  }}
                >
                  {openMarker.comparabilityFull}
                </p>
              )}
              <p
                style={{
                  margin: "14px 0 0",
                  fontSize: "11.5px",
                  lineHeight: 1.5,
                  color: "var(--text-faint)",
                }}
              >
                Lage relativ zum Quellreferenzintervall — keine Diagnose, keine
                Bewertung. {lageLabel(openMarker.lagePosition).sentence}.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
