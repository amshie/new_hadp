import {
  expect,
  type Browser,
  type BrowserContext,
  type Locator,
  type Page,
} from "@playwright/test";

// Until React has hydrated a control it is only what the server rendered: a click on a button
// does nothing, and a form submits natively — the page reloads and what was entered is gone.
// A production build paints fast enough for a test (and for a quick hand) to get there first.
// React writes a `__reactProps$…` key onto an element while it hydrates it; this waits for
// that key on the control the next step is about to use. The key says that hydration has
// reached the element, not that every handler above it is attached — what makes the next
// action safe is that React hydrates synchronously on the click, key press or change that
// follows. Call it after every full page load.
export async function hydrated(control: Locator): Promise<void> {
  await expect
    .poll(
      () =>
        control.evaluate((element) =>
          Object.keys(element).some((key) => key.startsWith("__reactProps$")),
        ),
      { message: "the control was never taken over by React (not hydrated)" },
    )
    .toBe(true);
}

// The seeded synthetic accounts of the demo clinic, by the role the API gives them, with the
// role as the shell names it next to the signed-in person.
const STAFF = {
  assistant: { email: "assistant@demo.synthetic", roleLabel: "Assistenz" },
  clinician: { email: "clinician@demo.synthetic", roleLabel: "Clinician" },
  medicalDirector: {
    email: "medical.director@demo.synthetic",
    roleLabel: "Ärztliche Leitung",
  },
} as const;

export type StaffRole = keyof typeof STAFF;

type Session = Awaited<ReturnType<BrowserContext["storageState"]>>;

// One sign-in per role and run, made when the role is first needed. Sign-in is rate limited
// (10 per minute, apps/api auth_routes.py — per address the API sees, which is the web
// server's for every browser): every later step of the same role opens a new browser context
// from the session kept here. The suite itself keeps the sessions in memory only. A FAILED
// run is different: its trace (playwright.config.ts) holds the cookies and the access link,
// under test-results/, and CI uploads it — sessions of made-up accounts on a stack that is
// gone when the job ends.
const sessions = new Map<StaffRole, Session>();

// An uncaught error on a page — a hydration mismatch among them — fails no step by itself:
// the page renders again and every assertion passes. Each context is watched, and the step
// that used it fails if a page reported one.
export function watchPageErrors(context: BrowserContext): () => void {
  const errors: string[] = [];
  context.on("page", (page) => {
    page.on("pageerror", (error) => {
      errors.push(`${new URL(page.url()).pathname}: ${error.message}`);
    });
  });
  return () => {
    expect(errors, "uncaught errors on the pages of this step").toEqual([]);
  };
}

async function signIn(browser: Browser, role: StaffRole): Promise<Session> {
  const { email, roleLabel } = STAFF[role];
  const context = await browser.newContext();
  const noPageErrors = watchPageErrors(context);
  try {
    const page = await context.newPage();
    await page.goto("/login");
    const address = page.getByRole("textbox", { name: "E-Mail-Adresse" });
    await hydrated(address);
    await address.fill(email);
    // The form takes no submission — not by the Enter key either — until it is hydrated.
    await expect(page.getByRole("button", { name: "Anmelden" })).toBeEnabled();
    await address.press("Enter");
    await expect(
      page,
      `sign-in as ${email} did not reach /overview (the API refuses more than 10 sign-ins per minute)`,
    ).toHaveURL(/\/overview$/);
    await expect(page.getByRole("banner")).toContainText(roleLabel);
    noPageErrors();
    return await context.storageState();
  } finally {
    await context.close();
  }
}

// A page as it is BEFORE React has taken it over: the server's markup, with the framework's
// scripts kept from loading. (The inline scripts that reveal streamed content still run.)
export async function withoutPageScripts(
  context: BrowserContext,
): Promise<void> {
  await context.route(/\/_next\/static\/.*\.js(\?.*)?$/, (route) =>
    route.abort(),
  );
}

// Runs one piece of work as a member of the clinic's staff, in a browser context of its own.
// `unhydrated`: the pages of this context never hydrate (see withoutPageScripts).
export async function asStaff(
  browser: Browser,
  role: StaffRole,
  work: (page: Page) => Promise<void>,
  options: { unhydrated?: boolean } = {},
): Promise<void> {
  let session = sessions.get(role);
  if (!session) {
    session = await signIn(browser, role);
    sessions.set(role, session);
  }
  const context = await browser.newContext({ storageState: session });
  const noPageErrors = watchPageErrors(context);
  if (options.unhydrated) await withoutPageScripts(context);
  try {
    await work(await context.newPage());
    noPageErrors();
  } finally {
    await context.close();
  }
}
