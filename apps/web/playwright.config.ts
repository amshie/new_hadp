import { defineConfig, devices } from "@playwright/test";

// Browser tests of the clinic workflow, through the UI alone, on synthetic data.
//
// No `webServer`: the suite runs against servers that are already up — `make dev` locally
// (API on :8000, web on :3000, a seeded dev database), the production build in CI. It never
// starts, seeds or resets anything, and it leaves the synthetic records it creates in place.
//
// One worker, no retries: the scenario is one patient walking through the clinic, and a
// step that only passes the second time is a finding, not noise. Sign-in is rate limited
// (10 per minute per client address), which is the other reason nothing runs in parallel.
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  // Generous for a dev server, which compiles a route on its first request; a production
  // build needs a fraction of it.
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : [["list"]],
  use: {
    // 127.0.0.1, not localhost: the session cookies are host-only, and the access link the
    // API issues for a released report names this host.
    baseURL: process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000",
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    actionTimeout: 20_000,
    navigationTimeout: 60_000,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
