// What the overview puts in front of a colleague (docs/notes/0015): what waits on their role
// now, what comes next, and what happened — and, under it, the work list with each record's
// next step, the clinic's weeks, its data and its sources, and the latest activity.
//
// Workflow only. Every item is a state of the workflow the API reports (a report's status, a
// count of values, a request, an invitation, a statement's date); nothing here reads a value,
// ranks a patient or estimates urgency. Within a tier the order is the kind of work, then how
// long it has waited — never a clinical judgement.
//
// No wording: the page says each kind in its language. Relative imports only: the Playwright
// runner imports this module directly (apps/web/e2e/today.spec.ts).

import type {
  AuditEvent,
  Coverage,
  DeletionRequestView,
  PreparationTime,
  Source,
  StaffInvitationListItem,
  Throughput,
  WorklistRow,
} from "../api";

export type Tier = "now" | "soon" | "fyi";

export type TodayKind =
  // Now — waits on the reader's role.
  | "review_draft" // clinician: a draft to review
  | "rework_rejected" // clinician: a rejected version to rework
  | "decide_values" // clinician: values awaiting a decision in the review queue
  | "release" // medical director: an approved report to release
  | "decide_deletion" // medical director: an erasure request to decide
  | "execute_deletion" // owner, medical director: an approved erasure to carry out
  | "upload_values" // assistant: a record without any value yet
  | "invitation_open" // owner: a team invitation not yet redeemed
  | "prep_baseline" // owner: no baseline for the preparation time
  | "prep_follow_up" // owner: no preparation-time statement in the last 30 days
  // Soon — for every role.
  | "values_since_run" // values received after the latest interpretation run
  | "no_draft" // published values, no report yet
  // For information.
  | "approved_waiting" // clinician: approved, waits on the medical director
  | "deletion_waiting" // owner: requested, waits on the medical director
  | "released_recently"; // reports released in the last 7 days

export const TIER_OF: Record<TodayKind, Tier> = {
  review_draft: "now",
  rework_rejected: "now",
  decide_values: "now",
  release: "now",
  decide_deletion: "now",
  execute_deletion: "now",
  upload_values: "now",
  invitation_open: "now",
  prep_baseline: "now",
  prep_follow_up: "now",
  values_since_run: "soon",
  no_draft: "soon",
  approved_waiting: "fyi",
  deletion_waiting: "fyi",
  released_recently: "fyi",
};

// The order within a tier: the kind of work first.
const KIND_ORDER = Object.keys(TIER_OF) as TodayKind[];

export interface TodayItem {
  key: string;
  kind: TodayKind;
  patientId: string | null;
  name: string | null;
  ref: string | null;
  // What the kind counts: values, reports; 1 for a single thing.
  count: number;
  version: number | null;
  runNumber: number | null;
  // When the thing began to wait (ISO); null when nothing says.
  since: string | null;
  // An invitation's expiry (ISO).
  until: string | null;
  // released_recently: whose reports.
  names: string[];
  href: string;
}

export interface TodayView {
  now: TodayItem[];
  soon: TodayItem[];
  fyi: TodayItem[];
}

export interface TodayInput {
  role: string | null;
  rows: WorklistRow[];
  // Loaded only for the roles that may read them; null otherwise.
  deletionRequests?: DeletionRequestView[] | null;
  invitations?: StaffInvitationListItem[] | null;
  preparation?: PreparationTime | null;
  now: number;
}

const DAY_MS = 86_400_000;
// A preparation-time statement older than this asks for the next one.
export const FOLLOW_UP_AFTER_DAYS = 30;
export const RECENT_RELEASE_DAYS = 7;

const DRAFT = new Set(["draft_generated", "draft_edited"]);

const reportHref = (r: WorklistRow) =>
  r.report_id
    ? `/patients/${r.patient_id}/assessments/${r.report_id}`
    : `/patients/${r.patient_id}`;
const patientHref = (r: WorklistRow) => `/patients/${r.patient_id}`;

function time(iso: string | null | undefined): number {
  const t = iso ? Date.parse(iso) : NaN;
  return Number.isFinite(t) ? t : NaN;
}

