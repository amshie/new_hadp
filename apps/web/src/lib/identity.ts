import type { Me } from "@/lib/api";

// Session identity for the shells (Phase 1C): the real user, role, and clinic replace
// the prototype's hardcoded persona. Fallbacks are honest em-dashes, never a fake name.
export interface ShellIdentity {
  name: string;
  // The role as the API names it; the shell says it in the interface language.
  role: string | null;
  // German, for the surfaces that are not translated yet.
  roleLabel: string;
  tenantName: string;
}

const ROLE_LABELS: Record<string, string> = {
  owner: "Inhaber",
  clinician: "Clinician",
  assistant: "Assistenz",
  medical_director: "Ärztliche Leitung",
};

export function shellIdentity(session: Me | null): ShellIdentity | null {
  if (!session) return null;
  return {
    name: session.user.display_name,
    role: session.role ?? null,
    roleLabel:
      (session.role && ROLE_LABELS[session.role]) || session.role || "—",
    tenantName: session.active_tenant_name ?? "—",
  };
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
