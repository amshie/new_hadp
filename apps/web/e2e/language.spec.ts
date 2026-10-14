import { expect, test, type Locator, type Page } from "@playwright/test";

import { asStaff, hydrated, watchPageErrors } from "./support/staff";

// The interface language is a person's choice — under Einstellungen, or on the sign-in page —
// kept on the device (apps/web/src/lib/i18n). German is what a device without a choice gets.
//
// These tests hold what is translated: the navigation shell, the settings overview and its
// four pages, the overview, the patients list, the dialog to add a patient (opened from the
// overview), the patient page, the review queue, the interpretation form, the report page, the
// sign-in page and the not-found page — and that a page which is still German (one a patient
// or an invited colleague opens) says so. They leave every other test in German: each runs in
// a browser context of its own, and none of them signs out (the session is shared).

// The medical director: the one seeded role whose name differs between the two languages.
const ROLE = { de: "Ärztliche Leitung", en: "Medical director" };

// The four tabs of the patients list, and the six of the overview's work list — five places
// a report can stand in, and all.
const PATIENT_TABS = {
  de: {
    all: "Alle",
    open: "Offene Reviews",
    released: "Freigegeben",
    none: "Ohne Bericht",
  },
  en: {
    all: "All",
    open: "Open reviews",
    released: "Released",
    none: "No report",
  },
};
const WORK_TABS = {
  de: {
    all: "Alle",
    open: "Offene Reviews",
    approved: "Zur Freigabe",
    released: "Freigegeben",
    rejected: "Zurückgewiesen",
    none: "Kein Entwurf",
  },
  en: {
    all: "All",
    open: "Open reviews",
    approved: "To release",
    released: "Released",
    rejected: "Rejected",
    none: "No draft",
  },
};

// A tab of the patients list: its name, then what it counts.
const tab = (page: Page, name: string) =>
  page.getByRole("button", { name: new RegExp(`^${name} \\d+$`) });

async function workCounts(page: Page, names: typeof WORK_TABS.de) {
  const out: Record<string, number> = {};
  for (const [key, name] of Object.entries(names))
    out[key] = Number((await tab(page, name).innerText()).match(/\d+$/)?.[0]);
  return out;
}

async function tabCounts(page: Page, names: typeof PATIENT_TABS.de) {
  const count = async (name: string) =>
    Number((await tab(page, name).innerText()).match(/\d+$/)?.[0]);
  return {
    all: await count(names.all),
    open: await count(names.open),
    released: await count(names.released),
    none: await count(names.none),
  };
}

