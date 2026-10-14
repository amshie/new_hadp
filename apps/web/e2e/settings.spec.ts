import { expect, test, type Page } from "@playwright/test";

import { asStaff, hydrated } from "./support/staff";

// Einstellungen (apps/web/src/app/einstellungen): the sub-navigation beside every settings
// page, a section a role may not open shown locked rather than hidden, each card with what
// it holds now, and the appearance chosen on this device. Navigation only — every page and
// route authorizes on its own (see language.spec.ts and the API's tests).

const nav = (page: Page) =>
  page.getByRole("navigation", { name: "Bereiche der Einstellungen" });

test("a section the role may not open is named and locked, not hidden", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/einstellungen");
    const sections = nav(page);
    // The one section every role opens is a link, and it is the page shown.
    await expect(sections.getByRole("link")).toHaveCount(1);
    await expect(
      sections.getByRole("link", { name: "Sprache & Darstellung" }),
    ).toHaveAttribute("aria-current", "page");
    // The four others are listed, locked, and say for whom they are.
    const locked = sections.locator('[aria-disabled="true"]');
    await expect(locked).toHaveCount(4);
    await expect(locked.filter({ hasText: "Mitglieder" })).toContainText(
      "Nur für Inhaber",
    );
    await expect(locked.filter({ hasText: "Löschanträge" })).toContainText(
      "Nur für Inhaber und Ärztliche Leitung",
    );
    // The cards of "Alle Bereiche" are locked too: no link, no state read for this role.
    const all = page.getByRole("region", { name: "Alle Bereiche" });
    await expect(all.getByRole("link")).toHaveCount(0);
    await expect(all.getByRole("listitem")).toHaveCount(4);
  });
});

test("the sub-navigation stays on every settings page, and each card says what it holds", async ({
  browser,
}) => {
  await asStaff(browser, "owner", async (page) => {
    await page.goto("/einstellungen");
    const all = page.getByRole("region", { name: "Alle Bereiche" });
    await expect(all.getByRole("link")).toHaveCount(4);
    await expect(all.getByRole("link", { name: /^Mitglieder/ })).toContainText(
      /\d+ Mitglieder · /,
    );
    await expect(
      all.getByRole("link", { name: /^Löschanträge/ }),
    ).toContainText(/Kein Antrag offen|\d+ Anträ?ge? offen/);
    await expect(
      all.getByRole("link", { name: /^Audit-Protokoll/ }),
    ).toContainText(/abgewiesene?r? Zugriffe? in 7 Tagen/);

    // From one settings page to the next without going back.
    await page.goto("/einstellungen/audit");
    await expect(
      nav(page).getByRole("link", { name: "Audit-Protokoll" }),
    ).toHaveAttribute("aria-current", "page");
    await nav(page).getByRole("link", { name: "Vorbereitungszeit" }).click();
    await expect(page).toHaveURL(/\/einstellungen\/vorbereitungszeit$/);
    await expect(
      nav(page).getByRole("link", { name: "Vorbereitungszeit" }),
    ).toHaveAttribute("aria-current", "page");
    await expect(nav(page).locator('[aria-disabled="true"]')).toHaveCount(0);
  });
});

test("the appearance is light, dark, or as the device's system is set", async ({
  browser,
}) => {
  await asStaff(browser, "assistant", async (page) => {
    const theme = page.locator(".vb-scope[data-theme]").first();
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/einstellungen");
    const choice = page.getByRole("group", { name: "Erscheinungsbild" });
    const dark = choice.getByRole("button", { name: "Dunkel" });
    await hydrated(dark);
    await expect(theme).toHaveAttribute("data-theme", "light");
    await expect(choice.getByRole("button", { name: "Hell" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await dark.click();
    await expect(theme).toHaveAttribute("data-theme", "dark");
    await expect(dark).toHaveAttribute("aria-pressed", "true");
    // Kept on this device.
    await page.reload();
    await expect(theme).toHaveAttribute("data-theme", "dark");

    // As the system: follows the device's setting, and its changes.
    await choice.getByRole("button", { name: "System" }).click();
    await expect(theme).toHaveAttribute("data-theme", "light");
    await page.emulateMedia({ colorScheme: "dark" });
    await expect(theme).toHaveAttribute("data-theme", "dark");

    await choice.getByRole("button", { name: "Hell" }).click();
    await expect(theme).toHaveAttribute("data-theme", "light");
  });
});
