import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listPatients, worklist } from "@/lib/api";
import { presentOverview, type OverviewView } from "@/lib/presenters/dashboard";

import { OverviewContent } from "./OverviewContent";

// VitaBahn Übersicht (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API (authenticated principal + active tenant via the session cookie + RLS),
// deny-by-default — ApiError 401/403 → /login.
async function loadView(): Promise<OverviewView> {
  try {
    const [rows, patients] = await Promise.all([worklist(), listPatients()]);
    return presentOverview(rows, patients);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function OverviewPage() {
  const view = await loadView();
  return (
    <VitaShell nav="uebersicht" crumb="Übersicht">
      <OverviewContent view={view} />
    </VitaShell>
  );
}
