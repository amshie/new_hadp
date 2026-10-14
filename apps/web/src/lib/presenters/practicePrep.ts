// The practice view (docs/notes/0023): the page before a visit for every record at once.
// The API counts; this module orders and filters what it sent. The order is workflow —
// where each report stands, then the name — and a person may sort by a column. No count
// is ranked as urgent, weighted or summed into anything (ADR-0003).
//
// Relative imports only: the Playwright runner imports this module directly
// (apps/web/e2e/practice-prep.spec.ts).

import type { PreparationRow } from "../api";

export type PrepFilter =
  | "newValues"
  | "outside"
  | "stale"
  | "missing"
  | "pending"
  | "noVerdict"
  | "noRun";
export const PREP_FILTERS: readonly PrepFilter[] = [
  "newValues",
  "outside",
  "stale",
  "missing",
  "pending",
  "noVerdict",
  "noRun",
];

export type PrepColumn =
  | "patient"
  | "status"
  | "run"
  | "newValues"
  | "outside"
  | "stale"
  | "missing"
  | "pending"
  | "noVerdict";

export interface PrepSort {
  column: PrepColumn;
  direction: "asc" | "desc";
}

// Where a report stands, as the work list orders it: what waits for the clinic first.
const STATUS_ORDER: Record<string, number> = {
  draft_generated: 0,
  draft_edited: 0,
  approved: 1,
  rejected: 2,
  released: 4,
};

function statusRank(status: string | null | undefined): number {
  if (status == null) return 3;
  return STATUS_ORDER[status] ?? 5;
}

export function rowMatches(
  row: PreparationRow,
  filter: PrepFilter | null,
): boolean {
  switch (filter) {
    case null:
      return true;
    case "newValues":
      return row.new_since_run > 0;
    case "outside":
      return row.outside > 0;
    case "stale":
      return row.stale_core > 0;
    case "missing":
      return row.missing_core > 0;
    case "pending":
      return row.values_pending > 0;
    case "noVerdict":
      return (row.domains_without_verdict ?? 0) > 0;
    case "noRun":
      return row.latest_run_number == null;
  }
}

function searchMatches(row: PreparationRow, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return `${row.display_name} ${row.external_ref ?? ""}`
    .toLowerCase()
    .includes(q);
}

function columnValue(row: PreparationRow, column: PrepColumn): number | string {
  switch (column) {
    case "patient":
      return row.display_name;
    case "status":
      return statusRank(row.report_status);
    case "run":
      return row.latest_run_at ?? "";
    case "newValues":
      return row.new_since_run;
    case "outside":
      return row.outside;
    case "stale":
      return row.stale_core;
    case "missing":
      return row.missing_core;
    case "pending":
      return row.values_pending;
    case "noVerdict":
      return row.domains_without_verdict ?? -1;
  }
}

function byWorkflow(a: PreparationRow, b: PreparationRow): number {
  return (
    statusRank(a.report_status) - statusRank(b.report_status) ||
    a.display_name.localeCompare(b.display_name, "de")
  );
}

export interface PracticePrepView {
  rows: PreparationRow[];
  total: number;
  // How many records each filter would show.
  counts: Record<PrepFilter, number>;
}

export function presentPracticePrep(
  rows: PreparationRow[],
  options: {
    filter?: PrepFilter | null;
    sort?: PrepSort | null;
    query?: string;
  } = {},
): PracticePrepView {
  const filter = options.filter ?? null;
  const query = options.query ?? "";
  const searched = rows.filter((r) => searchMatches(r, query));
  const shown = searched.filter((r) => rowMatches(r, filter));
  const sorted = [...shown].sort(byWorkflow);
  const sort = options.sort ?? null;
  if (sort) {
    const sign = sort.direction === "asc" ? 1 : -1;
    sorted.sort((a, b) => {
      const va = columnValue(a, sort.column);
      const vb = columnValue(b, sort.column);
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb), "de");
      return cmp !== 0 ? sign * cmp : byWorkflow(a, b);
    });
  }
  const counts = Object.fromEntries(
    PREP_FILTERS.map((f) => [
      f,
      searched.filter((r) => rowMatches(r, f)).length,
    ]),
  ) as Record<PrepFilter, number>;
  return { rows: sorted, total: rows.length, counts };
}
