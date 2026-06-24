// Logs in, opens the review screen, expands the "Metabolisch" domain card to reveal its
// biomarker evidence, and screenshots. Output → .shots/domain-detail-metabolic.png
import { chromium } from "playwright";

const BASE = "http://127.0.0.1:3000";
const browser = await chromium.launch();
try {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill("#password", "demo-password-1234");
  await page.click('button:has-text("Weiter zur Bestätigung")');
  await page.waitForTimeout(300);
  const code = await page.$$(".code-inputs input");
  for (const input of code) await input.type("1");
  await page.click('button:has-text("Bestätigen und anmelden")');
  await page.waitForURL("**/worklist", { timeout: 15000 });
  await page.waitForSelector(".worklist-table tbody tr", { timeout: 15000 });
  await page.click(".worklist-table tbody tr");
  await page.waitForURL("**/assessments/**", { timeout: 15000 });
  await page.getByText("Domänen-Interpretation").first().waitFor({ timeout: 15000 });
  await page
    .locator('article.card:has-text("Metabolisch") button')
    .first()
    .click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: ".shots/domain-detail-metabolic.png", fullPage: true });
  console.log("shot domain-detail-metabolic");
} finally {
  await browser.close();
}
