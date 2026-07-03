// Shared between the patient-link cookie-exchange route handler and the patient-view page.
// The token is carried in an httpOnly cookie (set by /patient-view/oeffnen) so it never
// lands in the address bar, browser history, or a referrer header.
export const PV_COOKIE = "hadp_pv";

// tenant is a UUID and token is url-safe base64 — neither contains ":", so it is a safe delimiter.
export function encodePv(tenant: string, token: string): string {
  return `${tenant}:${token}`;
}

export function decodePv(
  value: string | undefined,
): { tenant: string; token: string } | null {
  if (!value) return null;
  const idx = value.indexOf(":");
  if (idx <= 0) return null;
  const tenant = value.slice(0, idx);
  const token = value.slice(idx + 1);
  if (!tenant || !token) return null;
  return { tenant, token };
}