function item(
  kind: TodayKind,
  key: string,
  over: Partial<TodayItem> & { href: string },
): TodayItem {
  return {
    key: `${kind}:${key}`,
    kind,
    patientId: null,
    name: null,
    ref: null,
    count: 1,
    version: null,
    runNumber: null,
    since: null,
    until: null,
    names: [],
    ...over,
  };
}

function forRow(
  kind: TodayKind,
  r: WorklistRow,
  over: Partial<TodayItem> & { href: string },
): TodayItem {
  return item(kind, r.patient_id, {
    patientId: r.patient_id,
    name: r.display_name,
    ref: r.external_ref ?? null,
    version: r.version_no ?? null,
    ...over,
  });
}

function rowItems(input: TodayInput): TodayItem[] {
  const { role, rows, now } = input;
  const out: TodayItem[] = [];
  const recent: WorklistRow[] = [];
  for (const r of rows) {
    const status = r.report_status ?? null;
    const statusAt = r.status_at ?? r.updated_at;
    if (role === "clinician") {
      if (status && DRAFT.has(status))
        out.push(
          forRow("review_draft", r, { since: statusAt, href: reportHref(r) }),
        );
      if (status === "rejected")
        out.push(
          forRow("rework_rejected", r, {
            since: statusAt,
            href: reportHref(r),
          }),
        );
      if ((r.values_pending ?? 0) > 0)
        out.push(
          forRow("decide_values", r, {
            count: r.values_pending ?? 0,
            since: r.pending_since ?? null,
            href: "/review-queue",
          }),
        );
      if (status === "approved")
        out.push(
          forRow("approved_waiting", r, {
            since: statusAt,
            href: reportHref(r),
          }),
        );
    }
    if (role === "medical_director" && status === "approved")
      out.push(forRow("release", r, { since: statusAt, href: reportHref(r) }));
    if (
      role === "assistant" &&
      (r.values_published ?? 0) === 0 &&
      (r.values_pending ?? 0) === 0
    )
      out.push(
        forRow("upload_values", r, {
          since: r.updated_at,
          href: patientHref(r),
        }),
      );

    // Soon: the same for every role.
    if (r.latest_run_number != null && (r.values_since_run ?? 0) > 0)
      out.push(
        forRow("values_since_run", r, {
          count: r.values_since_run ?? 0,
          runNumber: r.latest_run_number,
          since: r.latest_received_at ?? null,
          href: patientHref(r),
        }),
      );
    if (r.report_id == null && (r.values_published ?? 0) > 0)
      out.push(
        forRow("no_draft", r, {
          count: r.values_published ?? 0,
          since: r.latest_received_at ?? null,
          href: patientHref(r),
        }),
      );

    if (
      status === "released" &&
      now - time(statusAt) <= RECENT_RELEASE_DAYS * DAY_MS
    )
      recent.push(r);
  }
  if (recent.length > 0) {
    const newest = recent.reduce((a, b) =>
      time(b.status_at ?? b.updated_at) > time(a.status_at ?? a.updated_at)
        ? b
        : a,
    );
    out.push(
      item("released_recently", "all", {
        count: recent.length,
        names: recent
          .map((r) => r.display_name)
          .sort((a, b) => a.localeCompare(b)),
        since: newest.status_at ?? newest.updated_at,
        href: "#arbeitsliste",
      }),
    );
  }
  return out;
}

function governanceItems(input: TodayInput): TodayItem[] {
  const { role, now } = input;
  const out: TodayItem[] = [];
  for (const d of input.deletionRequests ?? []) {
    const href = "/einstellungen/loeschantraege";
    const common = {
      patientId: d.patient_id,
      name: d.patient_display_name,
      href,
    };
    if (d.status === "pending" && role === "medical_director")
      out.push(
        item("decide_deletion", d.id, { ...common, since: d.requested_at }),
      );
    if (d.status === "pending" && role === "owner")
      out.push(
        item("deletion_waiting", d.id, { ...common, since: d.requested_at }),
      );
    if (
      d.status === "approved" &&
      (role === "owner" || role === "medical_director")
    )
      out.push(
        item("execute_deletion", d.id, {
          ...common,
          since: d.decided_at ?? d.requested_at,
        }),
      );
  }
  if (role === "owner") {
    for (const inv of input.invitations ?? []) {
      if (inv.status !== "pending" || time(inv.expires_at) <= now) continue;
      out.push(
        item("invitation_open", inv.invitation_id, {
          name: inv.role,
          since: inv.created_at,
          until: inv.expires_at,
          href: "/einstellungen/mitglieder",
        }),
      );
    }
    const prep = input.preparation;
    if (prep) {
      const href = "/einstellungen/vorbereitungszeit";
      if (!prep.baseline) {
        out.push(item("prep_baseline", "baseline", { href }));
      } else {
        const latest = [prep.baseline, prep.latest_follow_up]
          .filter((s) => s != null)
          .map((s) => s.recorded_at)
          .reduce((a, b) => (time(b) > time(a) ? b : a));
        if (now - time(latest) > FOLLOW_UP_AFTER_DAYS * DAY_MS)
          out.push(
            item("prep_follow_up", "follow_up", { since: latest, href }),
          );
      }
    }
  }
  return out;
}

