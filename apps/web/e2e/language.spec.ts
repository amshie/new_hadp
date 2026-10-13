import { expect, test, type Page } from "@playwright/test";

import { asStaff, hydrated, watchPageErrors } from "./support/staff";

// The interface language is a person's choice — under Einstellungen, or on the sign-in page —
// kept on the device (apps/web/src/lib/i18n). German is what a device without a choice gets.
//
// The pages are being translated one after another; these tests hold what is done: the two
// navigation shells, the settings overview, the sign-in page and the not-found page — and
// that a page which is still German says so. They leave every other test in German: each
// runs in a browser context of its own, and none of them signs out (the session is shared).

// The medical director: the one seeded role whose name differs between the two languages.
const ROLE = { de: "Ärztliche Leitung", en: "Medical director" };

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

    // It holds on the next page, reached by a link of the shell (no full page load). That
    // page is not translated yet: the shell is English, and the page says it is German.
    await page
      .getByRole("complementary", { name: "Main navigation" })
      .getByRole("link", { name: "Overview" })
      .click();
    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
    await expect(
      page.getByRole("heading", { level: 1, name: "Übersicht" }),
    ).toBeVisible();
    expect(
      await page
        .getByRole("heading", { level: 1, name: "Übersicht" })
        .evaluate((heading) => heading.closest("[lang]")?.getAttribute("lang")),
    ).toBe("de");

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
