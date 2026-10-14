import { expect, test } from "@playwright/test";

import type {
  AuditEvent,
  DeletionRequestView,
  PreparationTime,
  StaffInvitationListItem,
  Throughput,
  WorklistRow,
} from "../src/lib/api";
import {
  nextStep,
  presentActivity,
  presentDataMeters,
  presentSources,
  presentStatband,
  presentToday,
  presentWeeks,
  type TodayView,
} from "../src/lib/presenters/today";

// What the overview puts in front of each role (apps/web/src/lib/presenters/today.ts): the
// three tiers of "Heute", each record's next step, the weeks, the data, the sources and the
// activity. Workflow only — no browser.

const NOW = Date.parse("2026-10-14T08:00:00Z");
const H = 3_600_000;
const D = 24 * H;
const iso = (ms: number) => new Date(ms).toISOString();

let seq = 0;
function row(over: Partial<WorklistRow>): WorklistRow {
  seq += 1;
  return {
    patient_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    report_id: null,
    display_name: `Synthetic ${seq}`,
    external_ref: `SYN-${seq}`,
    date_of_birth: null,
    report_status: null,
    version_no: null,
    updated_at: iso(NOW - 10 * D),
    status_at: null,
    values_published: 0,
    values_pending: 0,
    pending_since: null,
    latest_received_at: null,
    latest_run_number: null,
    latest_run_at: null,
    values_since_run: 0,
    ...over,
  };
}

function report(status: string, at: number, over: Partial<WorklistRow> = {}) {
  return row({
    report_id: `10000000-0000-4000-8000-${String(seq + 1).padStart(12, "0")}`,
    report_status: status,
    version_no: 2,
    status_at: iso(at),
    values_published: 3,
    ...over,
  });
}

const kinds = (view: TodayView) => ({
  now: view.now.map((i) => i.kind),
  soon: view.soon.map((i) => i.kind),
  fyi: view.fyi.map((i) => i.kind),
});

// One clinic as every role sees it.
const draftOld = report("draft_edited", NOW - 3 * D);
const draftNew = report("draft_generated", NOW - 1 * H);
const rejected = report("rejected", NOW - 2 * D);
const approved = report("approved", NOW - 5 * H);
const releasedRecent = report("released", NOW - 2 * D);
const releasedOld = report("released", NOW - 9 * D);
const pending = row({
  values_published: 4,
  values_pending: 2,
  pending_since: iso(NOW - 4 * D),
  latest_received_at: iso(NOW - 4 * D),
  latest_run_number: 3,
  latest_run_at: iso(NOW - 6 * D),
  values_since_run: 5,
  report_id: "20000000-0000-4000-8000-000000000001",
  report_status: "released",
  status_at: iso(NOW - 20 * D),
});
const noDraft = row({
  values_published: 7,
  latest_received_at: iso(NOW - 6 * H),
});
const empty = row({ updated_at: iso(NOW - 12 * D) });
const ROWS = [
  draftNew,
  draftOld,
  rejected,
  approved,
  releasedRecent,
  releasedOld,
  pending,
  noDraft,
  empty,
];

const deletion = (
  status: string,
  over: Partial<DeletionRequestView> = {},
): DeletionRequestView => ({
  id: `30000000-0000-4000-8000-${status.padStart(12, "0").slice(-12)}`,
  patient_id: empty.patient_id,
  patient_display_name: empty.display_name,
  patient_erased: false,
  status,
  reason_category: "patient_request",
  requested_by_user_id: null,
  requested_at: iso(NOW - 2 * D),
  decided_by_user_id: null,
  decided_at: status === "approved" ? iso(NOW - 1 * D) : null,
  executed_at: null,
  ...over,
});
const DELETIONS = [
  deletion("pending"),
  deletion("approved"),
  deletion("executed"),
];

const invitation = (
  status: string,
  expires: number,
): StaffInvitationListItem => ({
  invitation_id: `40000000-0000-4000-8000-${String(expires).slice(-12)}`,
  role: "clinician",
  status,
  expires_at: iso(expires),
  created_at: iso(NOW - 1 * D),
});

function prep(
  baseline: number | null,
  followUp: number | null = null,
): PreparationTime {
  const statement = (kind: "baseline" | "follow_up", at: number) => ({
    id: `50000000-0000-4000-8000-${String(at).slice(-12)}`,
    kind,
    basis: "estimate" as const,
    median_minutes: 45,
    sample_size: null,
    recorded_at: iso(at),
    recorded_by: null,
  });
  const measured = {
    since: null,
    reports: 0,
    median_seconds: null,
    q1_seconds: null,
    q3_seconds: null,
  };
  return {
    definition: "test",
    minimum_reports: 5,
    baseline: baseline == null ? null : statement("baseline", baseline),
    latest_follow_up:
      followUp == null ? null : statement("follow_up", followUp),
    statements: [],
    statements_total: 0,
    measured_all_time: measured,
    measured_last_30_days: measured,
  } as PreparationTime;
}