// Kind first, then the longest wait; a thing without a time after those with one.
function byWorkThenAge(a: TodayItem, b: TodayItem): number {
  const kind = KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind);
  if (kind !== 0) return kind;
  const ta = time(a.since);
  const tb = time(b.since);
  if (Number.isNaN(ta) !== Number.isNaN(tb)) return Number.isNaN(ta) ? 1 : -1;
  if (ta !== tb && !Number.isNaN(ta)) return ta - tb;
  return (a.name ?? "").localeCompare(b.name ?? "");
}

export function presentToday(input: TodayInput): TodayView {
  const all = [...rowItems(input), ...governanceItems(input)].sort(
    byWorkThenAge,
  );
  return {
    now: all.filter((i) => TIER_OF[i.kind] === "now"),
    soon: all.filter((i) => TIER_OF[i.kind] === "soon"),
    fyi: all.filter((i) => TIER_OF[i.kind] === "fyi"),
  };
}

// --- The work list's next step ---------------------------------------------------------------

export type NextStep =
  | "clinical_review" // a draft: the clinician reviews it
  | "release" // approved: the medical director releases it
  | "rework" // rejected: the version is reworked
  | "none" // released: nothing open
  | "draft" // values, no report: a draft can be created
  | "import"; // nothing yet: values are read in

export function nextStep(r: WorklistRow): NextStep {
  const status = r.report_status ?? null;
  if (status && DRAFT.has(status)) return "clinical_review";
  if (status === "approved") return "release";
  if (status === "rejected") return "rework";
  if (status === "released") return "none";
  return (r.values_published ?? 0) > 0 ? "draft" : "import";
}

// --- The band of counts -----------------------------------------------------------------------

export interface Statband {
  openReviews: number;
  toRelease: number;
  valuesInReview: number;
  // Released in the window the throughput covers; null when it could not be read.
  released: number | null;
  releasedDays: number | null;
  // One count per day of that window, oldest first.
  releasedByDay: number[];
  patients: number;
  withReport: number;
  withoutReport: number;
}

export function presentStatband(
  rows: WorklistRow[],
  throughput: Throughput | null,
): Statband {
  return {
    openReviews: rows.filter(
      (r) => r.report_status && DRAFT.has(r.report_status),
    ).length,
    toRelease: rows.filter((r) => r.report_status === "approved").length,
    valuesInReview: rows.reduce((n, r) => n + (r.values_pending ?? 0), 0),
    released: throughput ? (throughput.total_released ?? 0) : null,
    releasedDays: throughput ? throughput.days : null,
    releasedByDay: throughput
      ? throughput.buckets.map((b) => b.released ?? 0)
      : [],
    patients: rows.length,
    withReport: rows.filter((r) => r.report_id != null).length,
    withoutReport: rows.filter((r) => r.report_id == null).length,
  };
}

// --- The clinic's weeks -----------------------------------------------------------------------

export interface WeekBar {
  // ISO 8601 week and the year it belongs to.
  week: number;
  year: number;
  // The first and last day of the window that fall in this week (YYYY-MM-DD); a week at
  // either end of the window can be partial.
  from: string;
  to: string;
  days: number;
  created: number;
  signed: number;
  released: number;
}

