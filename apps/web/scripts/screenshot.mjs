// Render routes with Playwright at the prototype's widths for side-by-side comparison
// against previews/*.png. Usage: node scripts/screenshot.mjs '<json-array-of-shots>'
// shot = { url, width, height?, out, fullPage?, before? }  before = async steps via selectors
import { chromium } from "playwright";

const shots = JSON.parse(process.argv[2]);
const browser = await chromium.launch();
try {
  for (const s of shots) {
    const ctx = await browser.newContext({
      viewport: { width: s.width, height: s.height ?? 900 },
      deviceScaleFactor: 1,
    });
    const page = await ctx.newPage();
    await page.goto(s.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(500);
    if (s.click) {
      for (const sel of s.click) {
        await page.click(sel);
        await page.waitForTimeout(250);
      }
    }
    await page.screenshot({ path: s.out, fullPage: s.fullPage ?? true });
    console.log("shot", s.out);
    await ctx.close();
  }
} finally {
  await browser.close();
}
