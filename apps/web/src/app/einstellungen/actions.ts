"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { isLocale, LOCALE_COOKIE } from "@/lib/i18n/locales";

// The person's choice of interface language, kept on this device for a year. Nothing but
// one of the offered languages is stored; anything else leaves the choice as it was. It is a
// preference, not an access right — no session is asked for, and nothing is recorded.
export async function setLocale(formData: FormData): Promise<void> {
  const chosen = formData.get("locale");
  if (isLocale(chosen)) {
    (await cookies()).set(LOCALE_COOKIE, chosen, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  }
  redirect("/einstellungen"); // NEXT_REDIRECT — the page is rendered again in the language
}
