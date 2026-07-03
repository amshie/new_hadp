import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listPatients, me, worklist } from "@/lib/api";
import { shellIdentity } from "@/lib/identity";
import {
  presentDirectory,
  type DirectoryView,
} from "@/lib/presenters/dashboard";

import { PatientsContent } from "./PatientsContent";

// VitaBahn Patienten directory (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API (authenticated principal + active tenant via the session cookie + RLS),
// deny-by-default — ApiError 401/403 → /login.
async function loadView(): Promise<DirectoryView> {
  try {
    const [patients, rows] = await Promise.all([listPatients(), worklist()]);
    return presentDirectory(patients, rows);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function PatientsPage() {
  const [view, session] = await Promise.all([
    loadView(),
    me().catch(() => null),
  ]);
  const identity = shellIdentity(session);
  return (
    <VitaShell nav="patienten" crumb="Patienten" identity={identity}>
      <PatientsContent view={view} tenantName={identity?.tenantName ?? "—"} />
    </VitaShell>
  );
}
