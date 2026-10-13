import type { Me } from "@/lib/api";

// Session identity for the shells (Phase 1C): the real user, role, and clinic replace
// the prototype's hardcoded persona. Fallbacks are honest em-dashes, never a fake name.
export interface ShellIdentity {
  name: string;
  // The role as the API names it; the shells say it in the interface language
  // (lib/i18n, `roles`).
  role: string | null;
  tenantName: string;
}

export function shellIdentity(session: Me | null): ShellIdentity | null {
  if (!session) return null;
  return {
    name: session.user.display_name,
    role: session.role ?? null,
    tenantName: session.active_tenant_name ?? "—",
  };
}

// The role in the interface language; a role the wording does not know, as the API names it.
export function roleName(
  roles: Record<string, string>,
  role: string | null | undefined,
): string {
  return (role && (roles[role] ?? role)) || "—";
}

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((p) => p[0] ?? "")
      .join("")
      .toUpperCase() || "–"
  );
}
