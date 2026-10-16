import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { asStaff, followLink, hydrated, openTab } from "./support/staff";

// The lab intake agent through the UI alone, on synthetic data: an assistant stores a PDF
// report and has its values proposed; the proposal shows every value beside the page region
// it was read from, all yellow (the text-layer reader proposes with low confidence and no
// plausibility bounds are signed); a clinician looks at one value and confirms it, rejects
// another with a reason, and the confirmed value — and only that one — stands on the
// patient's timeline. The assistant sees the proposal but has no decision to make.
test.describe.configure({ mode: "serial" });

const run = randomUUID().slice(0, 8);
const patient = { name: `Synthetic Intake ${run}`, ref: `INTAKE-${run}` };

// The API stores a file once per clinic (by checksum) and refuses it for a second patient,
// so each run appends a comment after the PDF's end — the reader ignores it, the checksum does
// not.
const pdf = {
  name: `synthetic-intake-${run}.pdf`,
  mimeType: "application/pdf",
  buffer: Buffer.concat([
    readFileSync(join(__dirname, "fixtures", "lab-report.synthetic.pdf")),
    Buffer.from(`\n%run-${run}\n`, "utf8"),
  ]),
};

let patientPath = "";
let proposalPath = "";

test("the assistant creates the patient", async ({ browser }) => {
  await asStaff(browser, "assistant", async (page) => {
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
    await wizard
      .getByRole("checkbox", { name: /^Freigabe geprüfter Berichte/ })
      .check();
    await wizard.getByRole("button", { name: "Weiter" }).click();
    await wizard.getByRole("button", { name: "Patient anlegen" }).click();
    await page
      .getByRole("dialog", { name: "Patient angelegt" })
      .getByRole("button", { name: "Akte öffnen" })
      .click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    patientPath = new URL(page.url()).pathname;
  });
});

test("the assistant stores the PDF and has its values proposed", async ({
  browser,
}) => {
  await asStaff(browser, "assistant", async (page) => {
    await page.goto(patientPath);
    await openTab(page, "Akte");
    const lab = page.getByRole("region", { name: "Labordaten" });
    const chooser = lab.getByLabel("Labordatei wählen");
    await hydrated(chooser);
    await chooser.setInputFiles(pdf);
    await lab.getByRole("button", { name: "Hochladen und einlesen" }).click();
    // A PDF has no structured reader: the file is stored, nothing is imported, and the row
    // offers the proposal instead.
    await expect(lab.getByRole("alert")).toContainText(
      "Die Originaldatei ist gespeichert",
    );
    const row = lab
      .getByRole("table", { name: "Gespeicherte Labordateien" })
      .getByRole("row")
      .filter({ hasText: pdf.name });
    const propose = row.getByRole("button", {
      name: "Werte vorschlagen lassen",
    });
    await hydrated(propose);
    await propose.click();
    await expect(lab.getByRole("status")).toContainText(
      "Vorschlag erstellt: 6 Werte, davon 0 grün, 6 gelb, 0 rot.",
    );
    await followLink(
      page,
      lab.getByRole("status").getByRole("link", { name: "Vorschlag öffnen" }),
      /\/intake\/[0-9a-f-]{36}$/,
    );
    proposalPath = new URL(page.url()).pathname;

    // Every value beside its region; the assistant may look but not decide.
    await expect(
      page.getByRole("heading", { name: "Vorschlag aus Datei" }),
    ).toBeVisible();
    await expect(
      page.getByText(
        "Bestätigen, Korrigieren und Ablehnen ist Ärztinnen und Ärzten vorbehalten (Nur-Lese-Ansicht).",
      ),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Bestätigen" })).toHaveCount(
      0,
    );
    const ldl = page.getByRole("article", { name: /^LDL 3,1 mmol\/L$/ });
    await expect(ldl).toContainText("Gelb");
    await expect(ldl).toContainText("Geringe Lesesicherheit");
    await expect(ldl).toContainText("Kennzahl: cardio.ldl_c");
    const region = ldl.getByRole("img", {
      name: /Ausschnitt von Seite 1 um den Wert 3,1 mmol\/L/,
    });
    await expect(region).toBeVisible();
    await expect
      .poll(() =>
        region.evaluate((img) => (img as HTMLImageElement).naturalWidth),
      )
      .toBeGreaterThan(50);
  });
});

test("the clinician looks, confirms one value, rejects another — only the confirmed one enters the record", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto(proposalPath);
    const ldl = page.getByRole("article", { name: /^LDL 3,1 mmol\/L$/ });
    const confirm = ldl.getByRole("button", { name: "Bestätigen" });
    await hydrated(confirm);
    // Yellow: the confirmation waits for the look.
    await expect(confirm).toBeDisabled();
    await ldl.getByRole("checkbox", { name: "Ausschnitt angesehen" }).check();
    await expect(confirm).toBeEnabled();
    await confirm.click();
    await expect(ldl).toContainText("Bestätigt");
    await expect(ldl).toContainText("In der Akte");

    const hba1c = page.getByRole("article", { name: /^HbA1c 5,4 %$/ });
    await hba1c.getByRole("button", { name: "Ablehnen" }).click();
    await hba1c
      .getByRole("combobox", { name: "Grund der Ablehnung" })
      .selectOption({ label: "Falsch gelesen" });
    await hba1c.getByRole("button", { name: "Ablehnung speichern" }).click();
    await expect(hba1c).toContainText("Abgelehnt: Falsch gelesen");
    await expect(hba1c).not.toContainText("In der Akte");
    // "Alle grünen bestätigen" has nothing to do: the reader proposed no green value.
    await expect(
      page.getByRole("button", { name: "Keine offenen grünen Werte" }),
    ).toBeDisabled();
    await expect(page.getByText(/4 offen/)).toBeVisible();

    // The record holds the confirmed value and not the rejected one.
    await followLink(
      page,
      page.getByRole("link", { name: "Zur Akte" }),
      patientPath,
    );
    await openTab(page, "Werte");
    // The timeline shows the number the platform holds (3.1 mmol/L, the canonical unit)
    // under the value's catalog domain; the rejected HbA1c has no marker.
    const marker = page
      .getByRole("region", { name: "Kardiovaskulär" })
      .getByRole("button", { name: "Marker LDL öffnen" });
    await expect(marker).toContainText("3.1 mmol/L");
    await expect(
      page.getByRole("button", { name: /^Marker HbA1c/ }),
    ).toHaveCount(0);
  });
});
