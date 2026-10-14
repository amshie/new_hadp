import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, me, preparation, type Preparation } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { PracticePrepContent } from "./PracticePrepContent";

// The practice view (docs/notes/0023): the page before a visit for every record of the
// clinic at once, over the governed path (authenticated principal + active tenant via the
// session cookie, RLS, one audited read). Deny-by-default: a refused read goes to the sign-in.
export default async function PracticePrepPage() {
  let data: Preparation;
  try {
    data = await preparation();
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  const identity = shellIdentity(session);
  return (
    <VitaShell
      nav="patienten"
      crumb={messages.practicePrep.title}
      crumbParent={{ label: messages.patients.title, href: "/patients" }}
      identity={identity}
    >
      <PracticePrepContent
        data={data}
        tenantName={identity?.tenantName ?? "—"}
      />
    </VitaShell>
  );
}
