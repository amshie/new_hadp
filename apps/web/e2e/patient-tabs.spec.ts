import { expect, test } from "@playwright/test";

import {
  percentText,
  statedChange,
} from "../src/lib/presenters/preparationTime";
import { asStaff, hydrated, openTab } from "./support/staff";

// The patient page in three tabs (docs/notes/0025): the preparation first, then the values,
// then the record's administration; a link into a domain list opens the tab that holds it;
// a domain list folds the core markers without a value into one line. And the pilot's
// figure: the clinic's latest stated preparation time against its baseline, as a percentage,
// computed by the presenter from the two statements and nothing else.

const statement = (median_minutes: number) => ({
  id: "00000000-0000-4000-8000-000000000001",
  kind: "baseline" as const,
  basis: "estimate" as const,
  median_minutes,
  sample_size: null,
  recorded_at: "2026-03-12T08:00:00Z",
  recorded_by: null,
});

test("the stated change is the follow-up against the baseline, in minutes and percent", () => {
  expect(
    statedChange({ baseline: statement(60), latest_follow_up: statement(27) }),
  ).toEqual({
    baselineMinutes: 60,
    followUpMinutes: 27,
    minutes: -33,
    percent: -55,
    targetMet: true,
  });
  expect(
    statedChange({ baseline: statement(40), latest_follow_up: statement(30) }),
  ).toMatchObject({ minutes: -10, percent: -25, targetMet: false });
  expect(
    statedChange({ baseline: statement(40), latest_follow_up: statement(44) }),
  ).toMatchObject({ minutes: 4, percent: 10, targetMet: false });
  // Nothing to set against each other without both statements; nothing to measure against
  // a baseline of zero.
  expect(
    statedChange({ baseline: statement(40), latest_follow_up: null }),
  ).toBe(null);
  expect(
    statedChange({ baseline: null, latest_follow_up: statement(40) }),
  ).toBe(null);
  expect(
    statedChange({ baseline: statement(0), latest_follow_up: statement(10) }),
  ).toMatchObject({ percent: null, targetMet: false });
  expect(percentText(-55)).toBe("−55 %");
  expect(percentText(10)).toBe("+10 %");
  expect(percentText(0)).toBe("±0 %");
});

test("the page opens on the preparation; the values and the record are a tab away", async ({
  browser,
}) => {
  await asStaff(browser, "clinician", async (page) => {
    await page.goto("/patients");
    const row = page.getByRole("button", { name: /SYN-0001/ }).first();
    await hydrated(row);
    await row.click();
    await page.waitForURL(/\/patients\/[0-9a-f-]{36}$/);
    const patientPath = new URL(page.url()).pathname;

    const tabs = page.getByRole("tablist", { name: "Bereiche der Akte" });
    await expect(tabs.getByRole("tab")).toHaveText([
      /^Vorbereitung$/,
      /^Werte \d+$/,
      /^Akte$/,
    ]);
    const prep = tabs.getByRole("tab", { name: "Vorbereitung" });
    await hydrated(prep);
    await expect(prep).toHaveAttribute("aria-selected", "true");
    await expect(
      page.getByRole("region", { name: "Vorbereitung" }),
    ).toBeVisible();
    await expect(page.getByRole("region", { name: "Labordaten" })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("region", { name: "Metabolisch", exact: true }),
    ).toHaveCount(0);

    // The record's administration.
    await openTab(page, "Akte");
    await expect(
      page.getByRole("region", { name: "Labordaten" }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Einwilligungen" }),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Vorbereitung" }),
    ).toHaveCount(0);

    // The values: a domain list folds its core markers without a value into one line,
    // and unfolds them on request.
    await openTab(page, "Werte");
    const metabolic = page.getByRole("region", {
      name: "Metabolisch",
      exact: true,
    });
    await expect(metabolic).toBeVisible();
    const unfold = metabolic.getByRole("button", {
      name: /^\d+ Kernmarker ohne Wert anzeigen$/,
    });
    await expect(unfold).toHaveAttribute("aria-expanded", "false");
    await expect(metabolic.getByText("Kein Wert erfasst")).toHaveCount(0);
    await unfold.click();
    await expect(
      metabolic.getByRole("button", {
        name: "Kernmarker ohne Wert ausblenden",
      }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(
      await metabolic.getByText("Kein Wert erfasst").count(),
    ).toBeGreaterThan(0);

    // The keyboard moves between the tabs.
    await page.getByRole("tab", { name: /^Werte/ }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: /^Akte/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await page.keyboard.press("Home");
    await expect(prep).toHaveAttribute("aria-selected", "true");

    // A link into a domain list opens the values tab: a fragment set on this page (what a
    // link on the preparation card does), and an address that carries one.
    await page.evaluate(() => {
      window.location.hash = "#vb-domain-metabolic";
    });
    await expect(page.getByRole("tab", { name: /^Werte/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(metabolic).toBeVisible();
    await page.goto(`${patientPath}#vb-domain-cardiovascular`);
    await expect(page.getByRole("tab", { name: /^Werte/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await expect(
      page.getByRole("region", { name: "Kardiovaskulär", exact: true }),
    ).toBeVisible();
    await page.goto(`${patientPath}#akte`);
    await expect(page.getByRole("tab", { name: /^Akte/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});

test("the owner states a baseline and a follow-up, and the figure stands on both pages", async ({
  browser,
}) => {
  await asStaff(browser, "owner", async (page) => {
    // Two statements through the form: 60 minutes before the platform, 24 now. Statements
    // are append-only; the newest of each kind stands, so a run after this one is told the
    // same figure.
    for (const [kind, minutes] of [
      ["Ausgangswert", "60"],
      ["Folgeangabe", "24"],
    ] as const) {
      await page.goto("/einstellungen/vorbereitungszeit");
      const kindOf = page.getByRole("combobox", { name: "Art der Angabe" });
      await hydrated(kindOf);
      await kindOf.selectOption({ label: kind });
      await page
        .getByRole("spinbutton", { name: "Median je Termin (Minuten)" })
        .fill(minutes);
      await page.getByRole("button", { name: "Angabe speichern" }).click();
      await expect(page.getByRole("status")).toHaveText(
        "Die Angabe wurde gespeichert.",
      );
    }
    const main = page.getByRole("main");
    await expect(main).toContainText("Veränderung gegenüber dem Ausgangswert");
    await expect(main).toContainText("−60 %");
    await expect(main).toContainText(
      "60 → 24 Minuten je Termin, beide Angaben der Praxis.",
    );
    await expect(main).toContainText(
      "Das Pilotkriterium von mindestens −50 % ist nach diesen Angaben erreicht.",
    );

    // The overview's practice card leads with it.
    await page.goto("/overview");
    const practice = page.getByRole("region", { name: /^Praxis · \d+ Tage$/ });
    await expect(practice).toContainText("Vorbereitungszeit je Termin");
    await expect(practice).toContainText("−60 %");
    await expect(practice).toContainText(
      "Letzte Folgeangabe gegenüber dem Ausgangswert (60 → 24 min, Angaben der Praxis) · Pilotkriterium: mindestens −50 %",
    );
  });
});
