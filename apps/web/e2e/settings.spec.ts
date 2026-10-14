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
    // Six sections are for every role (the personal ones, the clinic profile, the data
    // sources, the consent texts); this one is the page shown.
    await expect(sections.getByRole("link")).toHaveCount(6);
    await expect(
      sections.getByRole("link", { name: "Sprache & Darstellung" }),
    ).toHaveAttribute("aria-current", "page");
    // The four others are listed, locked, and say for whom they are.
    const locked = sections.locator('[aria-disabled="true"]');
    await expect(locked).toHaveCount(5);
    await expect(locked.filter({ hasText: "Team & Rollen" })).toContainText(
      "Nur für Inhaber",
    );
    await expect(locked.filter({ hasText: "Löschanträge" })).toContainText(
      "Nur für Inhaber und Ärztliche Leitung",
    );
    // The cards of "Alle Bereiche" are locked too: no link, no state read for this role.
    // Profile and security are this person's own, and say what they hold.
    const all = page.getByRole("region", { name: "Alle Bereiche" });
    await expect(all.getByRole("link")).toHaveCount(5);
    await expect(all.getByRole("listitem")).toHaveCount(10);
    await expect(all.getByRole("link", { name: /^Profil/ })).toContainText(
      "Synthetic Clinician · clinician@demo.synthetic",
    );
    await expect(
      all.getByRole("link", { name: /^Sicherheit & Sitzungen/ }),
    ).toContainText(/\d+ aktive Sitzungen? · Entwicklungsanmeldung/);
  });
});