async function expectEnglishSettings(page: Page): Promise<void> {
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  const navigation = page.getByRole("complementary", {
    name: "Main navigation",
  });
  for (const entry of ["Overview", "Patients", "Review queue", "Settings"]) {
    await expect(navigation.getByRole("link", { name: entry })).toBeVisible();
  }
  await expect(
    page.getByRole("heading", { level: 1, name: "Settings" }),
  ).toBeVisible();
  // A section this role may open, by its English name.
  await expect(
    page
      .getByRole("navigation", { name: "Settings sections" })
      .getByRole("link", { name: "Deletion requests" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "English" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.getByRole("button", { name: "Deutsch" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByRole("banner")).toContainText(ROLE.en);
  await expect(page.getByRole("banner")).not.toContainText(ROLE.de);
}

test("a person chooses English under Einstellungen, and goes back to German", async ({
  browser,
}) => {
  await asStaff(browser, "medicalDirector", async (page) => {
    await page.goto("/einstellungen");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(page.getByRole("banner")).toContainText(ROLE.de);

    // The choice is one of two submit buttons of a form with a server action.
    const english = page.getByRole("button", { name: "English" });
    await hydrated(english);
    await english.click();
    await expectEnglishSettings(page);

    // The choice is a cookie of this device: not readable by scripts, for about a year.
    const cookie = (await page.context().cookies()).find(
      (c) => c.name === "hadp_locale",
    );
    expect(cookie).toMatchObject({
      value: "en",
      httpOnly: true,
      sameSite: "Lax",
      path: "/",
    });
    const days = ((cookie?.expires ?? 0) - Date.now() / 1000) / 86_400;
    expect(days).toBeGreaterThan(360);
    expect(days).toBeLessThan(370);

    // It holds on the next pages, reached by links of the shell (no full page load).
    const navigation = page.getByRole("complementary", {
      name: "Main navigation",
    });
    const languageOf = (heading: Locator) =>
      heading.evaluate((element) =>
        element.closest("[lang]")?.getAttribute("lang"),
      );

    // The overview is English: its headings, its tiers, its work list.
    await navigation.getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
    const overview = page.getByRole("heading", { level: 1, name: "Overview" });
    await expect(overview).toBeVisible();
    expect(await languageOf(overview)).toBe("en");
    const body = page.locator("body");
    for (const heading of ["Today", "Work list", "Data coverage"]) {
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }
    for (const tier of ["Now", "Next", "For information"]) {
      await expect(
        page.getByRole("heading", { level: 3, name: new RegExp(`^${tier}`) }),
      ).toBeVisible();
    }
    await expect(body).not.toContainText("Arbeitsliste");
    await expect(body).not.toContainText("Zur Kenntnis");
    // The dialog to add a patient follows the choice: the message of a check it makes itself,
    // its three steps, and what the duplicate check answers from the server.
    await page.getByRole("button", { name: "Add patient" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText(
      "Synthetic demo data · no real patient.",
    );
    const name = dialog.getByRole("textbox", { name: "Name", exact: true });
    // The dialog moves focus to its first field a moment after it opens.
    await expect(name).toBeFocused();
    await dialog.getByRole("button", { name: "Next" }).click();
    await expect(dialog.getByRole("alert")).toHaveText("Please enter a name.");
    await name.fill("Synthetic Language Check");
    // The reference of the seeded patient: the duplicate check will find it.
    await dialog.getByRole("textbox", { name: "External ID" }).fill("SYN-0001");
    await dialog.getByRole("button", { name: "Next" }).click();
    const step = dialog.getByRole("heading", { level: 3 });
    await expect(step).toContainText("Consents");
    expect(await languageOf(step)).toBe("en");
    // The purposes of consent are no interface wording: they are shown as they are recorded,
    // and say that they are German — where they are chosen, and where they are summed up.
    const purpose = dialog.getByRole("checkbox", {
      name: /^Freigabe geprüfter Berichte/,
    });
    expect(await languageOf(purpose)).toBe("de");
    await purpose.check();
    await dialog.getByRole("button", { name: "Next" }).click();
    await expect(step).toHaveText("Review & confirm");
    const chosen = dialog.getByText("Freigabe geprüfter Berichte", {
      exact: true,
    });
    expect(await languageOf(chosen)).toBe("de");
    // A record with the same reference exists: the dialog says so, and does not create a
    // second one without an explicit decision.
    await expect(dialog.getByRole("alert")).toContainText(
      "Possibly on record already",
    );
    await expect(dialog.getByRole("alert")).toContainText("Same external ID");
    await expect(
      dialog.getByRole("button", { name: "Create patient" }),
    ).toBeDisabled();
    // No patient is created: what was entered is discarded. (The duplicate check leaves one
    // entry in the audit trail — a count, no name.)
    await dialog.getByRole("button", { name: "Back" }).click();
    await dialog.getByRole("button", { name: "Back" }).click();
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).toContainText("Discard what you entered?");
    await dialog.getByRole("button", { name: "Discard" }).click();
    await expect(dialog).toHaveCount(0);

    // So is the patients list.
    await navigation.getByRole("link", { name: "Patients" }).click();
    await expect(page).toHaveURL(/\/patients$/);
    const patients = page.getByRole("heading", { level: 1, name: "Patients" });
    await expect(patients).toBeVisible();
    expect(await languageOf(patients)).toBe("en");
    await expect(body).toContainText("Patient directory");
    await expect(body).toContainText("Last assessment");
    await expect(body).not.toContainText("Patientenverzeichnis");

    // The review queue is English, around the reasons of its tasks: a closed vocabulary,
    // German until its English names are confirmed (ADR-0007), and marked so.
    await navigation.getByRole("link", { name: "Review queue" }).click();
    await expect(page).toHaveURL(/\/review-queue$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const queue = page.getByRole("heading", { level: 1, name: "Review queue" });
    await expect(queue).toBeVisible();
    expect(await languageOf(queue)).toBe("en");
    await expect(body).toContainText(
      "Open review tasks from the import — no value is published without a human decision.",
    );
    await expect(body).not.toContainText("Offene Prüfaufgaben");
    const tasks = page.getByRole("table", { name: "Open review tasks" });
    if (await tasks.count()) {
      await expect(tasks.getByRole("columnheader")).toHaveText([
        "Patient",
        "Value (source)",
        "Reason",
        "Observed",
        "Decision",
      ]);
      for (const reason of await tasks.locator("tbody td:nth-child(3)").all()) {
        expect(await languageOf(reason)).toBe("de");
      }
    } else {
      await expect(body).toContainText("No open review tasks.");
    }

    // A value that is no offered language changes nothing.
    await page.goto("/einstellungen");
    const german = page.getByRole("button", { name: "Deutsch" });
    await hydrated(german);
    await german.evaluate((button: HTMLButtonElement) => {
      button.value = "fr";
    });
    await german.click();
    await expectEnglishSettings(page);

    // And back.
    const back = page.getByRole("button", { name: "Deutsch" });
    await hydrated(back);
    await back.click();
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(
      page.getByRole("heading", { level: 1, name: "Einstellungen" }),
    ).toBeVisible();
    await expect(page.getByRole("banner")).toContainText(ROLE.de);
    await expect(page.getByRole("button", { name: "Abmelden" })).toBeVisible();
  });
});

test("the overview and the patients list show the same in both languages", async ({
  browser,
  baseURL,
}) => {
  await asStaff(browser, "medicalDirector", async (page) => {
    const body = page.locator("body");
    const rows = page.locator(".vb-row");

    // German, as a device without a choice gets it — the sentences as they were.
    await page.goto("/patients");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    const counts = await tabCounts(page, PATIENT_TABS.de);
    const { all, released, none } = counts;
    expect(all, "the seeded clinic has patients").toBeGreaterThan(0);
    await expect(rows).toHaveCount(all);
    await expect(body).toContainText(`Zeige ${all} von ${all}`);
    // The overview's work list counts the same records: all, released, without a report.
    await page.goto("/overview");
    const work = await workCounts(page, WORK_TABS.de);
    expect(work).toMatchObject({ all, released, none, open: counts.open });

    // The same device chooses English (by the cookie the two buttons set; choosing by a
    // button is the test above).
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);

    // The overview's work list names the five places a report can stand in, in English only,
    // and counts what it counted in German.
    await page.goto("/overview");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    expect(await workCounts(page, WORK_TABS.en)).toEqual(work);
    for (const name of ["Zur Freigabe", "Zurückgewiesen", "Kein Entwurf"]) {
      await expect(tab(page, name)).toHaveCount(0);
    }

    // The patients list counts what it counted in German …
    await page.goto("/patients");
    expect(await tabCounts(page, PATIENT_TABS.en)).toEqual(counts);
    await expect(rows).toHaveCount(all);

    // … and a tab shows the rows it counts: by where the report stands, not by its name.
    const releasedTab = tab(page, PATIENT_TABS.en.released);
    await hydrated(releasedTab);
    await releasedTab.click();
    await expect(rows).toHaveCount(released);
    for (const row of await rows.all()) {
      await expect(row).toContainText("Released");
    }
    await expect(body).toContainText(`Showing ${released} of ${all}`);
    await tab(page, PATIENT_TABS.en.none).click();
    await expect(rows).toHaveCount(none);
    for (const row of await rows.all()) {
      await expect(row).toContainText("No draft");
    }
  });
});

test("the patient page follows the choice; what is not interface stays German and says so", async ({
  browser,
  baseURL,
}) => {
  await asStaff(browser, "medicalDirector", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    const languageOf = (part: Locator) =>
      part.evaluate((element) =>
        element.closest("[lang]")?.getAttribute("lang"),
      );

    // The seeded patient, opened from the list by its row.
    await page.goto("/patients");
    const row = page.getByRole("button", {
      name: /^Open patient .*, SYN-0001$/,
    });
    await hydrated(row);
    await row.click();
    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const body = page.locator("body");

    // The page's own wording is English: the way back, its cards, the audit steps.
    const back = page.getByRole("button", { name: "Back to patients" });
    await expect(back).toBeVisible();
    expect(await languageOf(back)).toBe("en");
    for (const heading of [
      "Data coverage",
      "Before the visit",
      "Domains",
      "Consents",
      "Laboratory data",
      "Audit status",
    ]) {
      await expect(
        page.getByRole("heading", { level: 3, name: heading, exact: true }),
      ).toBeVisible();
    }
    for (const german of [
      "Datenlage",
      "Vor dem Termin",
      "Kernmarker",
      "Labordaten",
      "Audit-Status",
      "Zurück zu Patienten",
    ]) {
      await expect(body).not.toContainText(german);
    }
    // The counts before a visit are English and filter the lists; each is a button.
    const prep = page.getByRole("region", { name: "Before the visit" });
    await expect(prep).toContainText(
      /Last interpretation: run \d+ · \d{2}\.\d{2}\.\d{4}/,
    );
    await expect(
      prep.getByRole("button", {
        name: /core markers? without a published value/,
      }),
    ).toBeVisible();
    // This role reads and does not record: the two cards say so, each in one sentence.
    await expect(body).toContainText(
      "earlier entries are never changed. Documenting is reserved for the practice team (read-only view).",
    );
    await expect(body).toContainText(
      "Uploading and reading is reserved for the practice team (read-only view).",
    );

    // Not interface, and German whatever the choice — each says that it is German.
    // The wording of a consent purpose, in its row and in the note under the list:
    const purposes = page.getByText("Freigabe geprüfter Berichte", {
      exact: true,
    });
    await expect(purposes).toHaveCount(2);
    for (const purpose of await purposes.all()) {
      expect(await languageOf(purpose)).toBe("de");
    }
    await expect(body).toContainText(
      "At present only the purpose Freigabe geprüfter Berichte is enforced technically",
    );

    // The names of the six domain axes (a closed vocabulary — ADR-0007), and on each card
    // the VALUE of follow-up adequacy; the name of that fact is interface, and so is the
    // state of the card's run.
    const cards = page.locator(".vb-domaincard");
    await expect(cards).toHaveCount(6);
    for (const axis of [
      "Metabolisch",
      "Immun / Entzündung",
      "Kardiovaskulär",
      "Neurokognitiv",
      "Muskuloskelettal",
      "Regenerationskapazität",
    ]) {
      const name = cards.getByText(axis, { exact: true });
      await expect(name).toBeVisible();
      expect(await languageOf(name)).toBe("de");
    }
    const run = cards.getByText(/^(Reviewed|Draft|No run)$/);
    await expect(run).toHaveCount(6);
    for (const state of await run.all()) {
      expect(await languageOf(state)).toBe("en");
    }
    await expect(cards.getByText(/^(Geprüft|Entwurf|Kein Lauf)$/)).toHaveCount(
      0,
    );
    // The seeded patient has an interpretation run: adequacy is stated.
    const adequacy = cards.getByText(/^(adäquat|inadäquat|nicht bewertet)$/);
    expect(await adequacy.count()).toBeGreaterThan(0);
    for (const value of await adequacy.all()) {
      expect(await languageOf(value)).toBe("de");
    }
    await expect(cards.first()).toContainText("Follow-up adequacy:");
    // The clinician's own CIS and Actionability, quoted: German, and marked so.
    const verdicts = cards.getByText(/^(CIS-\d|[A-E]) · /);
    await expect(verdicts).toHaveCount(12);
    for (const value of await verdicts.all()) {
      expect(await languageOf(value)).toBe("de");
    }
    await expect(cards.first()).toContainText(
      /Run \d+ · recorded on \d{2}\.\d{2}\.\d{4}/,
    );
    for (const english of ["adequate", "not assessed"]) {
      await expect(cards.filter({ hasText: english })).toHaveCount(0);
    }

    // The marker list of each domain: its heading names the domain in German, and every
    // value's position against its reference interval is one of the German names — none of
    // the English ones lib/lageCopy.ts holds, nor an English comparability note.
    const metabolic = page.getByRole("region", {
      name: "Metabolisch",
      exact: true,
    });
    expect(
      await languageOf(
        metabolic.getByRole("heading", { level: 3 }).locator("span"),
      ),
    ).toBe("de");
    await expect(metabolic).toContainText(
      /\d+ of \d+ core markers with a published value/,
    );
    const rows = page.locator(".vb-erow[role=button]");
    expect(await rows.count(), "the seeded patient has values").toBeGreaterThan(
      0,
    );
    const pills = rows
      .locator("span[lang=de]")
      .filter({ has: page.locator(".sr-only") });
    expect(await pills.count()).toBeGreaterThan(0);
    for (const pill of await pills.all()) {
      await expect(pill).toContainText(
        /Über Referenz|Unter Referenz|Im Intervall|Keine Referenz|Nicht bestimmbar/,
      );
    }
    // A marker the catalog links here from another domain names that domain — in German.
    const cardio = page.getByRole("region", {
      name: "Kardiovaskulär",
      exact: true,
    });
    await expect(cardio).toContainText("Also relevant here");
    const home = cardio.getByText("Metabolisch", { exact: true });
    expect(await languageOf(home.first())).toBe("de");
    const englishVocabulary = [
      "Above reference",
      "Below reference",
      "Within reference",
      "No reference",
      "Not determinable",
      "Not directly comparable",
      "Longitudinal comparison not available",
      "Not longitudinally comparable",
    ];
    for (const english of englishVocabulary) {
      await expect(body).not.toContainText(english);
    }

    // The detail of a value: English around a German sentence about its position.
    await rows.first().click();
    const detail = page.getByRole("dialog");
    await expect(detail).toContainText("Review status");
    await expect(detail).toContainText("published");
    // Its history: an image named in English, described by an English sentence, with the
    // English note that nothing is drawn but recorded values.
    await expect(
      detail.getByRole("img", {
        name: /^History of .+\. Every value is also in the table beneath\.$/,
      }),
    ).toBeVisible();
    await expect(detail).toContainText(
      /(one published value|\d+ published values)/,
    );
    await expect(detail).toContainText(
      "Recorded values only: no trend line, no smoothing, no forecast.",
    );
    // Every value of the marker beneath, with English column names.
    await expect(detail).toContainText("All values of this marker");
    await expect(
      detail.getByRole("columnheader", { name: "As reported", exact: true }),
    ).toBeVisible();
    await expect(detail).toContainText(
      "Position relative to the source reference interval · not a diagnosis or treatment advice.",
    );
    const sentence = detail.getByText(
      /Quellreferenzintervall|Referenzintervall/,
      {
        exact: false,
      },
    );
    expect(await sentence.count()).toBeGreaterThan(0);
    for (const german of await sentence.all()) {
      expect(await languageOf(german)).toBe("de");
    }
    for (const english of englishVocabulary) {
      await expect(detail).not.toContainText(english);
    }
    await detail.getByRole("button", { name: "Close" }).click();
    await expect(detail).toHaveCount(0);

    // A page that is not translated yet — the one an invited colleague opens (here without a
    // valid link, so nothing is asked of the API): the document is English, and the page says
    // it is German.
    await page.goto("/team-einladung");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const invitation = page.getByRole("heading", { level: 1 });
    await expect(invitation).toHaveText("Einladung ins Klinik-Team");
    expect(await languageOf(invitation)).toBe("de");
  });

  // What a server action of this page answers follows the choice as well. A file whose name
  // is too long is refused before anything is stored: nothing is written, nothing recorded.
  await asStaff(browser, "clinician", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    await page.goto("/patients");
    const row = page.getByRole("button", {
      name: /^Open patient .*, SYN-0001$/,
    });
    await hydrated(row);
    await row.click();
    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
    const upload = page.getByRole("button", { name: "Upload and read" });
    await hydrated(upload);
    await page.getByLabel("Choose laboratory file").setInputFiles({
      name: `${"synthetic-".repeat(20)}x.csv`,
      mimeType: "text/csv",
      buffer: Buffer.from("analyte;value;date\n"),
    });
    await upload.click();
    await expect(
      page.getByRole("region", { name: "Laboratory data" }).getByRole("alert"),
    ).toHaveText("The file name is too long (200 characters at most).");
  });
});

test("the interpretation form follows the choice; what is chosen in it stays German and says so", async ({
  browser,
  baseURL,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    const languageOf = (part: Locator) =>
      part.evaluate((element) =>
        element.closest("[lang]")?.getAttribute("lang"),
      );

    // From the seeded patient's page, which has a run: the form opens as a correction.
    await page.goto("/patients");
    const row = page.getByRole("button", {
      name: /^Open patient .*, SYN-0001$/,
    });
    await hydrated(row);
    await row.click();
    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
    await page.getByRole("button", { name: "Record interpretation" }).click();
    await expect(page).toHaveURL(/\/interpretation\/neu$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const heading = page.getByRole("heading", {
      level: 1,
      name: /^Record interpretation · correction after run \d+$/,
    });
    await expect(heading).toBeVisible();
    expect(await languageOf(heading)).toBe("en");
    const body = page.locator("body");
    await expect(body).toContainText(
      "The system validates and records your entries; it derives nothing.",
    );
    await expect(body).not.toContainText("Bitte wählen");

    // The fields are named in English; a domain's name and every value to choose stay German.
    const domain = page.getByRole("region", { name: "Metabolisch" });
    for (const field of ["CIS", "Actionability", "Follow-up adequacy"]) {
      await expect(
        domain.getByRole("combobox", { name: field, exact: true }),
      ).toBeVisible();
    }
    expect(await languageOf(domain.getByRole("heading", { level: 2 }))).toBe(
      "de",
    );
    const choices = domain.locator("option:not([value=''])");
    expect(await choices.count()).toBeGreaterThan(0);
    for (const choice of await choices.all()) {
      expect(await languageOf(choice)).toBe("de");
    }
    const biological = domain.getByRole("group", { name: /^Biologisch/ });
    await expect(biological).toContainText("(verdict-free)");
    await expect(
      biological.getByRole("combobox", { name: "State", exact: true }),
    ).toBeVisible();
    await expect(
      biological.getByRole("combobox", {
        name: "Endpoint adequacy",
        exact: true,
      }),
    ).toBeVisible();

    // What the form says before anything is sent is English as well. Nothing is recorded.
    const submit = page.getByRole("button", {
      name: "Record interpretation",
    });
    await hydrated(submit);
    await submit.click();
    await expect(page.getByRole("main").getByRole("alert")).toHaveText(
      "Please give a reason.",
    );
  });
});

test("the report page follows the choice; its closed vocabularies stay German and say so", async ({
  browser,
  baseURL,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    const languageOf = (part: Locator) =>
      part.evaluate((element) =>
        element.closest("[lang]")?.getAttribute("lang"),
      );

    // The seeded patient's latest report, from its page: a draft — the seed's own, or (in CI,
    // where the web smoke has released that one first) the second report it rejected and
    // reworked.
    await page.goto("/patients");
    const row = page.getByRole("button", {
      name: /^Open patient .*, SYN-0001$/,
    });
    await hydrated(row);
    await row.click();
    await expect(page).toHaveURL(/\/patients\/[0-9a-f-]{36}$/);
    // A click before the page is hydrated can be lost to the router's take-over.
    const openReport = page.getByRole("link", { name: "Open report" });
    await hydrated(openReport);
    await openReport.click();
    await expect(page).toHaveURL(/\/assessments\/[0-9a-f-]{36}$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const main = page.getByRole("main");
    expect(await languageOf(main)).toBe("en");

    // The page's own wording is English.
    for (const heading of [
      "Source-grounded draft",
      "Domain interpretation",
      "Observation evidence",
      "Audit status",
    ]) {
      await expect(
        page.getByRole("heading", { level: 2, name: heading, exact: true }),
      ).toBeVisible();
    }
    await expect(main).toContainText(
      /(System|Reworked) draft – not released\. Statements must be checked against their sources and signed by the clinical team\./,
    );
    await expect(main).toContainText(
      /Report v\d+ · Status: Clinical review open/,
    );
    const filters = page.getByRole("group", {
      name: "Filter by position relative to the reference interval",
    });
    for (const filter of ["All", "Outside reference", "Without reference"]) {
      await expect(
        filters.getByRole("button", { name: filter, exact: true }),
      ).toBeVisible();
    }
    for (const column of ["Position vs. reference interval", "Code / status"]) {
      await expect(
        page.getByRole("columnheader", { name: column, exact: true }),
      ).toBeVisible();
    }
    for (const german of [
      "Beobachtungsnachweis",
      "Domänen-Interpretation",
      "Audit-Status",
      "Quellengebundener",
      "Nicht freigegeben",
      "Außerhalb Referenz",
      "Bericht v",
    ]) {
      await expect(main).not.toContainText(german);
    }

    // German whatever the choice, and marked so: the name of each domain, its Actionability
    // class and the value of its follow-up adequacy; every position against the reference
    // interval.
    const domains = page.getByRole("region", { name: "Domain interpretation" });
    const axis = domains.getByText("Metabolisch", { exact: true });
    expect(await languageOf(axis)).toBe("de");
    const classes = domains.getByText(/^[A-E] · /);
    expect(await classes.count()).toBeGreaterThan(0);
    for (const value of await classes.all()) {
      expect(await languageOf(value)).toBe("de");
    }
    const adequacy = domains.getByText(/^(adäquat|inadäquat|nicht bewertet)$/);
    expect(await adequacy.count()).toBeGreaterThan(0);
    for (const value of await adequacy.all()) {
      expect(await languageOf(value)).toBe("de");
    }
    const pills = page.locator(".lage-pill");
    expect(await pills.count()).toBeGreaterThan(0);
    for (const pill of await pills.all()) {
      expect(await pill.getAttribute("lang")).toBe("de");
    }
    await expect(main).not.toContainText(
      /Above reference|Below reference|Within reference|No reference|Not determinable/,
    );

    // A chosen domain: English around its German name.
    const metabolic = domains.getByRole("button", { name: /^Metabolisch/ });
    await hydrated(metabolic);
    await metabolic.click();
    await expect(metabolic).toHaveAttribute("aria-pressed", "true");
    await expect(main).toContainText(
      "The domain's own observations: Metabolisch.",
    );
    await page.getByRole("button", { name: "Show all", exact: true }).click();
    await expect(metabolic).toHaveAttribute("aria-pressed", "false");

    // The two decisions this role has here, opened and left: their dialogs are English, the
    // reasons for a rejection (a closed vocabulary) German. Nothing is recorded.
    await page.getByRole("button", { name: "Reject", exact: true }).click();
    const reject = page.getByRole("dialog", { name: "Reject the report?" });
    await expect(reject).toBeVisible();
    const reasons = reject.getByRole("group", {
      name: "Reason for the rejection",
    });
    const wording = reasons.getByRole("radio", { name: /^Formulierung — / });
    await expect(wording).toBeVisible();
    expect(
      await languageOf(reasons.getByText("Formulierung", { exact: true })),
    ).toBe("de");
    await expect(
      reject.getByRole("button", { name: "Reject", exact: true }),
    ).toBeDisabled();
    await reject.getByRole("button", { name: "Cancel" }).click();
    await expect(reject).toHaveCount(0);

    await page.getByRole("button", { name: "Approve report" }).click();
    const approve = page.getByRole("dialog", { name: "Approve the report?" });
    await expect(
      approve.getByRole("checkbox", {
        name: "I have checked the open notes and confirm the clinical documentation.",
      }),
    ).toBeVisible();
    await expect(
      approve.getByRole("button", { name: "Approve", exact: true }),
    ).toBeDisabled();
    await approve.getByRole("button", { name: "Close dialog" }).click();
    await expect(approve).toHaveCount(0);
    await expect(main).toContainText(
      /Report v\d+ · Status: Clinical review open/,
    );
  });
});

test("members and deletion requests follow the choice; names are shown as recorded", async ({
  browser,
  baseURL,
}) => {
  // The owner manages the team: the roles carry their English names, as in the shell.
  await asStaff(browser, "owner", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    await page.goto("/einstellungen");
    await page
      .getByRole("navigation", { name: "Settings sections" })
      .getByRole("link", { name: "Team & roles" })
      .click();
    await expect(page).toHaveURL(/\/einstellungen\/mitglieder$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const main = page.getByRole("main");
    await expect(
      page.getByRole("heading", { level: 1, name: "Team & roles" }),
    ).toBeVisible();
    await expect(main).toContainText(
      "Who works in this clinic and what their role allows.",
    );
    const team = page.getByRole("region", { name: /^Members/ });
    await expect(team).toContainText("owner@demo.synthetic");
    await expect(team).toContainText("· you");
    const role = team.getByRole("combobox", {
      name: "Role of Synthetic Clinician",
    });
    await expect(role).toHaveValue("clinician");
    await expect(role.locator("option")).toHaveText([
      "Clinician",
      "Assistant",
      "Medical director",
      "Owner",
    ]);
    // What else can be done with a colleague: behind their row's button.
    const more = team.getByRole("button", {
      name: "More actions for Synthetic Clinician",
    });
    await hydrated(more);
    await more.click();
    await expect(
      team.getByRole("button", { name: "Remove from the team …" }),
    ).toBeVisible();
    await expect(
      team.getByRole("link", { name: "Show in the audit trail" }),
    ).toHaveAttribute("href", /\/einstellungen\/audit\?actor=[0-9a-f-]{36}$/);
    await page.keyboard.press("Escape");
    await expect(more).toBeFocused();
    // Inviting opens a dialog; nothing is created until it is asked for.
    await page.getByRole("button", { name: "Invite a colleague" }).click();
    const dialog = page.getByRole("dialog", { name: "Invite a colleague" });
    await expect(
      dialog.getByRole("textbox", { name: "Who it is for (optional)" }),
    ).toBeFocused();
    await expect(
      dialog.getByRole("button", { name: "Create invitation link" }),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: /^Open invitations/ }),
    ).toBeVisible();
    const matrix = page.getByRole("table", { name: "What each role may do" });
    await expect(matrix.getByRole("columnheader")).toHaveText([
      "May",
      "Assistant",
      "Clinician",
      "Medical director",
      "Owner",
    ]);
    await expect(
      matrix.getByRole("row", { name: /^Release reports/ }),
    ).toHaveText(/Release reports\s*–\s*no\s*–\s*no\s*✓\s*yes\s*–\s*no/);
    for (const german of [
      "Mitglieder",
      "Entfernen",
      "Kolleg:in einladen",
      "Offene Einladungen",
      "Ärztliche Leitung",
      "Inhaber",
    ]) {
      await expect(main).not.toContainText(german);
    }
  });

  // The medical director decides on deletion requests. The seed holds none; whether this run
  // shows any, the page around them is English.
  await asStaff(browser, "medicalDirector", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    await page.goto("/einstellungen");
    await page
      .getByRole("navigation", { name: "Settings sections" })
      .getByRole("link", { name: "Deletion requests" })
      .click();
    await expect(page).toHaveURL(/\/einstellungen\/loeschantraege$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const main = page.getByRole("main");
    await expect(
      page.getByRole("heading", { level: 1, name: "Deletion requests" }),
    ).toBeVisible();
    await expect(main).toContainText(
      "reviewed by the medical director (two-person approval)",
    );
    for (const german of ["Löschanträge", "Vier-Augen-Prinzip", "beantragt"]) {
      await expect(main).not.toContainText(german);
    }
  });

  // A role these pages are not for is told so, in its language.
  await asStaff(browser, "clinician", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    await page.goto("/einstellungen/mitglieder");
    await expect(page.getByRole("main")).toContainText(
      "Member management is available to owners only.",
    );
    await page.goto("/einstellungen/loeschantraege");
    await expect(page.getByRole("main")).toContainText(
      "Managing deletion requests is reserved for owners and the medical director.",
    );
  });
});

