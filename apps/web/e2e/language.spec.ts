import { expect, test } from "@playwright/test";

import { asStaff } from "./support/staff";

// The interface language is a person's choice under Einstellungen, kept on the device
// (apps/web/src/lib/i18n). German is what a device without a choice gets.
//
// The pages are being translated one after another; these tests hold what is done: the
// shell, the settings page and the sign-in page. They leave every other test in German —
// each runs in a browser context of its own.

test("a person chooses English under Einstellungen, and goes back to German", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/einstellungen");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(
      page.getByRole("complementary", { name: "Hauptnavigation" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "English" }).click();

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
    await expect(page.getByRole("button", { name: "English" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByRole("button", { name: "Deutsch" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // The role next to the person's name is said in the interface language as well.
    await expect(page.getByRole("banner")).toContainText("Clinician");

    // The choice holds on the next page: the shell around the overview.
    await page.goto("/overview");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();

    await page.goto("/einstellungen");
    await page.getByRole("button", { name: "Deutsch" }).click();

    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(
      page.getByRole("heading", { level: 1, name: "Einstellungen" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Abmelden" })).toBeVisible();
  });
});

test("the sign-in page speaks the chosen language; a cookie that names no language counts as none", async ({
  browser,
  baseURL,
}) => {
  const visit = async (choice: string | null) => {
    const context = await browser.newContext();
    try {
      if (choice !== null) {
        await context.addCookies([
          { name: "hadp_locale", value: choice, url: baseURL ?? "" },
        ]);
      }
      const page = await context.newPage();
      await page.goto("/login");
      return {
        lang: await page.locator("html").getAttribute("lang"),
        heading: await page.getByRole("heading", { level: 2 }).innerText(),
        field: await page.getByRole("textbox").getAttribute("name"),
        label: await page.locator(".field-label").innerText(),
      };
    } finally {
      await context.close();
    }
  };

  expect(await visit("en")).toEqual({
    lang: "en",
    heading: "Sign in",
    field: "email",
    label: "E-mail address",
  });
  const german = {
    lang: "de",
    heading: "Anmelden",
    field: "email",
    label: "E-Mail-Adresse",
  };
  expect(await visit(null)).toEqual(german);
  expect(await visit("fr")).toEqual(german);
  // Only the two offered codes are languages; a near miss is not.
  expect(await visit("EN")).toEqual(german);
  expect(await visit("en-US")).toEqual(german);
});
