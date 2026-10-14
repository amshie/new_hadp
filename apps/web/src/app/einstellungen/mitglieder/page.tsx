import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  listMembers,
  listStaffInvitations,
  me,
  rolePermissions,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { MitgliederContent } from "./MitgliederContent";
import { SettingsFrame, sectionEyebrow } from "../SettingsFrame";

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
        <SettingsFrame
          role={session.role}
          current="members"
          messages={messages}
        >
          <div className="vb-set-head">
            <span className="vb-ov-eyebrow">
              {sectionEyebrow("members", messages)}
            </span>
            <h1 className="vb-ov-h1">{title}</h1>
            <p className="vb-ov-lead">{messages.membersPage.ownersOnly}</p>
          </div>
        </SettingsFrame>
      </VitaShell>
    );
  }

  let members, invitations, permissions;
  try {
    [members, invitations, permissions] = await Promise.all([
      listMembers(),
      listStaffInvitations(),
      // The matrix is a secondary card: if it cannot be read, the card says so.
      rolePermissions().catch(() => null),
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
      <SettingsFrame role={session.role} current="members" messages={messages}>
        <MitgliederContent
          members={members}
          invitations={invitations}
          permissions={permissions}
          selfUserId={session.user.id}
          now={Date.now()}
        />
      </SettingsFrame>
    </VitaShell>
  );
}