test("the clinician's now: drafts, rejected versions and values to decide — oldest first", () => {
  const view = presentToday({ role: "clinician", rows: ROWS, now: NOW });
  expect(kinds(view)).toEqual({
    now: ["review_draft", "review_draft", "rework_rejected", "decide_values"],
    soon: ["values_since_run", "no_draft"],
    fyi: ["approved_waiting", "released_recently"],
  });
  // Within a kind, the one waiting longest comes first.
  expect(view.now.slice(0, 2).map((i) => i.patientId)).toEqual([
    draftOld.patient_id,
    draftNew.patient_id,
  ]);
  const values = view.now.find((i) => i.kind === "decide_values")!;
  expect(values).toMatchObject({
    count: 2,
    href: "/review-queue",
    since: pending.pending_since,
  });
  expect(view.now[0]!.href).toBe(
    `/patients/${draftOld.patient_id}/assessments/${draftOld.report_id}`,
  );
});

test("the medical director's now: releases and erasure decisions", () => {
  const view = presentToday({
    role: "medical_director",
    rows: ROWS,
    deletionRequests: DELETIONS,
    now: NOW,
  });
  expect(kinds(view)).toEqual({
    now: ["release", "decide_deletion", "execute_deletion"],
    soon: ["values_since_run", "no_draft"],
    fyi: ["released_recently"],
  });
  expect(view.now[0]!.patientId).toBe(approved.patient_id);
});

test("the assistant's now: records without any value", () => {
  const view = presentToday({ role: "assistant", rows: ROWS, now: NOW });
  expect(kinds(view).now).toEqual(["upload_values"]);
  expect(view.now[0]).toMatchObject({
    patientId: empty.patient_id,
    href: `/patients/${empty.patient_id}`,
  });
});

test("the owner's now: governance — erasures to carry out, open invitations, the preparation time", () => {
  const view = presentToday({
    role: "owner",
    rows: ROWS,
    deletionRequests: DELETIONS,
    invitations: [
      invitation("pending", NOW + 3 * D),
      invitation("pending", NOW - 1 * H), // expired: not shown
      invitation("redeemed", NOW + 3 * D),
    ],
    preparation: prep(null),
    now: NOW,
  });
  expect(kinds(view)).toEqual({
    now: ["execute_deletion", "invitation_open", "prep_baseline"],
    soon: ["values_since_run", "no_draft"],
    // The request still waits on the medical director: for information.
    fyi: ["deletion_waiting", "released_recently"],
  });
  expect(view.now[1]!.until).toBe(iso(NOW + 3 * D));
});

test("the preparation time asks again 30 days after its newest statement", () => {
  const owner = (p: PreparationTime) =>
    presentToday({ role: "owner", rows: [], preparation: p, now: NOW }).now.map(
      (i) => i.kind,
    );
  expect(owner(prep(NOW - 10 * D))).toEqual([]);
  expect(owner(prep(NOW - 31 * D))).toEqual(["prep_follow_up"]);
  // A recent follow-up counts as the newest statement.
  expect(owner(prep(NOW - 90 * D, NOW - 2 * D))).toEqual([]);
  // Nobody but the owner is asked.
  expect(
    presentToday({
      role: "clinician",
      rows: [],
      preparation: prep(null),
      now: NOW,
    }).now,
  ).toEqual([]);
});

test("released in the last 7 days is one line naming whose reports", () => {
  const view = presentToday({ role: "assistant", rows: ROWS, now: NOW });
  const released = view.fyi.find((i) => i.kind === "released_recently")!;
  expect(released.count).toBe(1);
  expect(released.names).toEqual([releasedRecent.display_name]);
  expect(
    presentToday({ role: "assistant", rows: [releasedOld], now: NOW }).fyi,
  ).toEqual([]);
});

test("an unknown or missing role gets only what is the same for everyone", () => {
  const view = presentToday({
    role: null,
    rows: ROWS,
    deletionRequests: DELETIONS,
    now: NOW,
  });
  expect(view.now).toEqual([]);
  expect(kinds(view).soon).toEqual(["values_since_run", "no_draft"]);
});

test("each record's next step follows its report, then its values", () => {
  expect(nextStep(draftNew)).toBe("clinical_review");
  expect(nextStep(approved)).toBe("release");
  expect(nextStep(rejected)).toBe("rework");
  expect(nextStep(releasedOld)).toBe("none");
  expect(nextStep(noDraft)).toBe("draft");
  expect(nextStep(empty)).toBe("import");
});

