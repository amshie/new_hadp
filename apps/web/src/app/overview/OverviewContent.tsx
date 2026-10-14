"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AddPatientDialog } from "@/components/vitabahn/AddPatientDialog";
import { EmptyState } from "@/components/vitabahn/EmptyState";
import { clickable } from "@/components/vitabahn/interactive";
import { actionLabel, targetLabel } from "@/lib/auditCopy";
import { roleName } from "@/lib/identity";
import { byCount, fill } from "@/lib/i18n/fill";
import { useI18n } from "@/lib/i18n/I18nProvider";
import type { Messages } from "@/lib/i18n/messages";
import type { StatusGroup, WorkRowView } from "@/lib/presenters/dashboard";
import {
  FOLLOW_UP_AFTER_DAYS,
  nextStep,
  presentActivity,
  presentDataMeters,
  presentSources,
  presentStatband,
  presentToday,
  type Tier,
  type TodayItem,
} from "@/lib/presenters/today";

import { ago, clock, day, longDay } from "@/lib/format";
import type { OverviewData } from "./page";
import { Card, CardHead, KeyValue, Pill } from "./parts";
import { PracticeCard } from "./PracticeCard";

// Übersicht (docs/notes/0015): one question, "what needs me today?", answered for the
// reader's role; then the work list with each record's next step, the clinic's weeks, its
// data and sources, and the latest activity. Workflow and counts only — no score, no
// urgency, no judgement of any value.

type TabKey = "open" | "approved" | "released" | "rejected" | "none" | "all";
const TABS: TabKey[] = [
  "open",
  "approved",
  "released",
  "rejected",
  "none",
  "all",
];
const TAB_GROUP: Record<Exclude<TabKey, "all">, StatusGroup> = {
  open: "review",
  approved: "approved",
  released: "released",
  rejected: "rejected",
  none: "none",
};

const inTab = (r: WorkRowView, tab: TabKey) =>
  tab === "all" || r.group === TAB_GROUP[tab];

export function OverviewContent({ data }: { data: OverviewData }) {
  const { locale, t } = useI18n();
  const o = t.overview;
  const today = useMemo(
    () =>
      presentToday({
        role: data.role,
        rows: data.rows,
        deletionRequests: data.deletionRequests,
        invitations: data.invitations,
        preparation: data.preparation,
        now: data.now,
      }),
    [data],
  );
  const band = useMemo(
    () => presentStatband(data.rows, data.throughput),
    [data.rows, data.throughput],
  );
  const [tab, setTab] = useState<TabKey>("all");

  const waiting = today.now.length;
  const leadRole =
    data.role && data.role in o.leadRole
      ? o.leadRole[data.role as keyof Messages["overview"]["leadRole"]]
      : "";

  const showReleased = () => {
    setTab("released");
    document
      .getElementById("arbeitsliste")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="vb-ov">
      <div className="vb-ov-pagehead">
        <div style={{ minWidth: 0 }}>
          <div className="vb-ov-eyebrow">
            {o.kicker} · {longDay(data.now, locale)}
          </div>
          <h1 className="vb-ov-h1">{o.title}</h1>
          <p className="vb-ov-lead">
            <b>{waiting === 0 ? o.lead.none : byCount(o.lead, waiting)}</b>{" "}
            {leadRole && `${leadRole} `}
            {o.synthetic}
          </p>
        </div>
        <AddPatientDialog />
      </div>

      <Statband band={band} />

      <TodayCard
        today={today}
        role={data.role}
        now={data.now}
        onReleased={showReleased}
      />

      <Worklist data={data} tab={tab} setTab={setTab} />

      <div className="vb-ov-grid2">
        <PracticeCard
          throughput={data.throughput}
          preparation={data.preparation}
        />
        <DataCard data={data} />
      </div>

      <ActivityCard data={data} />
    </div>
  );
}

// --- The band of counts -------------------------------------------------------------------

function Statband({ band }: { band: ReturnType<typeof presentStatband> }) {
  const s = useI18n().t.overview.statband;
  const max = Math.max(1, ...band.releasedByDay);
  const n = band.releasedByDay.length;
  const points = band.releasedByDay
    .map((v, i) => {
      const x = n <= 1 ? 45 : 2 + (86 * i) / (n - 1);
      return `${x.toFixed(1)},${(16 - (13 * v) / max).toFixed(1)}`;
    })
    .join(" ");
  return (
    <section className="vb-ov-statband" aria-label={s.label}>
      <Stat
        value={band.openReviews}
        label={s.openReviews.label}
        help={s.openReviews.help}
      />
      <Stat
        value={band.toRelease}
        label={s.toRelease.label}
        help={s.toRelease.help}
      />
      <Stat
        value={band.valuesInReview}
        label={s.valuesInReview.label}
        help={s.valuesInReview.help}
      />
      <Stat
        value={band.released ?? "—"}
        label={fill(s.released.label, { days: band.releasedDays ?? 30 })}
        help={band.released == null ? s.released.unavailable : s.released.help}
        spark={
          n > 0 ? (
            <svg width="90" height="18" aria-hidden="true" focusable="false">
              <polyline
                points={points}
                fill="none"
                stroke="var(--vital-500)"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
            </svg>
          ) : null
        }
      />
      <Stat
        value={band.patients}
        label={s.patients.label}
        help={fill(s.patients.help, {
          withReport: band.withReport,
          without: band.withoutReport,
        })}
      />
    </section>
  );
}

