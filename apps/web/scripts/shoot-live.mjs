// Logs in through the real UI (dev-login + 2FA), then screenshots worklist + review on
// real API data at desktop (1440) and mobile (390). Output → .shots/*-live.png
import { chromium } from "playwright";

const BASE = "http://127.0.0.1:3000";

async function run(width, height, suffix) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  // --- login flow ---
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill("#password", "demo-password-1234");
  await page.click('button:has-text("Weiter zur Bestätigung")');
  await page.waitForTimeout(300);
  const code = await page.$$(".code-inputs input");
  for (const input of code) await input.type("1");
  await page.click('button:has-text("Bestätigen und anmelden")');
  await page.waitForURL("**/worklist", { timeout: 15000 });
  await page.waitForSelector(".worklist-table tbody tr", { timeout: 15000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `.shots/worklist-${suffix}.png`, fullPage: true });
  console.log(`shot worklist-${suffix}`);
  // --- into the review (click the first row) ---
  await page.click(".worklist-table tbody tr");
  await page.waitForURL("**/assessments/**", { timeout: 15000 });
  await page.waitForSelector(".patient-heading h1", { timeout: 15000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `.shots/review-${suffix}.png`, fullPage: true });
  console.log(`shot review-${suffix}`);
  await ctx.close();
}

const browser = await chromium.launch();
try {
  await run(1440, 1000, "live-desktop");
  await run(390, 900, "live-mobile");
} finally {
  await browser.close();
}
