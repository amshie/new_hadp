import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import {
  asStaff,
  followLink,
  hydrated,
  openTab,
  watchPageErrors,
  withoutPageScripts,
} from "./support/staff";

// The primary clinic workflow, walked through the UI alone on synthetic data: a new patient
// with consent, a laboratory file of which one value is published by the import and two
// wait for a clinician, the interpretation run, the report draft, the clinical approval, the
// medical director's release — and what the patient then reads through the access link.
//
// The steps build on each other and run in order; the first one that fails ends the run.
// Every run creates its own patient (a random token in the name), so it can be repeated on
// a database that holds earlier runs. Nothing is cleaned up: the records are synthetic and
// the platform keeps what was recorded.
test.describe.configure({ mode: "serial" });

const run = randomUUID().slice(0, 8);
const patient = { name: `Synthetic E2E ${run}`, ref: `E2E-${run}` };

// The laboratory file. The API stores a file once per clinic (by checksum) and refuses it
// for a second patient, so each run marks its copy in the "Auftrag" column — a column the
// reader does not know and ignores.
const labFile = {
  name: `synthetic-e2e-${run}.csv`,
  mimeType: "text/csv",
  buffer: Buffer.from(
    readFileSync(
      join(__dirname, "fixtures", "lab-report.synthetic.csv"),
      "utf8",
    ).replaceAll("SYNTHETIC-E2E", `SYNTHETIC-E2E-${run}`),
    "utf8",
  ),
};

// The three values of the file, as the source wrote them. "LDL Cholesterol" is one of the six
// names the import acts on by itself; every other name waits for a clinician. Of the two that
// wait, the KPI catalog knows "Creatinine" and does not know "Zink".
const SAMPLED_ON = "10.06.2025";
const PUBLISHED_BY_IMPORT = { name: "LDL Cholesterol", written: "3,4 mmol/L" };
const HELD_FOR_REVIEW = [
  { name: "Zink", written: "65 µg/dL" },
  { name: "Creatinine", written: "88 µmol/L" },
];

// The headline the review page shows above a report version, by lifecycle status — the
// strings scripts/smoke_web.py holds as STAGE_HEADLINE.
const STAGE_HEADLINE = {
  draft_generated: "Systementwurf – nicht freigegeben.",
  draft_edited: "Überarbeiteter Entwurf – nicht freigegeben.",
  approved: "Klinisch genehmigt – noch nicht freigegeben.",
  released: "Ärztlich freigegeben.",
  rejected: "Zurückgewiesen – nicht freigegeben.",
} as const;

const DOMAIN_AXES = [
  "Metabolisch",
  "Immun / Entzündung",
  "Kardiovaskulär",
  "Neurokognitiv",
  "Muskuloskelettal",
  "Regenerationskapazität",
];
const TRI_STATE_AXES = ["Biologisch", "Risk", "Funktional"];

// What the steps hand on to the ones after them.
let patientPath = "";
let reviewPath = "";
let statements: string[] = [];
let accessLink = "";

// The review page says where the version stands — and nothing that belongs to another status.
async function expectStage(
  page: Page,
  status: keyof typeof STAGE_HEADLINE,
): Promise<void> {
  const banner = (headline: string) =>
    page.getByRole("status").filter({ hasText: headline });
  await expect(banner(STAGE_HEADLINE[status])).toBeVisible();
  for (const [other, headline] of Object.entries(STAGE_HEADLINE)) {
    if (other !== status) await expect(banner(headline)).toHaveCount(0);
  }
}

// A figure of the patient page's "Datenlage" card, found by the caption under it.
const figure = (page: Page, caption: string): Locator =>
  page
    .getByText(caption, { exact: true })
    .locator("xpath=preceding-sibling::div");

// This patient's open task for one analyte in the review queue.
const queueRow = (page: Page, analyte: string): Locator =>
  page
    .getByRole("table", { name: "Offene Prüfaufgaben" })
    .getByRole("row")
    .filter({ hasText: patient.name })
    .filter({ has: page.getByText(analyte, { exact: true }) });

// The row of one marker in a domain list of the patient page. A marker the catalog links to
// several domains is listed in each; it is looked for in the one named.
const markerRow = (page: Page, domain: string, analyte: string): Locator =>
  page
    .getByRole("region", { name: domain, exact: true })
    .getByRole("button", { name: `Marker ${analyte} öffnen` });

