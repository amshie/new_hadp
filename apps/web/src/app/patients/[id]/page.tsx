import { notFound, redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  coreCatalog,
  getPatient,
  getReport,
  interpretation,
  listConsents,
  listDataExports,
  listDocuments,
  listIntakeBatches,
  me,
  timeline,
  worklist,
  type ConsentState,
  type DataExport,
  type IntakeBatchSummary,
  type ReportView,
  type SourceDocument,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { presentDetail, type DetailView } from "@/lib/presenters/patientDetail";
import { isUuid } from "@/lib/uuid";

import { PatientDetailContent } from "./PatientDetailContent";

// VitaBahn patient Detail (ADR-0006, real-data path): governed server load over the real
// tenant-scoped API — authenticated principal + active tenant (enforced by the API session
// cookie + RLS), deny-by-default, UUID-guarded. The patient's latest report is resolved via
// the worklist; a patient without a draft renders an early-lifecycle "Kein Entwurf" state.
async function loadView(patientId: string): Promise<{
  view: DetailView;
  documents: SourceDocument[];
  intakeBatches: IntakeBatchSummary[];
  consents: ConsentState[];
}> {
  try {
    const rows = await worklist();
    const row = rows.find((r) => r.patient_id === patientId);
    const reportId = row?.report_id ?? null;
    const [
      patient,
      points,
      matrix,
      catalog,
      documents,
      intakeBatches,
      consents,
      report,
    ] = await Promise.all([
      getPatient(patientId),
      timeline(patientId),
      interpretation(patientId),
      coreCatalog(),
      listDocuments(patientId),
      listIntakeBatches(patientId),
      listConsents(patientId),
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
    return {
      view: presentDetail(patient, resolved, points, matrix, catalog),
      documents,
      intakeBatches,
      consents,
    };
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
  // The session role drives which staff actions render (invite); the API enforces them.
  // The report draft + Freigabe workflow lives on the dedicated review page, not here.
  const [{ view, documents, intakeBatches, consents }, session, messages] =
    await Promise.all([loadView(id), me().catch(() => null), getMessages()]);
  // The export list is the owner's (the API refuses every other role), and a tombstoned
  // record has none. A failed read must not take the patient page down with it.
  const dataExports: DataExport[] | null =
    session?.role === "owner" && !view.erased
      ? await listDataExports(id).catch(() => null)
      : null;
  return (
    <VitaShell
      nav="patienten"
      crumb={view.review.patientName}
      crumbParent={{ label: messages.patients.title, href: "/patients" }}
      identity={shellIdentity(session)}
    >
      <PatientDetailContent
        view={view}
        documents={documents}
        intakeBatches={intakeBatches}
        consents={consents}
        dataExports={dataExports}
        sessionRole={session?.role ?? null}
      />
    </VitaShell>
  );
}