test("the sub-navigation stays on every settings page, and each card says what it holds", async ({
  browser,
}) => {
  await asStaff(browser, "owner", async (page) => {
    await page.goto("/einstellungen");
    const all = page.getByRole("region", { name: "Alle Bereiche" });
    await expect(all.getByRole("link")).toHaveCount(10);
    await expect(
      all.getByRole("link", { name: /^Team & Rollen/ }),
    ).toContainText(/\d+ Mitglieder · /);
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

test("a colleague's row leads to their entries in the audit trail", async ({
  browser,
}) => {
  await asStaff(browser, "owner", async (page) => {
    await page.goto("/einstellungen/mitglieder");
    const team = page.getByRole("region", { name: /^Mitglieder/ });
    const more = team.getByRole("button", {
      name: "Weitere Aktionen für Synthetic Clinician",
    });
    await hydrated(more);
    await more.click();
    await team.getByRole("link", { name: "Im Protokoll anzeigen" }).click();
    await expect(page).toHaveURL(
      /\/einstellungen\/audit\?actor=[0-9a-f-]{36}$/,
    );
    const main = page.getByRole("main");
    await expect(main).toContainText("Nur Einträge von Synthetic Clinician.");
    // Every entry shown is theirs.
    const table = page.getByRole("table", {
      name: "Audit-Protokoll, neueste Einträge zuerst",
    });
    const rows = table.locator("tbody tr");
    expect(await rows.count()).toBeGreaterThan(0);
    for (const row of await rows.all()) {
      await expect(row).toContainText("Synthetic Clinician");
    }
    await main.getByRole("link", { name: "Alle Personen anzeigen" }).click();
    await expect(page).toHaveURL(/\/einstellungen\/audit$/);
  });
});

test("a person reads their profile, and ends their other sessions", async ({
  browser,
}) => {
  // A second sign-in of the same person, in a browser of its own.
  const elsewhere = await browser.newContext();
  const other = await elsewhere.newPage();
  await other.goto("/login");
  const address = other.getByRole("textbox", { name: "E-Mail-Adresse" });
  await hydrated(address);
  await address.fill("assistant@demo.synthetic");
  await address.press("Enter");
  await expect(other).toHaveURL(/\/overview$/);

  await asStaff(browser, "assistant", async (page) => {
    await page.goto("/einstellungen/profil");
    const account = page.getByRole("region", { name: "Konto" });
    await expect(account).toContainText("Synthetic Assistant");
    await expect(account).toContainText("assistant@demo.synthetic");
    await expect(account).toContainText("Assistenz");

    await page.goto("/einstellungen/sicherheit");
    const sessions = page.getByRole("table", {
      name: "Ihre Sitzungen, neueste zuerst",
    });
    await expect(sessions.getByText("diese Sitzung")).toHaveCount(1);
    await expect(page.getByRole("main")).toContainText(
      "Nicht vorhanden in der Entwicklungsanmeldung.",
    );
    const end = page.getByRole("button", {
      name: "Alle anderen Sitzungen beenden",
    });
    await hydrated(end);
    page.once("dialog", (dialog) => dialog.accept());
    await end.click();
    await expect(page.getByRole("status")).toHaveText(
      /^\d+ Sitzungen? beendet\.$/,
    );
    await expect(page.getByRole("main")).toContainText(
      "Keine andere Sitzung ist aktiv.",
    );
  });

  // The other sign-in is over; this person's session in the suite still works.
  await other.goto("/overview");
  await expect(other).toHaveURL(/\/login/);
  await elsewhere.close();
});

test("the owner keeps the clinic profile; everyone reads it", async ({
  browser,
}) => {
  await asStaff(browser, "owner", async (page) => {
    await page.goto("/einstellungen/praxis");
    const address = page.getByRole("textbox", { name: "Anschrift" });
    await hydrated(address);
    await expect(
      page.getByRole("textbox", { name: "Name der Praxis" }),
    ).toHaveValue("Synthetic Longevity Clinic");
    await expect(page.getByRole("main")).toContainText("Europe/Berlin");
    await address.fill("Synthetische Straße 1\n10115 Berlin");
    await page.getByRole("button", { name: "Speichern" }).click();
    await expect(page.getByRole("status")).toHaveText("Gespeichert.");
    await page.reload();
    await expect(page.getByRole("textbox", { name: "Anschrift" })).toHaveValue(
      "Synthetische Straße 1\n10115 Berlin",
    );
    // Back as it was: no address.
    const again = page.getByRole("textbox", { name: "Anschrift" });
    await hydrated(again);
    await again.fill("");
    await page.getByRole("button", { name: "Speichern" }).click();
    await expect(page.getByRole("status")).toHaveText("Gespeichert.");
  });
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/einstellungen/praxis");
    const main = page.getByRole("main");
    await expect(main).toContainText("Synthetic Longevity Clinic");
    await expect(main).toContainText("Ändern kann der Inhaber der Praxis.");
    await expect(page.getByRole("textbox")).toHaveCount(0);
  });
});

test("data sources, consent texts and retention say what is in place and what is not", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/einstellungen/datenquellen");
    const readers = page.getByRole("region", {
      name: "Leser für Labordateien",
    });
    for (const name of ["CSV (HADP-Layout)", "LDT 2", "LDT 3", "Wearables"]) {
      await expect(readers).toContainText(name);
    }
    await expect(page.getByRole("main")).toContainText(
      "PDF-Befunde werden noch nicht gelesen.",
    );

    await page.goto("/einstellungen/einwilligungen");
    const current = page.getByRole("region", { name: /^Aktuelle Fassung/ });
    await expect(current).toContainText("synthetic-v1");
    // The wording of a purpose is recorded text: German, and marked so.
    const purpose = current.getByText("Freigabe geprüfter Berichte");
    expect(
      await purpose.evaluate((e) => e.closest("[lang]")?.getAttribute("lang")),
    ).toBe("de");
    const table = page.getByRole("table", {
      name: "Einwilligungen je Zweck und Fassung",
    });
    await expect(table.getByRole("columnheader")).toHaveText([
      "Zweck",
      "Fassung",
      "Erteilt",
      "Widerrufen",
    ]);

    // Retention is the owner's: locked for this role.
    await expect(
      nav(page).locator('[aria-disabled="true"]', {
        hasText: "Aufbewahrung & Export",
      }),
    ).toContainText("Nur für Inhaber");
  });
  await asStaff(browser, "owner", async (page) => {
    await page.goto("/einstellungen/aufbewahrung");
    const main = page.getByRole("main");
    await expect(main).toContainText("Noch keine Richtlinie hinterlegt.");
    await expect(main).toContainText(
      "In dieser Pilotumgebung nicht eingerichtet.",
    );
    await expect(
      main.getByRole("link", { name: "Zu den Löschanträgen" }),
    ).toHaveAttribute("href", "/einstellungen/loeschantraege");
  });
});
