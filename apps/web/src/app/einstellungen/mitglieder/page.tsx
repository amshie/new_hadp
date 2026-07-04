import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listMembers, listStaffInvitations, me } from "@/lib/api";
import { shellIdentity } from "@/lib/identity";

import { MitgliederContent } from "./MitgliederContent";

// Owner-only staff administration (real-data path): the API gates every staff-invite endpoint
// to owners server-side (STAFF_INVITE_CREATE). This page mirrors that with a deny-by-default
// load — non-owners never reach the management surface — but the server authorization is the
// control, not this UI check.
export const dynamic = "force-dynamic";

export default async function MitgliederPage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);

  if (session.role !== "owner") {
    return (
      <VitaShell nav="einstellungen" crumb="Mitglieder" identity={identity}>
        <div style={{ maxWidth: "620px" }}>
          <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>Mitglieder</h1>
          <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
            Die Mitgliederverwaltung ist nur für Inhaber verfügbar.
          </p>
        </div>
      </VitaShell>
    );
  }

  let members, invitations;
  try {
    [members, invitations] = await Promise.all([
      listMembers(),
      listStaffInvitations(),
    ]);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }

  return (
    <VitaShell nav="einstellungen" crumb="Mitglieder" identity={identity}>
      <MitgliederContent
        members={members}
        invitations={invitations}
        selfUserId={session.user.id}
      />
    </VitaShell>
  );
}
