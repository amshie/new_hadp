"use server";

import { redirect } from "next/navigation";

import { devLogin, logout, selectTenant } from "@/lib/api";

export type LoginResult = { ok: false; error: string };

// Wires the prototype's sign-in to the real API: dev-login (sets the session cookie) +
// auto-select the first authorized tenant, then continue to the overview. On failure we do
// NOT proceed — a silently-failed login must never present a logged-in shell that then 401s.
// Returns an error on failure; on success it redirects (and never returns).
export async function login(email: string): Promise<LoginResult> {
  try {
    const res = await devLogin(email);
    const first = res.tenants[0];
    if (!first) {
      return { ok: false, error: "Kein Mandant für dieses Konto verfügbar." };
    }
    await selectTenant(first.tenant_id);
  } catch {
    return {
      ok: false,
      error: "Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
    };
  }
  redirect("/overview"); // throws NEXT_REDIRECT on success — must stay outside the try
}

// Ends the session: revokes it server-side and clears the cookie (lib/api.logout). A failed
// revoke (API unreachable, session already expired) must still sign the user out locally —
// logout() clears the cookie in its finally block, so we swallow the error and continue.
export async function signOut(): Promise<void> {
  try {
    await logout();
  } catch {
    /* cookie already cleared; proceed to login */
  }
  redirect("/login"); // NEXT_REDIRECT — must stay outside the try
}