// A select of the interpretation form, by the name its label gives it. (The labels were not
// connected to their controls when this suite was written; the selects are found by name
// since they are — a field that loses its name again fails here.)
const choose = (scope: Locator, label: string, option: string) =>
  scope
    .getByRole("combobox", { name: label, exact: true })
    .selectOption({ label: option });

test("the assistant creates the patient and records the consent to release", async ({
  browser,
}) => {
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
    // The dialog moves focus to its first field a moment after it opens. Typing into another
    // field before that has happened lands in this one (seen once in CI: the patient was
    // created under its name with the reference appended) — so wait for the focus first.
    await expect(name).toBeFocused();
    await name.fill(patient.name);
    await wizard.getByRole("textbox", { name: "Externe ID" }).fill(patient.ref);
    await wizard.getByRole("button", { name: "Weiter" }).click();

    // Nothing is preselected: the consent is recorded by an explicit choice.
    const releaseConsent = wizard.getByRole("checkbox", {
      name: /^Freigabe geprüfter Berichte/,
    });
    await expect(releaseConsent).not.toBeChecked();
    await releaseConsent.check();
    await wizard.getByRole("button", { name: "Weiter" }).click();

    await expect(
      wizard.getByText("Keine Übereinstimmungen in dieser Praxis gefunden."),
    ).toBeVisible();
    await wizard.getByRole("button", { name: "Patient anlegen" }).click();

    const created = page.getByRole("dialog", { name: "Patient angelegt" });
    await expect(created).toContainText(
      `${patient.name} · synthetischer Demodatensatz · 1 Einwilligung dokumentiert.`,
    );
    await created.getByRole("button", { name: "Akte öffnen" }).click();

    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    patientPath = new URL(page.url()).pathname;

    await expect(
      page.getByRole("heading", { level: 1, name: patient.name }),
    ).toBeVisible();
    // The shell says what kind of data this is.
    await expect(
      page.getByRole("complementary", { name: "Hauptnavigation" }),
    ).toContainText(
      "Synthetische Beispieldaten · keine reale Patientenversorgung.",
    );
    // The consent the release gate asks for is on record; the other purposes are not.
    await openTab(page, "Akte");
    const consents = page
      .getByRole("region", { name: "Einwilligungen" })
      .getByRole("listitem");
    await expect(
      consents.filter({ hasText: "Freigabe geprüfter Berichte" }),
    ).toContainText(
      /Aktiv — Erteilt am \d{2}\.\d{2}\.\d{4} \(vor Ort erklärt\)/,
    );
    await expect(
      consents.filter({ hasText: "Nicht aktiv — Nicht dokumentiert" }),
    ).toHaveCount(2);
    // No value and no report yet.
    await expect(figure(page, "Beobachtungen")).toHaveText("0");
    await expect(page.getByText("Kein Bericht", { exact: true })).toBeVisible();
  });
});

test("a form handled in script takes no submission before the page is hydrated", async ({
  browser,
}) => {
  // Submitted before React has taken the page over, such a form would go to the server
  // natively: a GET to the same address — a reload that drops what was entered and writes it
  // into the URL. The submit button is disabled in the server's markup; that also stops the
  // Enter key. Both forms are tried on pages whose scripts are kept from loading.
  const context = await browser.newContext();
  try {
    await withoutPageScripts(context);
    const page = await context.newPage();
    await page.goto("/login");
    const address = page.getByRole("textbox", { name: "E-Mail-Adresse" });
    await address.fill("assistant@demo.synthetic");
    await expect(page.getByRole("button", { name: "Anmelden" })).toBeDisabled();
    await address.press("Enter");
    // Nothing was sent: the address is still in the field and not in the URL.
    await expect(address).toHaveValue("assistant@demo.synthetic");
    expect(new URL(page.url()).search).toBe("");
    expect(new URL(page.url()).pathname).toBe("/login");
  } finally {
    await context.close();
  }

  await asStaff(
    browser,
    "assistant",
    async (page) => {
      await page.goto(patientPath);
      const lab = page.getByRole("region", { name: "Labordaten" });
      await lab.getByLabel("Labordatei wählen").setInputFiles(labFile);
      await expect(
        lab.getByRole("button", { name: "Hochladen und einlesen" }),
      ).toBeDisabled();
      expect(new URL(page.url()).search).toBe("");
      await expect(
        lab.getByText("Für diese Akte ist noch keine Labordatei gespeichert."),
      ).toBeVisible();
    },
    { unhydrated: true },
  );
});

