import { expect, test, type Locator, type Page } from "@playwright/test";

import { asStaff, hydrated, watchPageErrors } from "./support/staff";

// The interface language is a person's choice — under Einstellungen, or on the sign-in page —
// kept on the device (apps/web/src/lib/i18n). German is what a device without a choice gets.
//
// The pages are being translated one after another; these tests hold what is done: the two
// navigation shells, the settings overview, the overview, the patients list, the sign-in page
// and the not-found page — and that a page which is still German says so. They leave every
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
    // The one part of it that is not translated yet says so: the button, and the dialog it
    // opens.
    const add = page.getByRole("button", { name: "Patient hinzufügen" });
    expect(await languageOf(add)).toBe("de");
    await add.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toHaveAttribute("lang", "de");
    await page.keyboard.press("Escape");
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
