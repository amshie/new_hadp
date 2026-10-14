// "Was eine Rolle darf" (Team & Rollen): the authorization matrix of the API, in words a
// clinic owner reads. Each line names a group of the matrix's actions; whether a role may do
// it comes from the API (GET /api/v1/roles), never from this file. The API's tests hold that
// every action of the matrix is in exactly one line and that the actions of a line are
// granted to the same roles (apps/api/tests/test_team_api.py) — so a line is never "partly".
//
// Relative imports only: the Playwright runner imports this module directly.

export const CAPABILITIES = [
  {
    key: "readRecords",
    actions: [
      "patient.read",
      "observation.read",
      "audit.read_own",
      "tenant_profile.read",
    ],
  },
  {
    key: "createRecords",
    actions: ["patient.create", "consent.record", "invitation.create"],
  },
  { key: "importValues", actions: ["document.upload", "import.run"] },
  { key: "draftReports", actions: ["report.draft", "report.edit"] },
  { key: "decideValues", actions: ["review.resolve"] },
  { key: "interpret", actions: ["interpretation.author"] },
  { key: "approve", actions: ["report.approve"] },
  { key: "redraft", actions: ["report.redraft"] },
  { key: "reject", actions: ["report.reject"] },
  { key: "release", actions: ["report.release"] },
  {
    key: "team",
    actions: [
      "staff_invite.create",
      "member.list",
      "member.role_change",
      "member.remove",
    ],
  },
  { key: "clinicProfile", actions: ["tenant_profile.edit"] },
  { key: "auditTrail", actions: ["audit.read"] },
  { key: "metric", actions: ["metric.read", "metric.record"] },
  { key: "export", actions: ["privacy.export"] },
  { key: "requestDeletion", actions: ["privacy_request.create"] },
  { key: "listDeletion", actions: ["privacy_request.list"] },
  { key: "decideDeletion", actions: ["privacy_request.decide"] },
  { key: "executeDeletion", actions: ["privacy_request.execute"] },
] as const;

export type CapabilityKey = (typeof CAPABILITIES)[number]["key"];

// The roles as the page lists them: from operating to governing.
export const MATRIX_ROLES = [
  "assistant",
  "clinician",
  "medical_director",
  "owner",
] as const;

export interface CapabilityRow {
  key: CapabilityKey;
  // Per role in MATRIX_ROLES order: may it do all of this line's actions.
  allowed: boolean[];
}

export function capabilityMatrix(
  permissions: { role: string; actions: string[] }[],
): CapabilityRow[] {
  const byRole = new Map(permissions.map((p) => [p.role, new Set(p.actions)]));
  return CAPABILITIES.map((c) => ({
    key: c.key,
    allowed: MATRIX_ROLES.map((role) => {
      const granted = byRole.get(role);
      return granted != null && c.actions.every((a) => granted.has(a));
    }),
  }));
}
