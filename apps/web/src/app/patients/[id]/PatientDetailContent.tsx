"use client";

import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  useTransition,
  type CSSProperties,
  type KeyboardEvent,
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
import { AuditSteps } from "@/components/vitabahn/AuditSteps";
import { Dialog } from "@/components/vitabahn/Dialog";
import { EmptyState } from "@/components/vitabahn/EmptyState";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import { lageLabel } from "@/lib/lageCopy";
import type { MarkerSeries } from "@/lib/presenters/domainOverview";
import type { DetailView } from "@/lib/presenters/patientDetail";
import { sourceNoteText, type MarkerView } from "@/lib/presenters/review";

import { ConsentCard } from "./ConsentCard";
import { DataExportCard } from "./DataExportCard";
import {
  DomainOverviewPanel,
  SeriesValues,
  UNASSIGNED_ID,
} from "./DomainOverviewPanel";
import { HistoryChart } from "./HistoryChart";
import { LabDocumentsCard } from "./LabDocumentsCard";
import { GERMAN, LagePill, ReferenceBar } from "./MarkerParts";
import { VisitPrepCard } from "./VisitPrepCard";

// VitaBahn patient Detail (ADR-0006, real-data path). Consumes the governed DetailView
// (presentReview + a real data-completeness stat). NO A–E grade (doctrine). Observation Status
// is the verdict-free positional Lage (Über/Unter Referenz · Im Intervall · Keine Referenz),
// NOT a Normal/Grenzwertig/Auffällig verdict — that has no real source and crosses the MDR
// boundary. The marker modal uses the lab-only reference bar, not a heuristic severity gauge.
//
// The page follows the interface language (lib/i18n). The VALUES of closed vocabularies on it
// do not, and are marked lang="de" wherever they show: the names of the domain axes, the
// value of follow-up adequacy, the position against the reference interval, the
// comparability notes (ADR-0007: their English needs the medical director). What NAMES a kind
// of fact (a column heading, "Follow-up adequacy:") is interface. Numbers and dates keep
// their form.

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
      fg: "var(--status-warning-text)",
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

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0] ?? "");
  return letters.join("").toUpperCase() || "–";
}

// The three tabs of the page, in their order.
type PatientTab = "vorbereitung" | "werte" | "akte";
const PATIENT_TABS: readonly PatientTab[] = ["vorbereitung", "werte", "akte"];
const panelId = (tab: PatientTab) => `vb-pt-panel-${tab}`;
const tabId = (tab: PatientTab) => `vb-pt-tab-${tab}`;