test("the assistant imports a laboratory file: one value is published, two wait for review", async ({
  browser,
}) => {
  await asStaff(browser, "assistant", async (page) => {
    await page.goto(patientPath);
    await openTab(page, "Akte");

    const lab = page.getByRole("region", { name: "Labordaten" });
    const chooser = lab.getByLabel("Labordatei wählen");
    // Before hydration this form submits natively: the page reloads and no file is sent.
    await hydrated(chooser);
    await chooser.setInputFiles(labFile);
    await lab.getByRole("button", { name: "Hochladen und einlesen" }).click();

    const counts =
      "1 veröffentlicht · 2 zur Prüfung · 0 bereits vorhanden · 0 nicht übernommen";
    await expect(lab.getByRole("status")).toContainText(
      `Eingelesen (hadp-csv v1): ${counts}.`,
    );
    await expect(
      lab
        .getByRole("table", { name: "Gespeicherte Labordateien" })
        .getByRole("row")
        .filter({ hasText: labFile.name }),
    ).toContainText(counts);
    await expect(figure(page, "veröffentlicht")).toHaveText("1/3");

    // A value that waits says so, and no position against its reference interval is stated
    // for it (88 lies within 59–104). The catalog places creatinine in
    // "Regenerationskapazität"; it is also listed, and not counted, under "Metabolisch".
    await openTab(page, "Werte");
    const creatinine = markerRow(page, "Regenerationskapazität", "Creatinine");
    await expect(creatinine).toContainText("in Prüfung – nicht veröffentlicht");
    await expect(creatinine).toContainText("1 Wert in Prüfung");
    await expect(markerRow(page, "Metabolisch", "Creatinine")).toContainText(
      "Regenerationskapazität",
    );
    // A name the catalog does not know belongs to no domain: it waits in its own list.
    const unassigned = page.getByRole("region", {
      name: "Keinem Katalogmarker zugeordnet",
    });
    await expect(unassigned).toContainText("Zink");
    await expect(unassigned).toContainText("65 µg/dL");
    await expect(creatinine).toContainText("88 µmol/L");
    await expect(creatinine).not.toContainText("Im Intervall");

    // Both held values are in the review queue. The assistant sees them and is told that the
    // decision is not hers: the queue offers her no control.
    await openTab(page, "Akte");
    await followLink(
      page,
      lab.getByRole("link", { name: "Zur Review-Queue" }),
      "**/review-queue",
    );
    await expect(
      page.getByText(
        "Die Entscheidung ist der klinischen Rolle vorbehalten (Nur-Lese-Ansicht).",
      ),
    ).toBeVisible();
    for (const held of HELD_FOR_REVIEW) {
      const row = queueRow(page, held.name);
      await expect(row).toContainText(held.written);
      await expect(row).toContainText("Kennzahl nicht zugeordnet");
      await expect(row).toContainText("Klinische Rolle erforderlich");
      await expect(row.getByRole("button")).toHaveCount(0);
    }
    // The value the import published by itself is not a task.
    await expect(queueRow(page, PUBLISHED_BY_IMPORT.name)).toHaveCount(0);
  });
});

test("the clinician publishes the held values", async ({ browser }) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/review-queue");

    for (const held of HELD_FOR_REVIEW) {
      const row = queueRow(page, held.name);
      const publish = row.getByRole("button", { name: "Veröffentlichen" });
      await hydrated(publish);
      await publish.click();

      const confirm = page.getByRole("dialog", {
        name: "Wert veröffentlichen?",
      });
      await expect(confirm).toContainText(`${held.name}: ${held.written}`);
      await confirm.getByRole("button", { name: "Veröffentlichen" }).click();

      await expect(confirm).toBeHidden();
      await expect(row).toHaveCount(0);
    }

    // On the patient page the value no longer waits, and its position is now stated.
    await page.goto(patientPath);
    await expect(figure(page, "veröffentlicht")).toHaveText("3/3");
    await openTab(page, "Werte");
    const creatinine = markerRow(page, "Regenerationskapazität", "Creatinine");
    await expect(creatinine).toContainText("Im Intervall");
    await expect(creatinine).not.toContainText("in Prüfung");
  });
});

