import { expect, test, type Locator, type Page } from "@playwright/test";

import { asStaff, hydrated, watchPageErrors } from "./support/staff";

// The interface language is a person's choice — under Einstellungen, or on the sign-in page —
// kept on the device (apps/web/src/lib/i18n). German is what a device without a choice gets.
//
// The pages are being translated one after another; these tests hold what is done: the two
// navigation shells, the settings overview, the overview, the patients list, the dialog to
// add a patient (opened from the overview), the patient page, the sign-in page and the
// not-found page — and that a page which is still German says so. They leave every
// other test in German: each runs in a browser context of its own, and none of them signs out
// (the session is shared).

// The medical director: the one seeded role whose name differs between the two languages.
const ROLE = { de: "Ärztliche Leitung", en: "Medical director" };

// The four tabs of the patients list, and the five places a report can stand in.
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
const REPORT_STATES = {
  de: [
    "In Prüfung",
    "Genehmigt",
    "Freigegeben",
    "Zurückgewiesen",
    "Kein Entwurf",
  ],
  en: ["In review", "Approved", "Released", "Rejected", "No draft"],
};

// A tab of the patients list: its name, then what it counts.
const tab = (page: Page, name: string) =>
  page.getByRole("button", { name: new RegExp(`^${name} \\d+$`) });

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

// The card under a heading of the overview.
const card = (page: Page, title: string) =>
  page
    .locator("div")
    .filter({
      has: page.getByRole("heading", { level: 3, name: title, exact: true }),
    })
    .last();

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
    page.getByRole("link", { name: /Deletion requests/ }),
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

    // The overview is English: its headings, its work list, its report states.
    await navigation.getByRole("link", { name: "Overview" }).click();
    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
    const overview = page.getByRole("heading", { level: 1, name: "Overview" });
    await expect(overview).toBeVisible();
    expect(await languageOf(overview)).toBe("en");
    const body = page.locator("body");
    await expect(body).toContainText("Clinical work list");
    await expect(body).toContainText("Report status");
    await expect(body).not.toContainText("Klinische Arbeitsliste");
    await expect(body).not.toContainText("Berichtsstatus");
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

    // A page that is not translated yet: the shell is English, and the page says it is German.
    await navigation.getByRole("link", { name: "Review queue" }).click();
    await expect(page).toHaveURL(/\/review-queue$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const queue = page.getByRole("heading", { level: 1 });
    await expect(queue).toBeVisible();
    expect(await languageOf(queue)).toBe("de");

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
    await page.goto("/overview");
    await expect(body).toContainText(
      `Aktueller Bestand · Momentaufnahme · ${all} Patient`,
    );
    for (const state of REPORT_STATES.de) {
      await expect(card(page, "Berichtsstatus")).toContainText(state);
    }

    // The same device chooses English (by the cookie the two buttons set; choosing by a
    // button is the test above).
    await page
      .context()
      .addCookies([{ name: "hadp_locale", value: "en", url: baseURL ?? "" }]);

    // The overview names the five places a report can stand in, in English only.
    await page.goto("/overview");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(body).toContainText(
      `Current state · snapshot · ${all} patient`,
    );
    for (const state of REPORT_STATES.en) {
      await expect(card(page, "Report status")).toContainText(state);
    }
    for (const state of REPORT_STATES.de) {
      await expect(card(page, "Report status")).not.toContainText(state);
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
      "Labordaten",
      "Audit-Status",
      "Zurück zu Patienten",
    ]) {
      await expect(body).not.toContainText(german);
    }
    // This role reads and does not record: the two cards say so, each in one sentence.
    await expect(body).toContainText(
      "earlier entries are never changed. Documenting is reserved for the practice team (read-only view).",
    );
    await expect(body).toContainText(
      "Uploading and reading is reserved for the practice team (read-only view).",
    );

    // Not interface, and German whatever the choice: the wording of a consent purpose, and
    // the names of the six domain axes (a closed vocabulary — ADR-0007).
    const purpose = page.getByText("Freigabe geprüfter Berichte", {
      exact: true,
    });
    await expect(purpose).toBeVisible();
    expect(await languageOf(purpose)).toBe("de");
    for (const axis of [
      "Metabolisch",
      "Immun / Entzündung",
      "Kardiovaskulär",
      "Neurokognitiv",
      "Muskuloskelettal",
      "Regenerationskapazität",
    ]) {
      const name = page
        .locator(".vb-domaincard")
        .getByText(axis, { exact: true });
      await expect(name).toBeVisible();
      expect(await languageOf(name)).toBe("de");
    }
    // A position against the reference interval, where the page shows one, is German too.
    for (const pill of await page.locator(".vb-erow .sr-only").all()) {
      expect(await languageOf(pill)).toBe("de");
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