// Which tab a fragment of the address opens, and the element in it to scroll to: a tab by
// its name, a domain list or the unassigned list in the values tab.
export function tabOfFragment(
  hash: string,
): { tab: PatientTab; id: string | null } | null {
  const id = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!id) return null;
  if ((PATIENT_TABS as readonly string[]).includes(id))
    return { tab: id as PatientTab, id: null };
  if (id.startsWith("vb-domain-") || id === UNASSIGNED_ID)
    return { tab: "werte", id };
  return null;
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

  const t = useI18n().t.patientPage;
  const valueStatus: Record<string, string> = t.valueStatus;
  // The marker dialog: the value it opens on (the latest standing one), and the marker's
  // every value beneath it.
  const [openMarker, setOpenMarker] = useState<{
    marker: MarkerView;
    series: MarkerSeries | null;
  } | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // The page in three tabs (docs/notes/0025): the preparation first, then the values, then
  // the record's administration. Every panel is in the page (hidden, not left out), so a
  // link into a domain list — from the preparation card, the practice view, the printable
  // page — still lands: the address's fragment names the list, and the fragment opens the
  // tab that holds it.
  const [tab, setTab] = useState<PatientTab>("vorbereitung");
  // Until the page is hydrated every part is shown, one under the other: a page without
  // scripts reads in full, and the parts that then fold away lie below the first one.
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const hiddenUnless = (key: PatientTab) => hydrated && tab !== key;
  const tabRefs = useRef<Record<PatientTab, HTMLButtonElement | null>>({
    vorbereitung: null,
    werte: null,
    akte: null,
  });
  const [wanted, setWanted] = useState<string | null>(null);
  useEffect(() => {
    const follow = () => {
      const target = tabOfFragment(window.location.hash);
      if (!target) return;
      setTab(target.tab);
      setWanted(target.id);
    };
    follow();
    window.addEventListener("hashchange", follow);
    return () => window.removeEventListener("hashchange", follow);
  }, []);
  useEffect(() => {
    if (!wanted) return;
    document.getElementById(wanted)?.scrollIntoView({ block: "start" });
    setWanted(null);
  }, [wanted, tab]);
  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = PATIENT_TABS.indexOf(tab);
    const next =
      e.key === "ArrowRight"
        ? PATIENT_TABS[(i + 1) % PATIENT_TABS.length]
        : e.key === "ArrowLeft"
          ? PATIENT_TABS[(i + PATIENT_TABS.length - 1) % PATIENT_TABS.length]
          : e.key === "Home"
            ? PATIENT_TABS[0]
            : e.key === "End"
              ? PATIENT_TABS[PATIENT_TABS.length - 1]
              : null;
    if (!next) return;
    e.preventDefault();
    setTab(next);
    tabRefs.current[next]?.focus();
  };

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
      // On success the action redirects to the report; it answers only a refusal.
      const res = await generateReportAction(view.patientId);
      if (res && !res.ok) setDraftError(res.error);
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
  const openSeries = (series: MarkerSeries) => {
    const shown = series.latest ?? series.values[series.values.length - 1];
    const marker = review.markers.find((m) => m.id === shown?.id);
    if (marker) setOpenMarker({ marker, series });
  };
  const closeObs = () => setOpenMarker(null);

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
        className="vb-ov-card"
        style={{ padding: "22px 24px 4px", marginBottom: "20px" }}
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
          {/* On a narrow screen the actions go under the name, which wraps if it must. */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
              flex: "1 1 300px",
              flexWrap: "wrap",
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
            <div style={{ flex: "1 1 180px", minWidth: 0 }}>
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
                    overflowWrap: "anywhere",
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
                  {review.dateOfBirth
                    ? `${fill(t.born, { date: review.dateOfBirth })} · `
                    : ""}
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
              {/* Where the record stands in time: its newest sample, its latest run. */}
              {!erased && (
                <div className="vb-pt-stand">
                  <span>
                    {view.prep.today.latestDay
                      ? fill(t.lastValues, { date: view.prep.today.latestDay })
                      : t.noValuesYet}
                  </span>
                  <span>
                    {view.prep.run
                      ? fill(t.lastRun, {
                          n: view.prep.run.number,
                          date: view.prep.run.day,
                        })
                      : t.noRunYet}
                  </span>
                </div>
              )}
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
                      color: "var(--status-danger-text)",
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

      <div
        role="tablist"
        aria-label={t.tabs.label}
        className="vb-ov-tabs vb-pt-tabs"
      >
        {PATIENT_TABS.map((key) => (
          <button
            key={key}
            ref={(el) => {
              tabRefs.current[key] = el;
            }}
            type="button"
            role="tab"
            id={tabId(key)}
            className="vb-ov-tab"
            aria-selected={tab === key}
            aria-controls={panelId(key)}
            tabIndex={tab === key ? 0 : -1}
            onClick={() => setTab(key)}
            onKeyDown={onTabKey}
          >
            {t.tabs[key]}
            {key === "werte" && (
              <>
                {" "}
                <span className="vb-ov-tab-n">{completeness.published}</span>
              </>
            )}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={panelId("vorbereitung")}
        aria-labelledby={tabId("vorbereitung")}
        hidden={hiddenUnless("vorbereitung")}
      >
        {/* The facts since the latest interpretation run, one line each, before everything
          else (docs/notes/0022). A tombstoned record has nothing to prepare. */}
        {!erased && (
          <VisitPrepCard
            prep={view.prep}
            overview={view.overview}
            patientId={view.patientId}
            onOpen={openSeries}
          />
        )}

        {/* data completeness (real, deterministic — the compliant replacement for the comp's quality gauge) */}
        <div
          className="vb-ov-card"
          style={{ padding: "16px 22px", marginBottom: "20px" }}
        >
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
                      fontSize: "11px",
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
      </div>

      <div
        role="tabpanel"
        id={panelId("werte")}
        aria-labelledby={tabId("werte")}
        hidden={hiddenUnless("werte")}
      >
        {/* Before the visit, the six domains, and each domain's markers (values placed by the
            catalog). A tombstoned record has no values left to place. */}
        {!erased && (
          <DomainOverviewPanel overview={view.overview} onOpen={openSeries} />
        )}
      </div>

      <div
        role="tabpanel"
        id={panelId("akte")}
        aria-labelledby={tabId("akte")}
        hidden={hiddenUnless("akte")}
      >
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

        {/* Audit stepper (real, from report status) */}
        <div
          className="vb-ov-card"
          style={{ padding: "20px 22px 22px", marginBottom: "16px" }}
        >
          <h3 className="vb-ov-h2">{t.audit.title}</h3>
          <p className="vb-ov-note" style={{ margin: "3px 0 18px" }}>
            {t.audit.note}
          </p>
          {review.status === "none" ? (
            <EmptyState quiet style={{ padding: 0 }}>
              {t.audit.none}
            </EmptyState>
          ) : (
            <AuditSteps steps={review.auditSteps} copy={t.audit.steps} />
          )}
        </div>
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
            width: openMarker.series ? "760px" : "560px",
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
                  fontSize: "11px",
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "var(--text-faint)",
                  marginBottom: "6px",
                }}
              >
                {t.marker.kicker}{" "}
                {openMarker.marker.primaryDomainLabel ? (
                  <span lang={GERMAN}>
                    {openMarker.marker.primaryDomainLabel}
                  </span>
                ) : (
                  openMarker.marker.code
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
                {openMarker.marker.name}
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
                {openMarker.marker.current}
              </span>
              {!openMarker.marker.reviewRequired && (
                <LagePill pos={openMarker.marker.lagePosition} />
              )}
            </div>
            <div style={{ marginBottom: "16px" }}>
              <ReferenceBar
                bar={openMarker.marker.lageBar}
                range={openMarker.marker.referenceRange}
              />
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
                  {openMarker.marker.reference}
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
                  {openMarker.marker.change}
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
                  {openMarker.marker.code}
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
                  {openMarker.marker.reviewRequired
                    ? (valueStatus[openMarker.marker.status] ??
                      openMarker.marker.status)
                    : t.valueStatus.published}
                </span>
              </div>
            </div>
            {openMarker.marker.sourceNote && (
              <p
                style={{
                  margin: "14px 0 0",
                  fontSize: "12px",
                  lineHeight: 1.5,
                  color: "var(--text-muted)",
                }}
              >
                {
                  sourceNoteText(openMarker.marker.sourceNote, t.sourceNote)
                    .full
                }
              </p>
            )}
            {openMarker.marker.comparabilityFull && (
              <p
                lang={GERMAN}
                style={{
                  margin: "14px 0 0",
                  fontSize: "12px",
                  lineHeight: 1.5,
                  color: "var(--text-muted)",
                }}
              >
                {openMarker.marker.comparabilityFull}
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
              {openMarker.marker.reviewRequired ? (
                t.marker.noPosition
              ) : (
                <>
                  {t.marker.positionNote}{" "}
                  <span lang={GERMAN}>
                    {lageLabel(openMarker.marker.lagePosition).sentence}
                  </span>
                  .
                </>
              )}
            </p>
            {openMarker.series && view.overview.timeAxis && (
              <HistoryChart
                series={openMarker.series}
                axis={view.overview.timeAxis}
              />
            )}
            {openMarker.series && openMarker.series.values.length > 0 && (
              <SeriesValues series={openMarker.series} t={t} />
            )}
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
                className="vb-control is-wide"
                style={{ marginBottom: "16px" }}
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
                    color: "var(--status-danger-text)",
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
                    color: "var(--status-danger-text)",
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
