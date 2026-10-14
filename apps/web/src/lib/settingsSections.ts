// The sections of Einstellungen, in the order the sub-navigation lists them, and who may open
// each. Navigation only: every page and every API route authorizes on its own, server-side.
// A section the reader's role may not open is listed as locked, not hidden — so a colleague
// knows it exists and whom to ask.

export type SettingsGroup = "personal" | "clinic" | "governance";

export type SettingsKey =
  | "profile"
  | "appearance"
  | "security"
  | "clinicProfile"
  | "members"
  | "dataSources"
  | "preparationTime"
  | "deletionRequests"
  | "auditTrail"
  | "consentTexts"
  | "retention";

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
  {
    key: "profile",
    group: "personal",
    href: "/einstellungen/profil",
    roles: null,
  },
  { key: "appearance", group: "personal", href: "/einstellungen", roles: null },
  {
    key: "security",
    group: "personal",
    href: "/einstellungen/sicherheit",
    roles: null,
  },
  {
    key: "clinicProfile",
    group: "clinic",
    href: "/einstellungen/praxis",
    roles: null,
  },
  {
    key: "members",
    group: "clinic",
    href: "/einstellungen/mitglieder",
    roles: ["owner"],
  },
  {
    key: "dataSources",
    group: "clinic",
    href: "/einstellungen/datenquellen",
    roles: null,
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
  {
    key: "consentTexts",
    group: "governance",
    href: "/einstellungen/einwilligungen",
    roles: null,
  },
  {
    key: "retention",
    group: "governance",
    href: "/einstellungen/aufbewahrung",
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
