import { expect, test } from "@playwright/test";

import type { PreparationRow } from "../src/lib/api";
import { presentPracticePrep } from "../src/lib/presenters/practicePrep";
import { asStaff, hydrated } from "./support/staff";

// The practice view (apps/web/src/lib/presenters/practicePrep.ts, docs/notes/0023): the page
// before a visit for every record at once. The API counts (apps/api tests cover the counts);
// the presenter orders, filters and sorts what it sent. No browser for the presenter; one
// browser pass over the demo clinic for the page, its filters, a sort and the way to a record.

let seq = 0;
function row(
  over: Partial<PreparationRow> & { display_name: string },
): PreparationRow {
  seq += 1;
  return {
    patient_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    external_ref: null,
    report_status: null,
    updated_at: "2026-03-12T08:00:00Z",
    latest_run_number: 1,
    latest_run_at: "2026-03-12T08:00:00Z",
    new_since_run: 0,
    new_outside: 0,
    outside: 0,
    stale_core: 0,
    missing_core: 0,
    values_pending: 0,
    unassigned: 0,
    domains_without_verdict: 0,
    ...over,
  };
}

const ROWS: PreparationRow[] = [
  row({ display_name: "Released", report_status: "released", outside: 2 }),
  row({ display_name: "Approved", report_status: "approved", stale_core: 3 }),
  row({
    display_name: "No draft",
    external_ref: "SYN-9",
    latest_run_number: null,
    latest_run_at: null,
    domains_without_verdict: null,
    missing_core: 43,
  }),
  row({
    display_name: "Draft B",
    report_status: "draft_edited",
    new_since_run: 1,
  }),
  row({
    display_name: "Draft A",
    report_status: "draft_generated",
    new_since_run: 4,
    new_outside: 1,
    outside: 1,
    values_pending: 2,
    domains_without_verdict: 2,
  }),
];

const names = (rows: PreparationRow[]) => rows.map((r) => r.display_name);

test("the order is workflow: where the report stands, then the name", () => {
  const view = presentPracticePrep(ROWS);
  expect(names(view.rows)).toEqual([
    "Draft A",
    "Draft B",
    "Approved",
    "No draft",
    "Released",
  ]);
  expect(view.total).toBe(5);
});

test("a filter keeps the records with that fact; every filter's count is told", () => {
  const view = presentPracticePrep(ROWS, { filter: "newValues" });
  expect(names(view.rows)).toEqual(["Draft A", "Draft B"]);
  expect(view.counts).toEqual({
    newValues: 2,
    outside: 2,
    stale: 1,
    missing: 1,
    pending: 1,
    noVerdict: 1,
    noRun: 1,
  });
  expect(names(presentPracticePrep(ROWS, { filter: "noRun" }).rows)).toEqual([
    "No draft",
  ]);
  // Without a run there is no verdict to be missing: the record is not "without verdict".
  expect(
    names(presentPracticePrep(ROWS, { filter: "noVerdict" }).rows),
  ).toEqual(["Draft A"]);
});

test("a column sorts by its number, ties in workflow order; the search reads name and ID", () => {
  const desc = presentPracticePrep(ROWS, {
    sort: { column: "outside", direction: "desc" },
  });
  expect(names(desc.rows)).toEqual([
    "Released",
    "Draft A",
    "Draft B",
    "Approved",
    "No draft",
  ]);
  const asc = presentPracticePrep(ROWS, {
    sort: { column: "patient", direction: "asc" },
  });
  expect(names(asc.rows)).toEqual([
    "Approved",
    "Draft A",
    "Draft B",
    "No draft",
    "Released",
  ]);
  const found = presentPracticePrep(ROWS, { query: "syn-9" });
  expect(names(found.rows)).toEqual(["No draft"]);
  expect(found.counts.missing).toBe(1);
  expect(found.counts.outside).toBe(0);
});

test("the page lists every record, filters, sorts and leads to a record's own page", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/vorbereitung");
    await expect(
      page.getByRole("heading", { level: 1, name: "Vorbereitung je Akte" }),
    ).toBeVisible();
    const table = page.getByRole("table");
    await expect(table).toBeVisible();
    const seeded = table.getByRole("row").filter({ hasText: "SYN-0001" });
    await expect(seeded).toHaveCount(1);
    const open = seeded.getByRole("link", {
      name: /^Vorbereitung für .* öffnen$/,
    });
    await expect(open).toHaveAttribute(
      "href",
      /^\/patients\/[0-9a-f-]{36}\/vorbereitung$/,
    );

    // A filter is a pressed button; the one without a match says so and takes nothing away
    // from the others.
    const all = page.getByRole("button", { name: /^Alle \d+$/ });
    await hydrated(all);
    await expect(all).toHaveAttribute("aria-pressed", "true");
    const stale = page.getByRole("button", {
      name: /^Älter als 180 Tage \d+$/,
    });
    await stale.click();
    await expect(stale).toHaveAttribute("aria-pressed", "true");
    await expect(all).toHaveAttribute("aria-pressed", "false");
    await stale.click();
    await expect(all).toHaveAttribute("aria-pressed", "true");

    // A column's heading sorts by it: numbers largest first, then smallest first, then the
    // workflow order again.
    const outside = page.getByRole("button", {
      name: "Nach Außerhalb sortieren",
    });
    await outside.click();
    await expect(
      page.getByRole("columnheader", { name: /Außerhalb/ }),
    ).toHaveAttribute("aria-sort", "descending");
    await outside.click();
    await expect(
      page.getByRole("columnheader", { name: /Außerhalb/ }),
    ).toHaveAttribute("aria-sort", "ascending");

    // The search narrows by name or ID.
    const search = page.getByRole("textbox", {
      name: "Patient oder ID suchen",
    });
    await search.fill("SYN-0001");
    await expect(
      table.getByRole("row").filter({ hasText: "SYN-" }),
    ).toHaveCount(1);

    // The way to the page from the work list and from the patient directory.
    await page.goto("/overview");
    await expect(
      page.getByRole("link", { name: "Vorbereitung je Akte" }).first(),
    ).toHaveAttribute("href", "/vorbereitung");
    await page.goto("/patients");
    await expect(
      page.getByRole("link", { name: "Vorbereitung je Akte" }).first(),
    ).toHaveAttribute("href", "/vorbereitung");
  });
});
