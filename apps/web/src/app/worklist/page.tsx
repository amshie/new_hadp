import { redirect } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { ApiError, worklist } from "@/lib/api";
import { presentWorklist, type WorklistView } from "@/lib/presenters/worklist";

import { WorklistContent } from "./WorklistContent";

async function loadRows(): Promise<WorklistView[]> {
  try {
    return presentWorklist(await worklist());
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function WorklistPage() {
  const rows = await loadRows();
  return (
    <AppShell
      active="overview"
      breadcrumbs={
        <div className="breadcrumbs" aria-label="Brotkrümelnavigation">
          <span>Arbeitsbereich</span>
          <span>/</span>
          <span>Übersicht</span>
        </div>
      }
    >
      <WorklistContent rows={rows} />
    </AppShell>
  );
}