test("the clinician authors the interpretation run", async ({ browser }) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto(patientPath);
    const author = page.getByRole("button", {
      name: "Interpretation erfassen",
    });
    await hydrated(author);
    await author.click();
    await page.waitForURL(`**${patientPath}/interpretation/neu`);

    // What the form requires: a reason, and for each of the six axes CIS, Actionability and
    // follow-up adequacy plus a state and an endpoint adequacy for each of the three cells.
    // One cell is given a state that needs evidence, and cites a published value.
    await page
      .getByRole("textbox", { name: "Grund (Pflicht)" })
      .fill("Synthetische Baseline (E2E)");
    for (const axis of DOMAIN_AXES) {
      const domain = page.getByRole("region", { name: axis, exact: true });
      // Nine selects per axis — three for the axis, two in each of the three cells — and
      // every one of them is chosen by its name below; plus the optional rationale.
      await expect(domain.getByRole("combobox")).toHaveCount(9);
      await expect(
        domain.getByRole("textbox", { name: "Begründung (optional)" }),
      ).toHaveCount(1);
      await choose(domain, "CIS", "CIS-0 · Unzureichende Evidenz");
      await choose(domain, "Actionability", "A · Erkundung");
      await choose(domain, "Follow-up-Adäquanz", "nicht bewertet");
      for (const triState of TRI_STATE_AXES) {
        const cell = domain.getByRole("group", {
          name: `${triState} (bewertungsfrei)`,
          exact: true,
        });
        const cites = axis === "Kardiovaskulär" && triState === "Risk";
        await choose(cell, "Zustand", cites ? "Ungeklärt" : "Unbestimmt");
        await choose(cell, "Endpunkt-Adäquanz", "nicht bewertet");
        if (!cites) continue;

        await cell.getByText("Belege (0 gewählt) — Pflicht").click();
        // The values on offer as evidence are the published ones — the two the clinician
        // has just published among them.
        for (const value of [PUBLISHED_BY_IMPORT, ...HELD_FOR_REVIEW]) {
          await expect(
            cell.getByRole("checkbox", { name: `${value.name} · 2025-06-10` }),
          ).toBeVisible();
        }
        await expect(cell.getByRole("checkbox")).toHaveCount(3);
        await cell
          .getByRole("checkbox", {
            name: `${PUBLISHED_BY_IMPORT.name} · 2025-06-10`,
          })
          .check();
        await expect(cell.getByText("Belege (1 gewählt)")).toBeVisible();
      }
    }
    await page.getByRole("button", { name: "Interpretation erfassen" }).click();

    // Back on the patient page every axis carries the run, and the cited value is listed
    // under its domain.
    await page.waitForURL(`**${patientPath}`);
    await openTab(page, "Werte");
    for (const axis of DOMAIN_AXES) {
      const card = page.locator(".vb-domaincard").filter({
        has: page.getByRole("link", { name: `${axis}: zur Markerliste` }),
      });
      await expect(card).toContainText("Follow-up-Adäquanz: nicht bewertet");
      await expect(card).toContainText(
        /Lauf 1 · erfasst am \d{2}\.\d{2}\.\d{4}/,
      );
    }
    await expect(
      page.getByRole("region", { name: "Vor dem Termin" }),
    ).toContainText(/Letzte Interpretation: Lauf 1 · \d{2}\.\d{2}\.\d{4}/);
    await expect(
      markerRow(page, "Kardiovaskulär", PUBLISHED_BY_IMPORT.name),
    ).toContainText("Über Referenz");
  });
});