function Stat({
  value,
  label,
  help,
  spark,
}: {
  value: number | string;
  label: string;
  help: string;
  spark?: ReactNode;
}) {
  return (
    <div className="vb-ov-stat">
      <span className="vb-ov-stat-v">{value}</span>
      <span className="vb-ov-stat-l">{label}</span>
      <span className="vb-ov-stat-h">
        {spark}
        {spark ? <span className="sr-only">{help}</span> : help}
      </span>
    </div>
  );
}

// --- Today --------------------------------------------------------------------------------

const TIERS: Tier[] = ["now", "soon", "fyi"];

function TodayCard({
  today,
  role,
  now,
  onReleased,
}: {
  today: ReturnType<typeof presentToday>;
  role: string | null;
  now: number;
  onReleased: () => void;
}) {
  const { locale, t } = useI18n();
  const d = t.overview.today;
  return (
    <Card labelledBy="ov-today">
      <CardHead
        id="ov-today"
        level={2}
        title={d.title}
        note={d.note}
        aside={
          <span className="vb-ov-eyebrow">
            {fill(d.asOf, { time: clock(now, locale) })}
          </span>
        }
      />
      {TIERS.map((tier) => {
        const items = today[tier];
        return (
          <div key={tier} className="vb-ov-tier" data-tier={tier}>
            <h3 className="vb-ov-tier-h">
              <b>{d.tiers[tier].title}</b>
              <span className={`vb-ov-tag vb-ov-tag-${tier}`}>
                {d.tiers[tier].tag}
              </span>
              <small>{byCount(d.count, items.length)}</small>
            </h3>
            {items.length === 0 ? (
              <EmptyState quiet>{d.empty[tier]}</EmptyState>
            ) : (
              <ul className="vb-ov-qlist">
                {items.map((item) => (
                  <TodayRow
                    key={item.key}
                    item={item}
                    tier={tier}
                    role={role}
                    now={now}
                    onReleased={onReleased}
                  />
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </Card>
  );
}

function TodayRow({
  item,
  tier,
  now,
  onReleased,
}: {
  item: TodayItem;
  tier: Tier;
  role: string | null;
  now: number;
  onReleased: () => void;
}) {
  const { locale, t } = useI18n();
  const k = t.overview.today.kinds;
  const time = t.dashboard.time;
  let title = item.name ?? "—";
  let ref = item.ref ?? "";
  let what = "";
  let detail = "";
  let action = "";
  switch (item.kind) {
    case "review_draft":
    case "rework_rejected":
    case "release":
    case "approved_waiting":
      what = fill(k[item.kind].what, { version: item.version ?? 1 });
      action = k[item.kind].action;
      break;
    case "decide_values":
    case "no_draft":
      what = byCount(k[item.kind].what, item.count);
      action = k[item.kind].action;
      break;
    case "values_since_run":
      what = byCount(k.values_since_run.what, item.count);
      detail = fill(k.values_since_run.detail, { run: item.runNumber ?? "—" });
      action = k.values_since_run.action;
      break;
    case "decide_deletion":
    case "execute_deletion":
    case "deletion_waiting":
    case "upload_values":
      what = k[item.kind].what;
      action = k[item.kind].action;
      break;
    case "invitation_open":
      title = fill(k.invitation_open.title, {
        role: roleName(t.roles, item.name),
      });
      ref = "";
      what = fill(k.invitation_open.what, { until: day(item.until, locale) });
      action = k.invitation_open.action;
      break;
    case "prep_baseline":
      title = k.prep_baseline.title;
      what = k.prep_baseline.what;
      action = k.prep_baseline.action;
      break;
    case "prep_follow_up":
      title = k.prep_follow_up.title;
      what = fill(k.prep_follow_up.what, { days: FOLLOW_UP_AFTER_DAYS });
      action = k.prep_follow_up.action;
      break;
    case "released_recently":
      title = byCount(k.released_recently.title, item.count);
      ref = k.released_recently.ref;
      what = item.names.join(", ");
      action = k.released_recently.action;
      break;
  }
  const since = item.since ? ago(item.since, now, time) : "";
  return (
    <li className="vb-ov-qrow" data-tier={tier}>
      <i className="vb-ov-qbar" aria-hidden="true" />
      <div className="vb-ov-qwho">
        <b>{title}</b>
        {ref && <span>{ref}</span>}
      </div>
      <div className="vb-ov-qwhat">
        {what}
        {detail && <small>{detail}</small>}
      </div>
      <span className="vb-ov-qsince">
        {since && (
          <>
            <span className="sr-only">
              {fill(t.overview.today.waited, { since })}
            </span>
            <span aria-hidden="true">{since}</span>
          </>
        )}
      </span>
      <span className="vb-ov-qact">
        {item.kind === "released_recently" ? (
          <button
            type="button"
            className="vb-ov-btn ghost"
            onClick={onReleased}
          >
            {action}
          </button>
        ) : (
          <Link
            href={item.href}
            className={`vb-ov-btn${tier === "now" ? " primary" : ""}`}
            aria-label={`${action}: ${title}`}
          >
            {action}
          </Link>
        )}
      </span>
    </li>
  );
}

// --- The work list ------------------------------------------------------------------------

const WORK_GRID =
  "minmax(200px,1.6fr) minmax(130px,0.9fr) minmax(190px,1.4fr) 150px 110px";

function Worklist({
  data,
  tab,
  setTab,
}: {
  data: OverviewData;
  tab: TabKey;
  setTab: (tab: TabKey) => void;
}) {
  const router = useRouter();
  const { t } = useI18n();
  const w = t.overview.worklist;
  const [term, setTerm] = useState("");
  const raw = useMemo(
    () => new Map(data.rows.map((r) => [r.patient_id, r])),
    [data.rows],
  );
  const rows = data.view.rows;
  const counts = useMemo(() => {
    const out = {} as Record<TabKey, number>;
    for (const key of TABS) out[key] = rows.filter((r) => inTab(r, key)).length;
    return out;
  }, [rows]);
  const visible = useMemo(() => {
    const q = term.toLowerCase();
    return rows.filter(
      (r) => inTab(r, tab) && `${r.name} ${r.ref}`.toLowerCase().includes(q),
    );
  }, [rows, tab, term]);

  return (
    <section
      className="vb-ov-card"
      aria-labelledby="ov-worklist"
      id="arbeitsliste"
      style={{ overflow: "hidden", scrollMarginTop: "16px" }}
    >
      <div className="vb-ov-head">
        <div style={{ minWidth: 0 }}>
          <h2 id="ov-worklist" className="vb-ov-h2">
            {w.title}
          </h2>
          <p className="vb-ov-note">{w.note}</p>
        </div>
        <div className="vb-ov-wltools">
          <div className="vb-ov-tabs" role="group" aria-label={w.title}>
            {TABS.map((key) => (
              <button
                key={key}
                type="button"
                className="vb-ov-tab"
                aria-pressed={tab === key}
                onClick={() => setTab(key)}
              >
                {w.tabs[key]} <span className="vb-ov-tab-n">{counts[key]}</span>
              </button>
            ))}
          </div>
          <input
            className="vb-input vb-ov-search"
            type="text"
            aria-label={w.search}
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder={w.search}
          />
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <div style={{ minWidth: "820px" }}>
          <div
            className="vb-ov-wlrow vb-ov-wlhead"
            style={{ gridTemplateColumns: WORK_GRID }}
          >
            <span>{w.columns.patient}</span>
            <span>{w.columns.state}</span>
            <span>{w.columns.next}</span>
            <span>{w.columns.values}</span>
            <span style={{ textAlign: "right" }}>{w.columns.updated}</span>
          </div>
          {visible.map((r) => {
            const source = raw.get(r.patientId);
            const step = source ? nextStep(source) : "import";
            const next = w.next[step];
            const who =
              step === "clinical_review"
                ? fill(next.who, { role: roleName(t.roles, "clinician") })
                : step === "release"
                  ? fill(next.who, {
                      role: roleName(t.roles, "medical_director"),
                    })
                  : step === "none"
                    ? fill(next.who, { since: r.updatedLabel })
                    : next.who;
            return (
              <div
                key={r.patientId}
                className="vb-row vb-ov-wlrow"
                {...clickable(
                  () => router.push(`/patients/${r.patientId}`),
                  fill(w.openRow, { name: r.name, ref: r.ref }),
                )}
                style={{ gridTemplateColumns: WORK_GRID, cursor: "pointer" }}
              >
                <div className="vb-ov-pat">
                  <span className="vb-ov-av" aria-hidden="true">
                    {r.initials}
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <b>{r.name}</b>
                    <span>{r.ref}</span>
                  </div>
                </div>
                <div className="vb-ov-state">
                  <Pill meta={r.statusBadge} />
                  {r.version != null && (
                    <span className="vb-ov-mono">v{r.version}</span>
                  )}
                </div>
                <div className="vb-ov-next">
                  {next.title}
                  <small>{who}</small>
                </div>
                <div className="vb-ov-mono">
                  {r.valuesPublished}
                  {r.valuesPending > 0 &&
                    ` · ${fill(w.inReview, { n: r.valuesPending })}`}
                </div>
                <div className="vb-ov-mono" style={{ textAlign: "right" }}>
                  {r.updatedLabel}
                </div>
              </div>
            );
          })}
          {visible.length === 0 && (
            <EmptyState title={w.emptyTitle}>{w.emptyNote}</EmptyState>
          )}
        </div>
      </div>
    </section>
  );
}

// --- Data and sources ---------------------------------------------------------------------

function DataCard({ data }: { data: OverviewData }) {
  const { locale, t } = useI18n();
  const d = t.overview.data;
  const s = t.overview.sources;
  const time = t.dashboard.time;
  const meters = data.coverage ? presentDataMeters(data.coverage) : null;
  const sources = data.sources ? presentSources(data.sources) : null;
  return (
    <Card labelledBy="ov-data">
      <CardHead
        id="ov-data"
        title={d.title}
        note={data.coverage ? byCount(d.note, data.coverage.total) : undefined}
      />
      <div className="vb-ov-body">
        {meters && data.coverage ? (
          <>
            {meters.map((m) => (
              <div key={m.key} className="vb-ov-meter">
                <KeyValue label={d[m.key]} value={`${m.count} / ${m.total}`} />
                <div className="vb-ov-track" aria-hidden="true">
                  <i style={{ width: `${Math.round(m.share * 100)}%` }} />
                </div>
              </div>
            ))}
            <KeyValue
              label={d.latest}
              value={day(data.coverage.latest_observed_at, locale)}
            />
          </>
        ) : (
          <p className="vb-ov-unavailable">{d.unavailable}</p>
        )}
        <h4 className="vb-ov-h4">{s.title}</h4>
        {sources ? (
          <ul className="vb-ov-srclist">
            {sources.map((src) => (
              <li key={src.parserName ?? "other"}>
                <div>
                  {src.key === "other" && src.parserName
                    ? src.parserName
                    : s.names[src.key]}
                  <small>
                    {src.lastImportAt
                      ? fill(byCount(s.last, src.rows), {
                          when: ago(src.lastImportAt, data.now, time),
                        })
                      : src.key === "other"
                        ? s.neverOther
                        : s.neverFile}
                  </small>
                </div>
                <span className="vb-ov-tag">
                  {src.jobs > 0 ? s.state.used : s.state.ready}
                </span>
              </li>
            ))}
            <li>
              <div>
                {s.names.wearables}
                <small>{s.wearablesNote}</small>
              </div>
              <span className="vb-ov-tag">{s.state.none}</span>
            </li>
          </ul>
        ) : (
          <p className="vb-ov-unavailable">{s.unavailable}</p>
        )}
      </div>
    </Card>
  );
}

// --- Activity -----------------------------------------------------------------------------

function ActivityCard({ data }: { data: OverviewData }) {
  const { locale, t } = useI18n();
  const a = t.overview.activity;
  const items = data.activity
    ? presentActivity(data.activity, data.rows)
    : null;
  return (
    <Card labelledBy="ov-activity">
      <CardHead
        id="ov-activity"
        title={a.title}
        note={data.activityScope === "clinic" ? a.noteClinic : a.noteOwn}
        aside={
          data.activityScope === "clinic" ? (
            <Link href="/einstellungen/audit" className="vb-ov-btn ghost">
              {a.open}
            </Link>
          ) : undefined
        }
      />
      <div className="vb-ov-body">
        {items == null ? (
          <p className="vb-ov-unavailable">{a.unavailable}</p>
        ) : items.length === 0 ? (
          <EmptyState quiet style={{ padding: 0 }}>
            {a.empty}
          </EmptyState>
        ) : (
          <ul className="vb-ov-feed">
            {items.map((e) => (
              <li key={e.id}>
                <i aria-hidden="true" />
                <div>
                  <b>{actionLabel(e.action, locale)}</b>
                  {(e.patientName ?? e.targetType) &&
                    ` · ${e.patientName ?? targetLabel(e.targetType, locale)}`}
                  {e.actor && <small>{e.actor}</small>}
                </div>
                <span className="vb-ov-mono">
                  {ago(e.at, data.now, t.dashboard.time)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
