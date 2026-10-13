import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listPatients, me, worklist } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import {
  type DashboardWording,
  presentDirectory,
  type DirectoryView,
} from "@/lib/presenters/dashboard";

import { PatientsContent } from "./PatientsContent";

// VitaBahn Patienten directory (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API (authenticated principal + active tenant via the session cookie + RLS),
// deny-by-default — ApiError 401/403 → /login.
async function loadView(wording: DashboardWording): Promise<DirectoryView> {
  try {
    const [patients, rows] = await Promise.all([listPatients(), worklist()]);
    return presentDirectory(patients, rows, wording);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function PatientsPage() {
  const messages = await getMessages();
  const [view, session] = await Promise.all([
    loadView(messages.dashboard),
    me().catch(() => null),
  ]);
  const identity = shellIdentity(session);
  return (
    <VitaShell
      nav="patienten"
      crumb={messages.patients.title}
      identity={identity}
      translated
    >
      <PatientsContent view={view} tenantName={identity?.tenantName ?? "—"} />
    </VitaShell>
  );
}
