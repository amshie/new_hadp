import { notFound, redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  getPatient,
  getReport,
  interpretation,
  timeline,
  worklist,
  type ReportView,
} from "@/lib/api";
import { presentDetail, type DetailView } from "@/lib/presenters/patientDetail";
import { isUuid } from "@/lib/uuid";

import { PatientDetailContent } from "./PatientDetailContent";

// VitaBahn patient Detail (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API — authenticated principal + active tenant (enforced by the API session
// cookie + RLS), deny-by-default, UUID-guarded. The patient's latest report is resolved via
// the worklist; a patient without a draft renders an early-lifecycle "Kein Entwurf" state.
async function loadView(patientId: string): Promise<DetailView> {
  try {
    const rows = await worklist();
    const row = rows.find((r) => r.patient_id === patientId);
    const reportId = row?.report_id ?? null;
    const [patient, points, matrix, report] = await Promise.all([
      getPatient(patientId),
      timeline(patientId),
      interpretation(patientId),
      // A stale/RLS-filtered report id must not 404 the whole patient — fall through to the
      // no-report state. Only the patient/timeline/interpretation loads gate the page.
      reportId
        ? getReport(reportId).catch((e) => {
            if (e instanceof ApiError && e.status === 404) return null;
            throw e;
          })
        : Promise.resolve(null),
    ]);
    const resolved: ReportView = report ?? {
      report_id: "",
      patient_id: patientId,
      status: "none",
      version_no: 0,
      narrative_provider: "",
      narrative_version: "",
      statements: [],
    };
    return presentDetail(patient, resolved, points, matrix);
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403) redirect("/login");
      if (e.status === 404) notFound();
    }
    throw e;
  }
}

export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!isUuid(id)) notFound();
  const view = await loadView(id);
  return (
    <VitaShell
      nav="patienten"
      crumb={view.review.patientName}
      crumbParent={{ label: "Patienten", href: "/patients" }}
    >
      <PatientDetailContent view={view} />
    </VitaShell>
  );
}
