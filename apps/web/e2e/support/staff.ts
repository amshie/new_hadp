import {
  expect,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";

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
// (10 per minute per client address, apps/api auth_routes.py): every later step of the same
// role opens a new browser context from the session kept here. The sessions stay in memory —
// nothing that grants access is written to disk.
const sessions = new Map<StaffRole, Session>();

async function signIn(browser: Browser, role: StaffRole): Promise<Session> {
  const { email, roleLabel } = STAFF[role];
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    await page.goto("/login");
    const address = page.getByRole("textbox", { name: "E-Mail-Adresse" });
    await address.fill(email);
    await address.press("Enter");
    await expect(
      page,
      `sign-in as ${email} did not reach /overview (the API refuses more than 10 sign-ins per minute)`,
    ).toHaveURL(/\/overview$/);
    await expect(page.getByRole("banner")).toContainText(roleLabel);
    return await context.storageState();
  } finally {
    await context.close();
  }
}

// Runs one piece of work as a member of the clinic's staff, in a browser context of its own.
export async function asStaff(
  browser: Browser,
  role: StaffRole,
  work: (page: Page) => Promise<void>,
): Promise<void> {
  let session = sessions.get(role);
  if (!session) {
    session = await signIn(browser, role);
    sessions.set(role, session);
  }
  const context = await browser.newContext({ storageState: session });
  try {
    await work(await context.newPage());
  } finally {
    await context.close();
  }
}
