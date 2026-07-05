import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listDeletionRequests, me } from "@/lib/api";
import { shellIdentity } from "@/lib/identity";

import { LoeschantraegeContent } from "./LoeschantraegeContent";

// Owner + medical-director erasure-request queue (real-data path). The API gates the list
// endpoint to those two roles server-side (PRIVACY_REQUEST_LIST); this page mirrors that with
// a deny-by-default load — other roles never reach the surface — but the API is the control.
export const dynamic = "force-dynamic";

const ALLOWED = new Set(["owner", "medical_director"]);

export default async function LoeschantraegePage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);

  const role = session.role ?? "";
  if (!ALLOWED.has(role)) {
    return (
      <VitaShell nav="einstellungen" crumb="Löschanträge" identity={identity}>
        <div style={{ maxWidth: "620px" }}>
          <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>
            Löschanträge
          </h1>
          <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
            Die Verwaltung von Löschanträgen ist Inhabern und der Ärztlichen
            Leitung vorbehalten.
          </p>
        </div>
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
    <VitaShell nav="einstellungen" crumb="Löschanträge" identity={identity}>
      <LoeschantraegeContent
        requests={requests}
        role={role}
        selfUserId={session.user.id}
      />
    </VitaShell>
  );
}