const THROUGHPUT: Throughput = {
  days: 10,
  // Thursday 2026-10-01 to Saturday 2026-10-10: ISO weeks 40 (Thu–Sun) and 41 (Mon–Sat).
  buckets: Array.from({ length: 10 }, (_, i) => ({
    date: `2026-10-${String(i + 1).padStart(2, "0")}`,
    created: i % 2,
    signed: i === 9 ? 3 : 0,
    released: i === 2 ? 1 : 0,
  })),
  total_created: 5,
  total_signed: 3,
  total_released: 1,
};

test("the days are summed per ISO week; a week at either end may be partial", () => {
  expect(presentWeeks(THROUGHPUT)).toEqual([
    {
      week: 40,
      year: 2026,
      from: "2026-10-01",
      to: "2026-10-04",
      days: 4,
      created: 2,
      signed: 0,
      released: 1,
    },
    {
      week: 41,
      year: 2026,
      from: "2026-10-05",
      to: "2026-10-10",
      days: 6,
      created: 3,
      signed: 3,
      released: 0,
    },
  ]);
  // Around New Year: 2026-12-31 is in week 53 of 2026, 2027-01-04 in week 1 of 2027.
  const turn = presentWeeks({
    days: 5,
    buckets: [
      "2026-12-31",
      "2027-01-01",
      "2027-01-02",
      "2027-01-03",
      "2027-01-04",
    ].map((date) => ({ date, created: 1, signed: 0, released: 0 })),
    total_created: 5,
    total_signed: 0,
    total_released: 0,
  });
  expect(turn.map((w) => [w.year, w.week, w.days])).toEqual([
    [2026, 53, 4],
    [2027, 1, 1],
  ]);
});

test("the band counts the work list, and the releases of the window", () => {
  const band = presentStatband(ROWS, THROUGHPUT);
  expect(band).toMatchObject({
    openReviews: 2,
    toRelease: 1,
    valuesInReview: 2,
    released: 1,
    releasedDays: 10,
    patients: 9,
    withReport: 7,
    withoutReport: 2,
  });
  expect(band.releasedByDay).toHaveLength(10);
  expect(presentStatband(ROWS, null).released).toBeNull();
});

test("the data meters are counts of the whole; nothing is merged into one figure", () => {
  const meters = presentDataMeters({
    total: 32,
    published: 31,
    with_reference: 16,
    with_kpi: 28,
    latest_observed_at: null,
  });
  expect(meters.map((m) => [m.key, m.count, m.total])).toEqual([
    ["published", 31, 32],
    ["withReference", 16, 32],
    ["withKpi", 28, 32],
  ]);
  expect(
    presentDataMeters({
      total: 0,
      published: 0,
      with_reference: 0,
      with_kpi: 0,
      latest_observed_at: null,
    })[0]!.share,
  ).toBe(0);
});

test("a reader the page does not know is shown by its own name", () => {
  const lines = presentSources([
    { parser_name: "hadp-csv", jobs: 2, rows: 9, last_import_at: iso(NOW) },
    { parser_name: "ldt2-8201", jobs: 0, rows: 0, last_import_at: null },
    { parser_name: "ldt3-8205", jobs: 0, rows: 0, last_import_at: null },
    { parser_name: null, jobs: 1, rows: 1, last_import_at: iso(NOW) },
  ]);
  expect(lines.map((l) => l.key)).toEqual(["csv", "ldt2", "ldt3", "other"]);
  expect(
    presentSources([
      { parser_name: "x-reader", jobs: 1, rows: 1, last_import_at: null },
    ])[0],
  ).toMatchObject({
    key: "other",
    parserName: "x-reader",
  });
});

test("activity names the record when the page knows it, and leaves sign-ins out", () => {
  const event = (
    action: string,
    target_type: string | null,
    target_id: string | null,
  ): AuditEvent => ({
    id: `60000000-0000-4000-8000-${String(++seq).padStart(12, "0")}`,
    occurred_at: iso(NOW - seq * H),
    action,
    actor: {
      user_id: "u",
      display_name: "Synthetic Clinician",
      email: "c@demo.synthetic",
    },
    target_type,
    target_id,
    detail: {},
  });
  const items = presentActivity(
    [
      event("tenant.select", "tenant", null),
      event("report.released", "report", releasedRecent.report_id),
      event("patient.create", "patient", empty.patient_id),
      event(
        "report.draft_generated",
        "report",
        "70000000-0000-4000-8000-000000000001",
      ),
      event("authz.denied", null, null),
    ],
    ROWS,
  );
  expect(items.map((i) => [i.action, i.patientName])).toEqual([
    ["report.released", releasedRecent.display_name],
    ["patient.create", empty.display_name],
    // A report the work list no longer carries: named by its kind on the page.
    ["report.draft_generated", null],
    ["authz.denied", null],
  ]);
  expect(
    presentActivity(
      Array.from({ length: 9 }, () => event("patient.create", null, null)),
      [],
    ).length,
  ).toBe(5);
});
