import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listDeletionRequests, me } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { LoeschantraegeContent } from "./LoeschantraegeContent";
import { SettingsFrame } from "../SettingsFrame";

// Owner + medical-director erasure-request queue (real-data path). The API gates the list
// endpoint to those two roles server-side (PRIVACY_REQUEST_LIST); this page mirrors that with
// a deny-by-default load — other roles never reach the surface — but the API is the control.
// The page follows the interface language (lib/i18n).
export const dynamic = "force-dynamic";

const ALLOWED = new Set(["owner", "medical_director"]);

export default async function LoeschantraegePage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const title = messages.settings.deletionRequests.title;
  const parent = { label: messages.settings.title, href: "/einstellungen" };

  const role = session.role ?? "";
  if (!ALLOWED.has(role)) {
    return (
      <VitaShell
        nav="einstellungen"
        crumb={title}
        crumbParent={parent}
        identity={identity}
      >
        <SettingsFrame
          role={session.role}
          current="deletionRequests"
          messages={messages}
        >
          <div style={{ maxWidth: "620px" }}>
            <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>{title}</h1>
            <p
              style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}
            >
              {messages.deletionRequestsPage.reserved}
            </p>
          </div>
        </SettingsFrame>
      </VitaShell>
    );
  }

  let requests;
  try {
    requests = await listDeletionRequests();
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
      <SettingsFrame
        role={session.role}
        current="deletionRequests"
        messages={messages}
      >
        <LoeschantraegeContent
          requests={requests}
          role={role}
          selfUserId={session.user.id}
        />
      </SettingsFrame>
    </VitaShell>
  );
}
