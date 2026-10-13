import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  coverage,
  listPatients,
  me,
  throughput,
  worklist,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import {
  type DashboardWording,
  presentCoverage,
  presentOverview,
  presentThroughput,
  type CoverageView,
  type OverviewView,
  type ThroughputChartView,
} from "@/lib/presenters/dashboard";

import { OverviewContent } from "./OverviewContent";

// VitaBahn Übersicht (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API (authenticated principal + active tenant via the session cookie + RLS),
// deny-by-default — ApiError 401/403 → /login.
async function loadView(wording: DashboardWording): Promise<{
  overview: OverviewView;
  coverage: CoverageView | null;
  throughput: ThroughputChartView | null;
}> {
  try {
    // Coverage + throughput are secondary tiles — if either endpoint fails it must not blank the
    // whole page; the tile falls back to its gated state. The worklist/patients loads gate the page.
    const [rows, patients, cov, thru] = await Promise.all([
      worklist(),
      listPatients(),
      coverage().catch(() => null),
      throughput(30).catch(() => null),
    ]);
    return {
      overview: presentOverview(rows, patients, wording),
      coverage: cov ? presentCoverage(cov, wording) : null,
      throughput: thru ? presentThroughput(thru) : null,
    };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function OverviewPage() {
  const messages = await getMessages();
  const [{ overview, coverage: cov, throughput: thru }, session] =
    await Promise.all([loadView(messages.dashboard), me().catch(() => null)]);
  return (
    <VitaShell
      nav="uebersicht"
      crumb={messages.overview.title}
      identity={shellIdentity(session)}
    >
      <OverviewContent view={overview} coverage={cov} throughput={thru} />
    </VitaShell>
  );
}