test("the clinician drafts the report and approves it", async ({ browser }) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto(patientPath);
    const draftIt = page.getByRole("button", {
      name: "Berichtsentwurf erstellen",
    });
    await hydrated(draftIt);
    await draftIt.click();
    await page.waitForURL(
      new RegExp(`${patientPath}/assessments/[0-9a-f-]{36}$`),
    );
    reviewPath = new URL(page.url()).pathname;

    await expectStage(page, "draft_generated");
    // One statement per published value, each giving the result as the source wrote it.
    const draft = page
      .getByRole("region", { name: "Quellengebundener Entwurf" })
      .getByRole("paragraph");
    await expect(draft).toHaveCount(3);
    statements = await draft.allInnerTexts();
    for (const value of [PUBLISHED_BY_IMPORT, ...HELD_FOR_REVIEW]) {
      const quoted = `${value.name} am ${SAMPLED_ON}: ${value.written}.`;
      expect(
        statements.filter((text) => text.startsWith(quoted)),
        `one statement quotes "${quoted}"`,
      ).toHaveLength(1);
    }

    await page.getByRole("button", { name: "Bericht genehmigen" }).click();
    const confirm = page.getByRole("dialog", { name: "Bericht genehmigen?" });
    const approve = confirm.getByRole("button", {
      name: "Genehmigen",
      exact: true,
    });
    // The approval is not a single click: it is offered once the review is confirmed.
    await expect(approve).toBeDisabled();
    await confirm
      .getByRole("checkbox", { name: /^Ich habe die offenen Hinweise geprüft/ })
      .check();
    await approve.click();
    await expect(confirm).toBeHidden();

    await expectStage(page, "approved");
    await expect(
      page
        .getByRole("region", { name: "Quellengebundener Bericht" })
        .getByRole("paragraph"),
    ).toHaveText(statements);
    // The release is the medical director's step: the clinician is offered none.
    await expect(
      page.getByText("Genehmigt — wartet auf die ärztliche Freigabe."),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "An Patientin freigeben" }),
    ).toHaveCount(0);
  });
});

test("without an access link the patient page shows the neutral message and no report", async ({
  browser,
}) => {
  // What this shows, and no more: a browser that holds no link is told that the link is not
  // valid and sees nothing of the report the clinician has just approved. It would say the
  // same at any other moment — the access link is issued by the release and shown once, so
  // before the release there is no link to try, and the UI gives no way to ask for this
  // report as a patient. (A link that is NOT the issued one is tried after the release,
  // below; that a link shows released content only is the API's rule and is tested there.)
  const context = await browser.newContext();
  const noPageErrors = watchPageErrors(context);
  try {
    const page = await context.newPage();
    await page.goto("/patient-view");

    await expect(
      page.getByText("Dieser Link ist nicht oder nicht mehr gültig."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Ihr Bericht" }),
    ).toHaveCount(0);
    expect(statements.length, "the approved statements").toBe(3);
    for (const statement of statements) {
      await expect(page.getByText(statement)).toHaveCount(0);
    }
    await expect(
      page.getByRole("complementary", { name: "Wichtige Hinweise" }),
    ).toContainText(
      "Pilotumgebung. Synthetische Beispieldaten · keine reale Patientenversorgung.",
    );
    noPageErrors();
  } finally {
    await context.close();
  }
});

test("the medical director releases the report", async ({ browser }) => {
  await asStaff(browser, "medicalDirector", async (page) => {
    // She finds the patient in the directory and opens the report from the patient page.
    await page.goto("/patients");
    const search = page.getByRole("textbox", {
      name: "Patient oder ID suchen",
    });
    await hydrated(search);
    await search.fill(patient.ref);
    await page
      .getByRole("button", {
        name: `Patient ${patient.name}, ${patient.ref} öffnen`,
      })
      .click();
    await page.waitForURL(`**${patientPath}`);
    await followLink(
      page,
      page.getByRole("link", { name: "Bericht öffnen" }),
      `**${reviewPath}`,
    );

    // She releases what the clinician approved.
    await expectStage(page, "approved");
    await expect(
      page
        .getByRole("region", { name: "Quellengebundener Bericht" })
        .getByRole("paragraph"),
    ).toHaveText(statements);

    await page.getByRole("button", { name: "An Patientin freigeben" }).click();
    await page
      .getByRole("dialog", { name: "An Patientin freigeben?" })
      .getByRole("button", { name: "Freigeben", exact: true })
      .click();

    // The access link is shown once, for the clinic to hand to the patient.
    const released = page.getByRole("dialog", {
      name: "Freigegeben — Zugriffslink",
    });
    accessLink = await released
      .getByRole("textbox", { name: "Zugriffslink (einmalig angezeigt)" })
      .inputValue();
    const link = new URL(accessLink);
    expect(link.pathname).toBe("/patient-view/oeffnen");
    expect(link.searchParams.get("tenant")).toMatch(/^[0-9a-f-]{36}$/);
    expect(link.searchParams.get("token")).toBeTruthy();

    // Copying it says so. The page answers its actions in a toast — its errors too — and lost
    // every one silently once, when it left the shell that provided the toasts.
    await page
      .context()
      .grantPermissions(["clipboard-read", "clipboard-write"]);
    await released.getByRole("button", { name: "Link kopieren" }).click();
    await expect(page.getByText("Link kopiert.")).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
      accessLink,
    );

    await released
      .getByRole("button", { name: "Schließen", exact: true })
      .click();

    await expectStage(page, "released");
    await expect(
      page.getByRole("button", { name: "An Patientin freigeben" }),
    ).toHaveCount(0);
  });
});

