import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listMembers, listStaffInvitations, me } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { MitgliederContent } from "./MitgliederContent";

// Owner-only staff administration (real-data path): the API gates every staff-invite endpoint
// to owners server-side (STAFF_INVITE_CREATE). This page mirrors that with a deny-by-default
// load — non-owners never reach the management surface — but the server authorization is the
// control, not this UI check. The page follows the interface language (lib/i18n).
export const dynamic = "force-dynamic";

export default async function MitgliederPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const title = messages.settings.members.title;
  const parent = { label: messages.settings.title, href: "/einstellungen" };

  if (session.role !== "owner") {
    return (
      <VitaShell
        nav="einstellungen"
        crumb={title}
        crumbParent={parent}
        identity={identity}
      >
        <div style={{ maxWidth: "620px" }}>
          <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>{title}</h1>
          <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
            {messages.membersPage.ownersOnly}
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
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={parent}
      identity={identity}
    >
      <MitgliederContent
        members={members}
        invitations={invitations}
        selfUserId={session.user.id}
      />
    </VitaShell>
  );
}
