import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listKpiConfig, me } from "@/lib/api";
import { shellIdentity } from "@/lib/identity";

import { KpiConfigContent } from "./KpiConfigContent";

// Owner-only KPI configuration: choose which of the global, read-only KPI catalog entries are
// active and visible FOR THIS CLINIC. The API gates KPI_CONFIG_READ/WRITE to owners server-side;
// this deny-by-default load mirrors that, but the server authorization is the control, not this
// UI check. The global catalog is never mutated — only this tenant's override rows.
export const dynamic = "force-dynamic";

export default async function KpiConfigPage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);

  if (session.role !== "owner") {
    return (
      <VitaShell
        nav="einstellungen"
        crumb="Kennzahlen"
        crumbParent={{ label: "Einstellungen", href: "/einstellungen" }}
        identity={identity}
      >
        <div style={{ maxWidth: "620px" }}>
          <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>Kennzahlen</h1>
          <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
            Die Kennzahlen-Konfiguration ist nur für Inhaber verfügbar.
          </p>
        </div>
      </VitaShell>
    );
  }

  let rows;
  try {
    rows = await listKpiConfig();
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }

  return (
    <VitaShell
      nav="einstellungen"
      crumb="Kennzahlen"
      crumbParent={{ label: "Einstellungen", href: "/einstellungen" }}
      identity={identity}
    >
      <KpiConfigContent rows={rows} />
    </VitaShell>
  );
}