test("the audit trail and preparation time follow the choice; codes and names stay as recorded", async ({
  browser,
  baseURL,
}) => {
  await asStaff(browser, "owner", async (page) => {
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);
    const main = page.getByRole("main");

    // The audit trail: its frame, its filter and its table are English, and so is the label of
    // every event — next to the code the API wrote, which stays as it is. The owner's own entry
    // into the clinic is always there.
    await page.goto("/einstellungen");
    await page
      .getByRole("navigation", { name: "Settings sections" })
      .getByRole("link", { name: "Audit trail" })
      .click();
    await expect(page).toHaveURL(/\/einstellungen\/audit$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit trail" }),
    ).toBeVisible();
    await expect(main.locator("summary")).toHaveText(
      "What this trail does not show",
    );
    await expect(main).toContainText(
      "Not recorded at present: a report read by staff",
    );
    const area = page.getByRole("combobox", { name: "Area" });
    await expect(area.locator("option").first()).toHaveText("All areas");
    await expect(area.locator("option[value=tenant]")).toHaveText(
      "Entering the clinic",
    );
    await page.goto("/einstellungen/audit?category=tenant");
    const table = page.getByRole("table", {
      name: "Audit trail, newest entries first",
    });
    for (const column of ["Time", "Who", "Event", "Record", "Details"]) {
      await expect(
        table.getByRole("columnheader", { name: column, exact: true }),
      ).toBeVisible();
    }
    await expect(table.getByText("Clinic selected").first()).toBeVisible();
    await expect(table.getByText("tenant.select").first()).toBeVisible();
    for (const german of [
      "Audit-Protokoll",
      "Praxis ausgewählt",
      "Was dieses Protokoll nicht zeigt",
      "Alle Bereiche",
      "Vorgang",
    ]) {
      await expect(main).not.toContainText(german);
    }

    // Preparation time: what the clinic states and what the platform measures, in English;
    // so is what the form's action answers. (A figure the form refuses records nothing.)
    await page.goto("/einstellungen/vorbereitungszeit?fehler=minuten");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(
      page.getByRole("heading", { level: 1, name: "Preparation time" }),
    ).toBeVisible();
    for (const heading of [
      "Stated by the clinic",
      "Measured from the course of the reports",
      "What these figures are – and what they are not",
    ]) {
      await expect(
        page.getByRole("heading", { level: 2, name: heading }),
      ).toBeVisible();
    }
    // (Within main: Next's route announcer is an alert of its own.)
    await expect(main.getByRole("alert")).toHaveText(
      "The figure was not saved: the median is a whole number from 1 to 600 minutes.",
    );
    await expect(
      page.getByRole("combobox", { name: "Kind of figure" }).locator("option"),
    ).toHaveText(["Baseline", "Follow-up figure"]);
    await expect(main).toContainText("not working time");
    for (const german of [
      "Vorbereitungszeit",
      "Angaben der Praxis",
      "Ausgangswert",
      "Arbeitszeit",
      "nicht gespeichert",
    ]) {
      await expect(main).not.toContainText(german);
    }
  });
});