test("the patient reads the released report through the access link", async ({
  browser,
}) => {
  // A browser of the patient's own: a new context, no staff session.
  const context = await browser.newContext();
  const noPageErrors = watchPageErrors(context);
  try {
    const page = await context.newPage();
    await page.goto(accessLink);

    // The link is exchanged for a cookie: the token does not stay in the address.
    await expect(page).toHaveURL(/\/patient-view$/);
    const report = page.getByRole("main");
    await expect(
      report.getByRole("heading", { level: 1, name: "Ihr Bericht" }),
    ).toBeVisible();
    // Everything the page says: the release line with the synthetic label, the introduction,
    // the released statements — exactly those the clinician approved — the practice that
    // released them, and the four-part disclaimer.
    await expect(report.getByRole("paragraph")).toHaveText([
      /^Ärztlich freigegeben am \d{2}\.\d{2}\.\d{4} · synthetische Demo-Inhalte$/,
      /^Diese Zusammenfassung gibt Ihre Messwerte wieder/,
      ...statements,
      /^Freigegeben von Synthetic Longevity Clinic/,
      "Pilotumgebung. Synthetische Beispieldaten · keine reale Patientenversorgung.",
      "Die Inhalte sind keine automatische Diagnose oder Therapieempfehlung.",
      /Sie sehen ausschließlich freigegebene Versionen\.$/,
      /^Dieses Angebot ist nicht für Notfälle bestimmt\./,
    ]);
    // The disclaimer is announced as such.
    await expect(
      page
        .getByRole("complementary", { name: "Wichtige Hinweise" })
        .getByRole("paragraph"),
    ).toHaveCount(4);
    // The values the statements cite, as the source wrote them: one row per cited
    // measurement, with the source's reference text and the day of sampling.
    const values = report.getByRole("table");
    await expect(values.getByRole("columnheader")).toHaveText([
      "Wert",
      "Ergebnis",
      "Referenz der Quelle",
      "Gemessen",
    ]);
    expect(await values.getByRole("row").count()).toBeGreaterThan(1);
    await expect(values.getByRole("cell").first()).toHaveText(
      /^\d+([.,]\d+)? \S+/,
    );

    // The link opens the report and nothing else: the clinic's pages stay closed.
    await page.goto(patientPath);
    await expect(page).toHaveURL(/\/login$/);
    noPageErrors();
  } finally {
    await context.close();
  }
});

test("a link that is not the issued one opens no report", async ({
  browser,
}) => {
  // The issued link with one character of its token changed, in a browser of its own.
  const link = new URL(accessLink);
  const token = link.searchParams.get("token") ?? "";
  const last = token.slice(-1) === "A" ? "B" : "A";
  link.searchParams.set("token", token.slice(0, -1) + last);
  expect(link.toString()).not.toBe(accessLink);

  const context = await browser.newContext();
  const noPageErrors = watchPageErrors(context);
  try {
    const page = await context.newPage();
    await page.goto(link.toString());

    await expect(page).toHaveURL(/\/patient-view$/);
    await expect(
      page.getByText("Dieser Bericht ist nicht verfügbar."),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Ihr Bericht" }),
    ).toHaveCount(0);
    for (const statement of statements) {
      await expect(page.getByText(statement)).toHaveCount(0);
    }
    noPageErrors();
  } finally {
    await context.close();
  }
});
