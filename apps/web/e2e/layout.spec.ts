import { expect, test, type Page } from "@playwright/test";

import { asStaff } from "./support/staff";

// A page never scrolls sideways on a phone (docs/notes/0019). What is wider than the screen —
// a table, the role matrix — scrolls inside its own card; the page itself does not. Measured as
// the browser sees it: the document's scroll width against the viewport.
//
// The pages of the demo clinic, as the owner, who may open every one of them.
const PAGES = [
  "/overview",
  "/patients",
  "/review-queue",
  "/einstellungen",
  "/einstellungen/profil",
  "/einstellungen/sicherheit",
  "/einstellungen/praxis",
  "/einstellungen/mitglieder",
  "/einstellungen/datenquellen",
  "/einstellungen/vorbereitungszeit",
  "/einstellungen/loeschantraege",
  "/einstellungen/audit",
  "/einstellungen/einwilligungen",
  "/einstellungen/aufbewahrung",
];

const PHONE = { width: 390, height: 844 };

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
}

test("no page scrolls sideways on a phone", async ({ browser }) => {
  await asStaff(browser, "owner", async (page) => {
    await page.setViewportSize(PHONE);
    for (const path of PAGES) {
      await page.goto(path);
      await expect(page.getByRole("main")).toBeVisible();
      expect(await overflow(page), `${path} overflows sideways`).toBe(0);
    }
    // The patient page: the one the clinic opens most, with its domain tables.
    await page.goto("/patients");
    const row = page.getByRole("button", { name: /SYN-0001/ }).first();
    await row.click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("main")).toBeVisible();
    expect(await overflow(page), "the patient page overflows sideways").toBe(0);
  });
});

test("the sign-in and a patient's page fit a phone too", async ({
  browser,
}) => {
  const context = await browser.newContext({ viewport: PHONE });
  try {
    const page = await context.newPage();
    for (const path of ["/login", "/patient-view", "/this-page-is-not-here"]) {
      await page.goto(path);
      await expect(page.getByRole("main")).toBeVisible();
      expect(await overflow(page), `${path} overflows sideways`).toBe(0);
    }
  } finally {
    await context.close();
  }
});