function isoWeek(day: string): { week: number; year: number } {
  const [y, m, d] = day.split("-").map(Number);
  const date = new Date(Date.UTC(y!, m! - 1, d!));
  const weekday = date.getUTCDay() || 7;
  // The Thursday of this week decides the year it belongs to.
  date.setUTCDate(date.getUTCDate() + 4 - weekday);
  const yearStart = Date.UTC(date.getUTCFullYear(), 0, 1);
  const week = Math.ceil(((date.getTime() - yearStart) / DAY_MS + 1) / 7);
  return { week, year: date.getUTCFullYear() };
}

// The daily buckets (UTC days, oldest first), summed per ISO week.
export function presentWeeks(throughput: Throughput): WeekBar[] {
  const weeks: WeekBar[] = [];
  for (const b of throughput.buckets) {
    const { week, year } = isoWeek(b.date);
    let bar = weeks[weeks.length - 1];
    if (!bar || bar.week !== week || bar.year !== year) {
      bar = {
        week,
        year,
        from: b.date,
        to: b.date,
        days: 0,
        created: 0,
        signed: 0,
        released: 0,
      };
      weeks.push(bar);
    }
    bar.to = b.date;
    bar.days += 1;
    bar.created += b.created;
    bar.signed += b.signed;
    bar.released += b.released ?? 0;
  }
  return weeks;
}

// --- Data and sources -------------------------------------------------------------------------

export interface DataMeter {
  key: "published" | "withReference" | "withKpi";
  count: number;
  total: number;
  // 0..1; 0 without any observation.
  share: number;
}

export function presentDataMeters(c: Coverage): DataMeter[] {
  const meter = (key: DataMeter["key"], count: number): DataMeter => ({
    key,
    count,
    total: c.total,
    share: c.total > 0 ? count / c.total : 0,
  });
  return [
    meter("published", c.published),
    meter("withReference", c.with_reference),
    meter("withKpi", c.with_kpi ?? 0),
  ];
}

export type SourceKey = "csv" | "ldt2" | "ldt3" | "other";

const SOURCE_KEYS: Record<string, SourceKey> = {
  "hadp-csv": "csv",
  "ldt2-8201": "ldt2",
  "ldt3-8205": "ldt3",
};

export interface SourceView {
  key: SourceKey;
  // A name the API sent that this page does not know: shown as it is.
  parserName: string | null;
  jobs: number;
  rows: number;
  lastImportAt: string | null;
}

export function presentSources(lines: Source[]): SourceView[] {
  return lines.map((l) => ({
    key:
      l.parser_name == null ? "other" : (SOURCE_KEYS[l.parser_name] ?? "other"),
    parserName: l.parser_name ?? null,
    jobs: l.jobs,
    rows: l.rows,
    lastImportAt: l.last_import_at ?? null,
  }));
}

// --- Activity ---------------------------------------------------------------------------------

export interface ActivityItem {
  id: string;
  action: string;
  at: string;
  actor: string | null;
  // The record the event is about, when the page knows it: by patient, or by report.
  patientName: string | null;
  patientId: string | null;
  targetType: string | null;
}

// Entering a clinic is recorded at every sign-in; the trail keeps it, the overview leaves it
// out (with reads and listings, which the API leaves out already).
const NOT_SHOWN = new Set(["tenant.select"]);
export const ACTIVITY_SHOWN = 5;

export function presentActivity(
  events: AuditEvent[],
  rows: WorklistRow[],
  limit = ACTIVITY_SHOWN,
): ActivityItem[] {
  const byPatient = new Map(rows.map((r) => [r.patient_id, r]));
  const byReport = new Map(
    rows.filter((r) => r.report_id).map((r) => [r.report_id as string, r]),
  );
  return events
    .filter((e) => !NOT_SHOWN.has(e.action))
    .slice(0, limit)
    .map((e) => {
      const target = e.target_id ?? null;
      const row =
        target == null
          ? undefined
          : e.target_type === "patient"
            ? byPatient.get(target)
            : e.target_type === "report"
              ? byReport.get(target)
              : undefined;
      return {
        id: e.id,
        action: e.action,
        at: e.occurred_at,
        actor: e.actor?.display_name ?? null,
        patientName: row?.display_name ?? null,
        patientId: row?.patient_id ?? null,
        targetType: e.target_type ?? null,
      };
    });
}
