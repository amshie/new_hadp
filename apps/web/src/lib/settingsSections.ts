// The sections of Einstellungen, in the order the sub-navigation lists them, and who may open
// each. Navigation only: every page and every API route authorizes on its own, server-side.
// A section the reader's role may not open is listed as locked, not hidden — so a colleague
// knows it exists and whom to ask.

export type SettingsGroup = "personal" | "clinic" | "governance";

export type SettingsKey =
  | "appearance"
  | "members"
  | "preparationTime"
  | "deletionRequests"
  | "auditTrail";

export interface SettingsSection {
  key: SettingsKey;
  group: SettingsGroup;
  href: string;
  // null: every signed-in role.
  roles: readonly string[] | null;
}

export const SETTINGS_GROUPS: readonly SettingsGroup[] = [
  "personal",
  "clinic",
  "governance",
];

export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
  { key: "appearance", group: "personal", href: "/einstellungen", roles: null },
  {
    key: "members",
    group: "clinic",
    href: "/einstellungen/mitglieder",
    roles: ["owner"],
  },
  {
    key: "preparationTime",
    group: "clinic",
    href: "/einstellungen/vorbereitungszeit",
    roles: ["owner"],
  },
  {
    key: "deletionRequests",
    group: "governance",
    href: "/einstellungen/loeschantraege",
    roles: ["owner", "medical_director"],
  },
  {
    key: "auditTrail",
    group: "governance",
    href: "/einstellungen/audit",
    roles: ["owner"],
  },
];

export function mayOpen(
  section: SettingsSection,
  role: string | null | undefined,
): boolean {
  return (
    section.roles == null || (role != null && section.roles.includes(role))
  );
}
