"use client";

import {
  useMemo,
  useRef,
  useState,
  useTransition,
  type CSSProperties,
} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  createInvitationAction,
  requestPatientDeletion,
} from "@/app/patients/actions";
import { generateReportAction } from "@/app/reports/actions";
import type {
  ConsentState,
  DataExport,
  DeletionReason,
  SourceDocument,
} from "@/lib/api";
import { Dialog } from "@/components/vitabahn/Dialog";
import { clickable } from "@/components/vitabahn/interactive";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import { lageLabel } from "@/lib/lageCopy";
import type { ReferencePosition } from "@/lib/referencePosition";
import type { DetailView } from "@/lib/presenters/patientDetail";
import { DOMAIN_AXIS_LABELS, type MarkerView } from "@/lib/presenters/review";

import { ConsentCard } from "./ConsentCard";
import { DataExportCard } from "./DataExportCard";
import { LabDocumentsCard } from "./LabDocumentsCard";

// VitaBahn patient Detail (ADR-0006, real-data path). Consumes the governed DetailView
// (presentReview + a real data-completeness stat). NO A–E grade (doctrine). Observation Status
// is the verdict-free positional Lage (Über/Unter Referenz · Im Intervall · Keine Referenz),
// NOT a Normal/Grenzwertig/Auffällig verdict — that has no real source and crosses the MDR
// boundary. The marker modal uses the lab-only reference bar, not a heuristic severity gauge.
//
// The page follows the interface language (lib/i18n). Four things on it do not, and are
// marked lang="de" wherever they show: the names of the domain axes, follow-up adequacy, the
// position against the reference interval, and the comparability notes — closed vocabularies
// whose English terms need the medical director (ADR-0007). So is a message of the report
// draft action, which belongs to the report pages. Numbers and dates keep their form.
const GERMAN = "de";

// How a shown value relates to what the source wrote, in the page's language.
function sourceNoteText(
  note: NonNullable<MarkerView["sourceNote"]>,
  t: Messages["patientPage"]["sourceNote"],
): { short: string; full: string } {
  if (note.kind !== "converted") return t[note.kind];
  const values = {
    source: note.source ?? "",
    unit: note.unit ?? t.converted.unitOfMetric,
  };
  return {
    short: fill(t.converted.short, values),
    full: fill(t.converted.full, values),
  };
}

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
const secBtn: CSSProperties = {
  height: "38px",
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
};
const EGRID =
  "minmax(150px,1.6fr) 110px minmax(96px,0.9fr) 96px minmax(150px,1.2fr) 132px";

function statusVita(
  status: string,
  t: Messages["patientPage"]["reportStatus"],
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
      text: t.released,
    };
  if (status === "approved")
    return {
      fg: "var(--sky-400)",
      bg: "rgba(63,164,201,0.12)",
      bd: "rgba(63,164,201,0.30)",
      text: t.approved,
    };
  if (status === "draft_generated" || status === "draft_edited")
    return {
      fg: "var(--amber-500)",
      bg: "rgba(201,136,28,0.12)",
      bd: "rgba(201,136,28,0.30)",
      text: t.draft,
    };
  if (status === "rejected")
    return {
      fg: "var(--rose-500)",
      bg: "rgba(194,74,74,0.12)",
      bd: "rgba(194,74,74,0.30)",
      text: t.rejected,
    };
  return {
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
    text: t.none,
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
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0] ?? "");
  return letters.join("").toUpperCase() || "–";
}

function ReferenceBar({ marker }: { marker: MarkerView }) {
  const t = useI18n().t.patientPage.evidence;
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
      {marker.referenceRange && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            color: "var(--text-faint)",
            marginTop: "3px",
          }}
        >
          {fill(t.reference, { range: marker.referenceRange })}
        </div>
      )}
    </div>
  );
}

