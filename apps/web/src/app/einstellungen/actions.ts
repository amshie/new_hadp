"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { isLocale, LOCALE_COOKIE } from "@/lib/i18n/locales";

// The person's choice of interface language, kept on this device for a year. Nothing but
// one of the offered languages is stored; anything else leaves the choice as it was. It is a
// preference, not an access right — no session is asked for, and nothing is recorded. The
// cookie holds no secret and decides nothing but wording.
async function keep(formData: FormData): Promise<void> {
  const chosen = formData.get("locale");
  if (!isLocale(chosen)) return;
  (await cookies()).set(LOCALE_COOKIE, chosen, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
}

// Two actions, each with its own fixed way back: where the person is sent afterwards is
// never taken from the request.
export async function setLocale(formData: FormData): Promise<void> {
  await keep(formData);
  redirect("/einstellungen"); // NEXT_REDIRECT — the page is rendered again in the language
}

export async function setLocaleBeforeSignIn(formData: FormData): Promise<void> {
  await keep(formData);
  redirect("/login");
}
