import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, coverage, listPatients, worklist } from "@/lib/api";
import {
  presentCoverage,
  presentOverview,
  type CoverageView,
  type OverviewView,
} from "@/lib/presenters/dashboard";

import { OverviewContent } from "./OverviewContent";

// VitaBahn Übersicht (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API (authenticated principal + active tenant via the session cookie + RLS),
// deny-by-default — ApiError 401/403 → /login.
async function loadView(): Promise<{
  overview: OverviewView;
  coverage: CoverageView | null;
}> {
  try {
    // Coverage is a secondary tile — if its endpoint fails it must not blank the whole page; the
    // tile falls back to its gated state (cov = null). The worklist/patients loads gate the page.
    const [rows, patients, cov] = await Promise.all([
      worklist(),
      listPatients(),
      coverage().catch(() => null),
    ]);
    return {
      overview: presentOverview(rows, patients),
      coverage: cov ? presentCoverage(cov) : null,
    };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function OverviewPage() {
  const { overview, coverage: cov } = await loadView();
  return (
    <VitaShell nav="uebersicht" crumb="Übersicht">
      <OverviewContent view={overview} coverage={cov} />
    </VitaShell>
  );
}