function LagePill({ pos }: { pos: ReferencePosition }) {
  const l = lageLabel(pos);
  const c = lageVita(pos);
  return (
    // The German name, until the English one is confirmed (see the top of this file).
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

export function PatientDetailContent({
  view,
  documents,
  consents,
  dataExports,
  sessionRole,
}: {
  view: DetailView;
  documents: SourceDocument[];
  consents: ConsentState[];
  // null: not the owner, an erased record, or the list could not be read — no card.
  dataExports: DataExport[] | null;
  sessionRole: string | null;
}) {
  const router = useRouter();
  const { review, completeness } = view;

  // The six domain axes are the fixed canonical structure (ADR-0003) — the page ALWAYS shows
  // all six. Axes that an interpretation run has scored render with their adequacy + evidence;
  // axes without a run-verdict render as honest "noch nicht bewertet" placeholders (never an
  // invented verdict). Order is the founder-approved ADR-0003 order.
  const DOMAIN_ORDER = [
    "metabolic",
    "immune_inflammation",
    "cardiovascular",
    "neurocognitive",
    "musculoskeletal",
    "regenerative_capacity",
  ];
  type DomainCard = (typeof review.domains)[number] & { assessed: boolean };
  const domains: DomainCard[] = DOMAIN_ORDER.map((axis) => {
    const real = review.domains.find((d) => d.domainAxis === axis);
    if (real) return { ...real, assessed: true };
    return {
      axisLabel: DOMAIN_AXIS_LABELS[axis] ?? axis,
      domainAxis: axis,
      cisLabel: "",
      actionabilityLabel: "",
      adequacyLabel: "",
      reviewed: false,
      citesReplaced: false,
      markerCodes: [],
      cells: [],
      assessed: false,
    };
  });

  const t = useI18n().t.patientPage;
  const valueStatus: Record<string, string> = t.valueStatus;
  const firstWithMarkers =
    domains.find((d) => d.markerCodes.length > 0)?.domainAxis ??
    domains[0]?.domainAxis ??
    "";
  const [domainAxis, setDomainAxis] = useState(firstWithMarkers);
  const [openMarker, setOpenMarker] = useState<MarkerView | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // A tombstoned (erased) record shows a banner and hides all staff actions — its artifacts
  // are gone and it must never accept a new invitation, interpretation, or deletion request.
  const erased = view.erased;
  // Inviting is operational provisioning (care staff); the MD is the gate, not an operator.
  const canInvite =
    !erased &&
    (sessionRole === "owner" ||
      sessionRole === "clinician" ||
      sessionRole === "assistant");
  // Requesting erasure is tenant administration (owner). It only FILES a request; a medical
  // director decides it, and execution is separate — nothing is deleted here.
  const canRequestDeletion = !erased && sessionRole === "owner";
  // Drafting is operational (care staff) and only offered while the patient has no report:
  // each call creates a NEW report, so an existing one is opened, never silently duplicated.
  // Approve/release stay on the review surface the draft leads to.
  const canDraft = canInvite && review.status === "none";
  const reportLink = erased ? null : view.reportLink;

  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftPending, startDraftTransition] = useTransition();
  const runDraft = () => {
    startDraftTransition(async () => {
      setDraftError(null);
      const res = await generateReportAction(view.patientId);
      if (res.ok) router.push(res.reviewUrl);
      else setDraftError(res.error);
    });
  };

  const [deletionState, setDeletionState] = useState<
    { phase: "confirm" } | { phase: "done" } | null
  >(null);
  const [deletionReason, setDeletionReason] =
    useState<DeletionReason>("patient_request");
  const [deletionError, setDeletionError] = useState<string | null>(null);
  const [deletionPending, startDeletionTransition] = useTransition();
  const closeDeletion = () => {
    setDeletionState(null);
    setDeletionError(null);
  };
  const runDeletion = () => {
    startDeletionTransition(async () => {
      setDeletionError(null);
      const res = await requestPatientDeletion(view.patientId, deletionReason);
      if (res.ok) setDeletionState({ phase: "done" });
      else setDeletionError(res.error);
    });
  };

  // Invitation dialog (P3): the one-time URL renders exactly once, for manual sharing.
  const [inviteState, setInviteState] = useState<
    | { phase: "confirm" }
    | { phase: "done"; url: string; expiresAt: string }
    | null
  >(null);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteCopied, setInviteCopied] = useState(false);
  const [invitePending, startInviteTransition] = useTransition();
  const closeInvite = () => {
    setInviteState(null);
    setInviteError(null);
    setInviteCopied(false);
  };
  const runInvite = () => {
    startInviteTransition(async () => {
      const res = await createInvitationAction(view.patientId);
      if (!res.ok) {
        setInviteError(res.error);
        return;
      }
      setInviteError(null);
      setInviteState({ phase: "done", url: res.url, expiresAt: res.expiresAt });
    });
  };

  // The shared Dialog handles Escape, the focus trap, and focus capture/restore to the trigger.
  const openObs = (m: MarkerView) => setOpenMarker(m);
  const closeObs = () => setOpenMarker(null);

  const curDomain = domains.find((d) => d.domainAxis === domainAxis) ?? null;
  const evidence = useMemo(() => {
    if (!curDomain) return [];
    // Mirror the authoritative review surface: primary membership by the domain's marker
    // codes, secondary membership by the KPI's secondary-domain links — never a fuzzy
    // label match (which could pull markers not actually in this domain's evidence).
    const codes = new Set(curDomain.markerCodes);
    return review.markers.filter(
      (m) =>
        (m.identity != null && codes.has(m.identity)) ||
        m.secondaryDomains.includes(curDomain.domainAxis),
    );
  }, [curDomain, review.markers]);

  const sb = statusVita(review.status, t.reportStatus);
  const idBadge = sb;

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
        {t.back}
      </button>

      {erased && (
        <div
          role="status"
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "flex-start",
            padding: "14px 16px",
            marginBottom: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-default)",
            background: "var(--surface-sunken)",
          }}
        >
          <svg
            aria-hidden="true"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ flexShrink: 0, marginTop: "1px" }}
          >
            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          </svg>
          <div>
            <div
              style={{
                fontSize: "13.5px",
                fontWeight: 700,
                color: "var(--text-strong)",
                marginBottom: "3px",
              }}
            >
              {t.erased.title}
            </div>
            <p
              style={{
                margin: 0,
                fontSize: "12.5px",
                lineHeight: 1.55,
                color: "var(--text-muted)",
              }}
            >
              {t.erased.note}
            </p>
          </div>
        </div>
      )}

      {/* identity */}
      <div
        style={{ ...cardStyle, padding: "22px 24px 4px", marginBottom: "20px" }}
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
                <span>
                  {review.ageYears === null
                    ? t.ageUnknown
                    : byCount(t.age, review.ageYears)}
                </span>
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
                    ? t.noReport
                    : fill(t.reportVersion, { version: review.versionNo })}
                </span>
              </div>
            </div>
            {(canInvite || reportLink) && (
              <div
                style={{
                  marginLeft: "auto",
                  alignSelf: "center",
                  display: "flex",
                  gap: "10px",
                  flexWrap: "wrap",
                }}
              >
                {reportLink && (
                  <Link
                    href={reportLink}
                    className="vb-btn-sec"
                    style={{
                      ...secBtn,
                      display: "inline-flex",
                      alignItems: "center",
                      textDecoration: "none",
                    }}
                  >
                    {t.actions.openReport}
                  </Link>
                )}
                {canDraft && (
                  <button
                    type="button"
                    disabled={draftPending}
                    onClick={runDraft}
                    className="vb-btn-sec"
                    style={secBtn}
                  >
                    {draftPending
                      ? t.actions.creatingDraft
                      : t.actions.createDraft}
                  </button>
                )}
                {canInvite && sessionRole === "clinician" && (
                  <button
                    type="button"
                    onClick={() =>
                      router.push(
                        `/patients/${view.patientId}/interpretation/neu`,
                      )
                    }
                    className="vb-btn-sec"
                    style={{
                      height: "38px",
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
                    {t.actions.recordInterpretation}
                  </button>
                )}
                {canInvite && (
                  <button
                    type="button"
                    disabled={invitePending}
                    onClick={() => {
                      setInviteError(null);
                      setInviteCopied(false);
                      setInviteState({ phase: "confirm" });
                    }}
                    className="vb-btn-sec"
                    style={secBtn}
                  >
                    {t.actions.invite}
                  </button>
                )}
                {canRequestDeletion && (
                  <button
                    type="button"
                    disabled={deletionPending}
                    onClick={() => {
                      setDeletionError(null);
                      setDeletionReason("patient_request");
                      setDeletionState({ phase: "confirm" });
                    }}
                    style={{
                      height: "38px",
                      padding: "0 15px",
                      whiteSpace: "nowrap",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid rgba(165,72,64,0.45)",
                      background: "transparent",
                      color: "var(--rose-500)",
                      fontFamily: "var(--font-text)",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    {t.actions.requestDeletion}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
        {draftError && (
          <p
            role="alert"
            lang={GERMAN}
            style={{
              margin: "0 0 14px",
              fontSize: "12.5px",
              color: "var(--danger, #b3261e)",
            }}
          >
            {draftError}
          </p>
        )}
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
              {t.coverage.title}
            </h3>
            <p
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                margin: 0,
              }}
            >
              {t.coverage.note}
            </p>
          </div>
          <div style={{ display: "flex", gap: "26px", flexWrap: "wrap" }}>
            {[
              { v: String(completeness.total), l: t.coverage.observations },
              {
                v: `${completeness.published}/${completeness.total}`,
                l: t.coverage.published,
              },
              {
                v: `${completeness.withReference}/${completeness.total}`,
                l: t.coverage.withReference,
              },
              {
                v:
                  completeness.latestAgeDays == null
                    ? "—"
                    : completeness.latestAgeDays === 0
                      ? t.coverage.today
                      : fill(t.coverage.days, {
                          n: completeness.latestAgeDays,
                        }),
                l: t.coverage.latest,
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

      {/* Consent state per purpose (all staff) + documenting a consent or a withdrawal (care
          staff). A tombstoned record takes no new entries. */}
      {!erased && (
        <ConsentCard
          patientId={view.patientId}
          consents={consents}
          canRecord={canInvite}
        />
      )}

      {/* Laboratory files: upload + import (care staff), list of stored files (all staff).
          A tombstoned record takes no new data. */}
      {!erased && (
        <LabDocumentsCard
          patientId={view.patientId}
          documents={documents}
          canImport={canInvite}
        />
      )}

      {/* Data export (GDPR Art. 15/20): tenant administration, owner only. */}
      {canRequestDeletion && dataExports !== null && (
        <DataExportCard patientId={view.patientId} exports={dataExports} />
      )}

      {/* domain cards — the six canonical axes always (no A–E grade — doctrine) */}
      {review.runNumber == null && (
        <p
          style={{
            fontSize: "12.5px",
            color: "var(--text-muted)",
            margin: "0 0 12px",
            lineHeight: 1.5,
          }}
        >
          {t.domains.noRun}
        </p>
      )}
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
                fill(t.domains.select, { axis: d.axisLabel }),
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
                  <span lang={GERMAN}>{d.axisLabel}</span>
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
                  {d.assessed
                    ? d.reviewed
                      ? t.domains.reviewed
                      : t.domains.draft
                    : t.domains.none}
                </span>
              </div>
              {d.assessed ? (
                <>
                  {/* A closed vocabulary: its name and its value stay German. */}
                  <div
                    lang={GERMAN}
                    style={{ fontSize: "12px", color: "var(--text-muted)" }}
                  >
                    Follow-up-Adäquanz: {d.adequacyLabel}
                  </div>
                  {d.citesReplaced && (
                    <div
                      style={{
                        marginTop: "6px",
                        fontSize: "12px",
                        color: "var(--danger)",
                      }}
                    >
                      {t.domains.citesReplaced}
                    </div>
                  )}
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
                      {t.domains.shown}
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
                      {fill(t.domains.show, { n: d.markerCodes.length })}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontSize: "12px", color: "var(--text-faint)" }}>
                  {t.domains.notInterpreted}
                </div>
              )}
            </div>
          );
        })}
      </div>

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
            {t.evidence.title}
            {curDomain && (
              <>
                {" · "}
                <span lang={GERMAN}>{curDomain.axisLabel}</span>
              </>
            )}
          </h3>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted)",
              margin: 0,
              maxWidth: "94ch",
            }}
          >
            {t.evidence.note}
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
              <span style={colLabel}>{t.evidence.columns.marker}</span>
              <span style={colLabel}>{t.evidence.columns.category}</span>
              <span style={colLabel}>{t.evidence.columns.value}</span>
              <span style={colLabel}>{t.evidence.columns.change}</span>
              <span style={colLabel}>{t.evidence.columns.position}</span>
              <span style={colLabel}>{t.evidence.columns.bar}</span>
            </div>
            {evidence.map((m, i) => (
              <div
                key={m.code + m.name + i}
                className="vb-erow"
                {...clickable(
                  () => openObs(m),
                  fill(t.evidence.open, { name: m.name }),
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
                  {m.name}
                  {m.reviewRequired && (
                    <span
                      style={{
                        display: "block",
                        fontSize: "11px",
                        fontWeight: 600,
                        color: "var(--text-body)",
                      }}
                    >
                      {valueStatus[m.status] ?? m.status}
                    </span>
                  )}
                  {m.superseded && (
                    <span
                      style={{
                        display: "block",
                        fontSize: "11px",
                        fontWeight: 500,
                        color: "var(--text-muted)",
                      }}
                    >
                      {t.evidence.superseded}
                    </span>
                  )}
                  {m.inputReplaced && (
                    <span
                      style={{
                        display: "block",
                        fontSize: "11px",
                        fontWeight: 500,
                        color: "var(--text-muted)",
                      }}
                    >
                      {t.evidence.inputReplaced}
                    </span>
                  )}
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
                    {m.primaryDomainLabel ? (
                      <span lang={GERMAN}>{m.primaryDomainLabel}</span>
                    ) : (
                      "—"
                    )}
                  </span>
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "var(--text-strong)",
                    // A result that is no number shows the source's wording, which can be long.
                    overflowWrap: "anywhere",
                  }}
                >
                  {m.current}
                  {m.sourceNote && (
                    <span
                      title={sourceNoteText(m.sourceNote, t.sourceNote).full}
                      style={{
                        display: "block",
                        fontFamily: "var(--font-text)",
                        fontSize: "11px",
                        fontWeight: 500,
                        color: "var(--text-muted)",
                      }}
                    >
                      {sourceNoteText(m.sourceNote, t.sourceNote).short}
                    </span>
                  )}
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
                  {/* No position is stated for a value nobody has reviewed. */}
                  {m.reviewRequired ? "—" : <LagePill pos={m.lagePosition} />}
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
                {t.evidence.empty}
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
          {t.audit.title}
        </h3>
        <p
          style={{
            fontSize: "12.5px",
            color: "var(--text-muted)",
            margin: "0 0 18px",
          }}
        >
          {t.audit.note}
        </p>
        {review.status === "none" ? (
          <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            {t.audit.none}
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              minWidth: "560px",
            }}
          >
            {review.auditSteps.map((s, i, a) => {
              // The step's wording in the page's language, by the step and its line.
              const step: Record<string, string> = t.audit.steps[s.key];
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
                  key={s.key}
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
                          i === a.length - 1
                            ? "transparent"
                            : "var(--teal-300)",
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
                      {step.label}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10.5px",
                        color: "var(--text-muted)",
                        marginTop: "2px",
                      }}
                    >
                      {step[s.subKey] ?? ""}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Invite dialog (P3, docs/notes/0010) — one-time URL, manual secure sharing only */}
      {inviteState && (
        <Dialog
          onClose={closeInvite}
          labelledBy="vb-invite-title"
          lockScroll
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "520px",
            maxWidth: "100%",
            background: "var(--surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-xl)",
            padding: "22px",
          }}
        >
          <h3
            id="vb-invite-title"
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: "var(--text-xl)",
              color: "var(--text-strong)",
              margin: 0,
            }}
          >
            {inviteState.phase === "done" ? t.invite.doneTitle : t.invite.title}
          </h3>
          <p
            style={{
              margin: "10px 0 0",
              fontSize: "12.5px",
              lineHeight: 1.5,
              color: "var(--text-muted)",
            }}
          >
            {inviteState.phase === "done" ? t.invite.doneNote : t.invite.note}
          </p>
          {inviteError && (
            <p
              role="alert"
              style={{
                margin: "12px 0 0",
                fontSize: "12.5px",
                color: "var(--danger, #b3261e)",
              }}
            >
              {inviteError}
            </p>
          )}
          {inviteState.phase === "done" && (
            <label
              style={{
                display: "block",
                marginTop: "16px",
                fontSize: "12px",
                color: "var(--text-muted)",
              }}
            >
              {t.invite.link}
              <input
                readOnly
                value={inviteState.url}
                onFocus={(e) => e.currentTarget.select()}
                style={{
                  display: "block",
                  width: "100%",
                  marginTop: "6px",
                  padding: "9px 11px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--surface-sunken)",
                  color: "var(--text-body)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                }}
              />
            </label>
          )}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "10px",
              marginTop: "20px",
            }}
          >
            {inviteState.phase === "done" ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard
                      .writeText(inviteState.url)
                      .then(() => setInviteCopied(true));
                  }}
                  className="vb-btn-sec"
                  style={{
                    height: "38px",
                    padding: "0 15px",
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
                  {inviteCopied ? t.invite.copied : t.invite.copy}
                </button>
                <button
                  type="button"
                  onClick={closeInvite}
                  className="vb-btn-pri"
                  style={{
                    height: "38px",
                    padding: "0 16px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--brand)",
                    background: "var(--brand)",
                    color: "var(--text-on-brand)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {t.close}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  disabled={invitePending}
                  onClick={closeInvite}
                  className="vb-btn-sec"
                  style={{
                    height: "38px",
                    padding: "0 15px",
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
                  {t.cancel}
                </button>
                <button
                  type="button"
                  disabled={invitePending}
                  onClick={runInvite}
                  className="vb-btn-pri"
                  style={{
                    height: "38px",
                    padding: "0 16px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--brand)",
                    background: "var(--brand)",
                    color: "var(--text-on-brand)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {t.invite.create}
                </button>
              </>
            )}
          </div>
        </Dialog>
      )}

      {/* Marker modal — compliant (lab reference bar + positional Lage; no severity gauge) */}
      {openMarker && (
        <Dialog
          onClose={closeObs}
          labelledBy="vb-marker-title"
          initialFocusRef={closeBtnRef}
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(12,18,20,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
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
                {t.marker.kicker}{" "}
                {openMarker.primaryDomainLabel ? (
                  <span lang={GERMAN}>{openMarker.primaryDomainLabel}</span>
                ) : (
                  openMarker.code
                )}
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
              aria-label={t.close}
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
              {!openMarker.reviewRequired && (
                <LagePill pos={openMarker.lagePosition} />
              )}
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
                <span style={{ color: "var(--text-muted)" }}>
                  {t.marker.reference}
                </span>
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
                  {t.marker.change}
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
                  {t.marker.source}
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
                  {t.marker.status}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-body)",
                  }}
                >
                  {openMarker.reviewRequired
                    ? (valueStatus[openMarker.status] ?? openMarker.status)
                    : t.valueStatus.published}
                </span>
              </div>
            </div>
            {openMarker.sourceNote && (
              <p
                style={{
                  margin: "14px 0 0",
                  fontSize: "12px",
                  lineHeight: 1.5,
                  color: "var(--text-muted)",
                }}
              >
                {sourceNoteText(openMarker.sourceNote, t.sourceNote).full}
              </p>
            )}
            {openMarker.comparabilityFull && (
              <p
                lang={GERMAN}
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
              {openMarker.reviewRequired ? (
                t.marker.noPosition
              ) : (
                <>
                  {t.marker.positionNote}{" "}
                  <span lang={GERMAN}>
                    {lageLabel(openMarker.lagePosition).sentence}
                  </span>
                  .
                </>
              )}
            </p>
          </div>
        </Dialog>
      )}

      {deletionState && (
        <Dialog
          onClose={closeDeletion}
          labelledBy="del-title"
          describedBy="del-desc"
          backdropStyle={{
            position: "fixed",
            inset: 0,
            zIndex: 60,
            background: "rgba(15,23,28,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
          dialogStyle={{
            width: "100%",
            maxWidth: "440px",
            background: "var(--surface-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-lg)",
            padding: "24px",
          }}
        >
          {deletionState.phase === "done" ? (
            <div>
              <h2
                id="del-title"
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                  margin: "0 0 6px",
                }}
              >
                {t.deletion.doneTitle}
              </h2>
              <p
                id="del-desc"
                style={{
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  lineHeight: 1.55,
                  margin: "0 0 18px",
                }}
              >
                {t.deletion.doneNote}
              </p>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={closeDeletion}
                  style={{
                    height: "38px",
                    padding: "0 18px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--brand-border)",
                    background: "var(--brand)",
                    color: "var(--text-on-brand)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {t.close}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <h2
                id="del-title"
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 700,
                  fontSize: "var(--text-xl)",
                  color: "var(--text-strong)",
                  margin: "0 0 6px",
                }}
              >
                {t.deletion.title}
              </h2>
              <p
                id="del-desc"
                style={{
                  fontSize: "12.5px",
                  color: "var(--text-muted)",
                  lineHeight: 1.55,
                  margin: "0 0 16px",
                }}
              >
                {t.deletion.noteBefore}{" "}
                <strong style={{ color: "var(--text-strong)" }}>
                  {review.patientName}
                </strong>
                {t.deletion.noteAfter}
              </p>
              <label
                htmlFor="del-reason"
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--text-body)",
                  marginBottom: "5px",
                }}
              >
                {t.deletion.reason}
              </label>
              <select
                id="del-reason"
                value={deletionReason}
                onChange={(e) =>
                  setDeletionReason(e.target.value as DeletionReason)
                }
                style={{
                  width: "100%",
                  height: "38px",
                  padding: "0 10px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-default)",
                  background: "var(--surface-sunken)",
                  color: "var(--text-strong)",
                  fontFamily: "var(--font-text)",
                  fontSize: "13.5px",
                  marginBottom: "16px",
                }}
              >
                <option value="patient_request">
                  {t.deletion.reasons.patient_request}
                </option>
                <option value="withdrawn_consent">
                  {t.deletion.reasons.withdrawn_consent}
                </option>
                <option value="data_minimization">
                  {t.deletion.reasons.data_minimization}
                </option>
              </select>

              {deletionError && (
                <div
                  role="alert"
                  style={{
                    fontSize: "12.5px",
                    color: "var(--rose-500)",
                    background: "rgba(194,74,74,0.10)",
                    border: "1px solid rgba(194,74,74,0.30)",
                    borderRadius: "var(--radius-sm)",
                    padding: "9px 12px",
                    marginBottom: "14px",
                  }}
                >
                  {deletionError}
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={closeDeletion}
                  disabled={deletionPending}
                  style={{
                    height: "38px",
                    padding: "0 16px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                    background: "transparent",
                    color: "var(--text-body)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: deletionPending ? "default" : "pointer",
                  }}
                >
                  {t.cancel}
                </button>
                <button
                  type="button"
                  onClick={runDeletion}
                  disabled={deletionPending}
                  style={{
                    height: "38px",
                    padding: "0 18px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid rgba(165,72,64,0.5)",
                    background: "rgba(194,74,74,0.10)",
                    color: "var(--rose-500)",
                    fontFamily: "var(--font-text)",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: deletionPending ? "default" : "pointer",
                    opacity: deletionPending ? 0.7 : 1,
                  }}
                >
                  {deletionPending ? t.deletion.submitting : t.deletion.submit}
                </button>
              </div>
            </div>
          )}
        </Dialog>
      )}
    </>
  );
}
