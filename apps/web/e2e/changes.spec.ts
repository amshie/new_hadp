import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import type { ChangeRow } from "../src/lib/api";
import { presentChanges } from "../src/lib/presenters/changes";
import { asStaff, hydrated, openTab } from "./support/staff";

// Seit zuletzt (apps/web/src/lib/presenters/changes.ts, docs/notes/0024): what arrived or
// moved in a record since the person last opened it. The API decides what counts (apps/api
// tests cover that); the presenter only orders. One browser pass tells the whole story: a
// clinician opens a record, a colleague imports a file into it, the overview names it to the
// clinician, and opening the record again is what clears it.

test.describe.configure({ mode: "serial" });

const run = randomUUID().slice(0, 8);
const patient = { name: `Synthetic Changes ${run}`, ref: `CHG-${run}` };

// The laboratory file, marked per run as the primary workflow marks its copy (the API keeps a
// file once per clinic, by checksum).
const labFile = {
  name: `synthetic-changes-${run}.csv`,
  mimeType: "text/csv",
  buffer: Buffer.from(
    readFileSync(
      join(__dirname, "fixtures", "lab-report.synthetic.csv"),
      "utf8",
    ).replaceAll("SYNTHETIC-E2E", `SYNTHETIC-CHG-${run}`),
    "utf8",
  ),
};

let patientPath = "";

let seq = 0;
function row(over: Partial<ChangeRow> & { display_name: string }): ChangeRow {
  seq += 1;
  return {
    patient_id: `00000000-0000-4000-8000-${String(seq).padStart(12, "0")}`,
    external_ref: null,
    last_opened_at: "2026-03-10T08:00:00Z",
    new_published: 0,
    new_pending: 0,
    latest_received_at: null,
    run_number: null,
    run_at: null,
    report_status: null,
    report_version_no: null,
    report_status_at: null,
    changed_at: "2026-03-12T08:00:00Z",
    ...over,
  };
}

test("the latest change comes first; the same instant by name", () => {
  const view = presentChanges([
    row({ display_name: "Older", changed_at: "2026-03-11T08:00:00Z" }),
    row({ display_name: "Second same", changed_at: "2026-03-12T08:00:00Z" }),
    row({ display_name: "First same", changed_at: "2026-03-12T08:00:00Z" }),
    row({ display_name: "Newest", changed_at: "2026-03-13T08:00:00Z" }),
  ]);
  expect(view.map((r) => r.display_name)).toEqual([
    "Newest",
    "First same",
    "Second same",
    "Older",
  ]);
});

test("the clinician creates a record and opens it: nothing is new in it yet", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/patients");
    const add = page.getByRole("button", {
      name: "Patient hinzufügen",
      exact: true,
    });
    await hydrated(add);
    await add.click();
    const wizard = page.getByRole("dialog", { name: "Patient hinzufügen" });
    const name = wizard.getByRole("textbox", { name: "Name", exact: true });
    await expect(name).toBeFocused();
    await name.fill(patient.name);
    await wizard.getByRole("textbox", { name: "Externe ID" }).fill(patient.ref);
    await wizard.getByRole("button", { name: "Weiter" }).click();
    await wizard.getByRole("button", { name: "Weiter" }).click();
    await wizard.getByRole("button", { name: "Patient anlegen" }).click();
    const created = page.getByRole("dialog", { name: "Patient angelegt" });
    await created.getByRole("button", { name: "Akte öffnen" }).click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    patientPath = new URL(page.url()).pathname;
    // The address changes before the server has rendered the record; the opening is only
    // recorded once it has. Its heading says so.
    await expect(
      page.getByRole("heading", { level: 1, name: patient.name }),
    ).toBeVisible();

    await page.goto("/overview");
    const card = page.getByRole("region", { name: "Seit zuletzt" });
    await expect(card).toBeVisible();
    await expect(card).not.toContainText(patient.ref);
  });
});

test("a colleague imports a file into the record", async ({ browser }) => {
  await asStaff(browser, "assistant", async (page) => {
    await page.goto(patientPath);
    await openTab(page, "Akte");
    const lab = page.getByRole("region", { name: "Labordaten" });
    const chooser = lab.getByLabel("Labordatei wählen");
    await hydrated(chooser);
    await chooser.setInputFiles(labFile);
    await lab.getByRole("button", { name: "Hochladen und einlesen" }).click();
    await expect(lab.getByRole("status")).toContainText(
      "1 veröffentlicht · 2 zur Prüfung",
    );
  });
});

test("the overview names the record to the clinician until they open it again", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/overview");
    const card = page.getByRole("region", { name: "Seit zuletzt" });
    const entry = card.getByRole("listitem").filter({ hasText: patient.ref });
    await expect(entry).toHaveCount(1);
    await expect(entry).toContainText("1 neuer Wert");
    await expect(entry).toContainText("2 Werte in Prüfung");
    await expect(entry).toContainText("zuletzt geöffnet");
    const open = entry.getByRole("link", {
      name: `Akte öffnen: ${patient.name}`,
    });
    await expect(open).toHaveAttribute("href", patientPath);
    await hydrated(open);
    await open.click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    await expect(
      page.getByRole("heading", { level: 1, name: patient.name }),
    ).toBeVisible();

    // Opening the record is what clears it.
    await page.goto("/overview");
    await expect(
      page.getByRole("region", { name: "Seit zuletzt" }),
    ).not.toContainText(patient.ref);
  });
});