test("the choice works before the page is hydrated, too", async ({
  browser,
}) => {
  // The form posts by itself; nothing of it waits for a script.
  await asStaff(
    browser,
    "medicalDirector",
    async (page) => {
      await page.goto("/einstellungen");
      await page.getByRole("button", { name: "English" }).click();
      await expectEnglishSettings(page);
    },
    { unhydrated: true },
  );
});

test("the sign-in page speaks the chosen language and offers the choice; a cookie that names no language counts as none", async ({
  browser,
  baseURL,
}) => {
  const signInPage = async (choice: string | null) => {
    const context = await browser.newContext();
    const noPageErrors = watchPageErrors(context);
    try {
      if (choice !== null) {
        await context.addCookies([
          { name: "hadp_locale", value: choice, url: baseURL ?? "" },
        ]);
      }
      const page = await context.newPage();
      await page.goto("/login");
      const seen = {
        lang: await page.locator("html").getAttribute("lang"),
        heading: await page.getByRole("heading", { level: 2 }).innerText(),
        label: await page.locator(".field-label").innerText(),
      };
      noPageErrors();
      return seen;
    } finally {
      await context.close();
    }
  };

  const english = { lang: "en", heading: "Sign in", label: "E-mail address" };
  const german = { lang: "de", heading: "Anmelden", label: "E-Mail-Adresse" };
  expect(await signInPage("en")).toEqual(english);
  expect(await signInPage(null)).toEqual(german);
  expect(await signInPage("fr")).toEqual(german);
  // Only the two offered codes are languages; a near miss is not.
  expect(await signInPage("EN")).toEqual(german);
  expect(await signInPage("en-US")).toEqual(german);

  // Chosen on the sign-in page itself, before any session exists.
  const context = await browser.newContext();
  const noPageErrors = watchPageErrors(context);
  try {
    const page = await context.newPage();
    await page.goto("/login");
    const choose = page.getByRole("button", { name: "English" });
    await hydrated(choose);
    await choose.click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(
      page.getByRole("heading", { level: 2, name: "Sign in" }),
    ).toBeVisible();
    // The not-found page follows it as well.
    await page.goto("/this-page-does-not-exist");
    await expect(
      page.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeVisible();
    noPageErrors();
  } finally {
    await context.close();
  }
});
