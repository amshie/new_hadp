import { VitaShell } from "@/components/vitabahn/VitaShell";

import { OverviewContent } from "./OverviewContent";

// VitaBahn Übersicht (ADR-0005). Synthetic Alpha dashboard.
export default function OverviewPage() {
  return (
    <VitaShell nav="uebersicht" crumb="Übersicht">
      <OverviewContent />
    </VitaShell>
  );
}
