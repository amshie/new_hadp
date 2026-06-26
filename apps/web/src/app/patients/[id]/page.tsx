import { notFound } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { PATIENTS } from "@/lib/demo/dashboard";

import { PatientDetailContent } from "./PatientDetailContent";

// VitaBahn patient Detail (ADR-0005). Synthetic Alpha. The patient identity comes from
// the synthetic demo set. Demo IDs are MLX-#### (not UUIDs), so the sibling assessment
// route's isUuid() guard is intentionally NOT used here; instead the id is validated
// against the known synthetic set and an unknown id 404s rather than reflecting raw input.
export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const patient = PATIENTS.find((p) => p.id === id);
  if (!patient) notFound();
  return (
    <VitaShell
      nav="patienten"
      crumb={patient.name}
      crumbParent={{ label: "Patienten", href: "/patients" }}
    >
      <PatientDetailContent
        name={patient.name}
        id={patient.id}
        age={patient.age}
      />
    </VitaShell>
  );
}
