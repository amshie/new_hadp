import { VitaShell } from "@/components/vitabahn/VitaShell";

import { PatientsContent } from "./PatientsContent";

// VitaBahn Patienten directory (ADR-0005). Synthetic Alpha.
export default function PatientsPage() {
  return (
    <VitaShell nav="patienten" crumb="Patienten">
      <PatientsContent />
    </VitaShell>
  );
}
