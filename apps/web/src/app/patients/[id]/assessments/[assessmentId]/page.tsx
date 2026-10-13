import { notFound, redirect } from "next/navigation";

import { ToastProvider } from "@/components/Toaster";
import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  getPatient,
  getReport,
  interpretation,
  me,
  timeline,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { presentReview, type ReviewView } from "@/lib/presenters/review";
import { isUuid } from "@/lib/uuid";

import { ReviewContent } from "./ReviewContent";

async function loadView(
  patientId: string,
  reportId: string,
): Promise<ReviewView> {
  try {
    const [patient, report, points, matrix] = await Promise.all([
      getPatient(patientId),
      getReport(reportId),
      timeline(patientId),
      interpretation(patientId),
    ]);
    return presentReview(patient, report, points, matrix);
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403) redirect("/login");
      if (e.status === 404) notFound();
    }
    throw e;
  }
}

export default async function AssessmentReviewPage({
  params,
}: {
  params: Promise<{ id: string; assessmentId: string }>;
}) {
  const { id, assessmentId } = await params;
  if (!isUuid(id) || !isUuid(assessmentId)) notFound();

  // The session role drives which Freigabe actions render (the API enforces them).
  const [view, session, messages] = await Promise.all([
    loadView(id, assessmentId),
    me().catch(() => null),
    getMessages(),
  ]);

  // The dashboard shell, as every other workspace page, in the interface language (ADR-0007);
  // the closed vocabularies on the page stay German and say so. The page reports what its
  // actions answer — an error among them — through the toast provider.
  return (
    <VitaShell
      nav="patienten"
      crumb={messages.reportPage.crumb}
      crumbParent={{ label: view.patientName, href: `/patients/${id}` }}
      identity={shellIdentity(session)}
      translated
    >
      <ToastProvider>
        <ReviewContent
          view={view}
          sessionRole={session?.role ?? null}
          path={`/patients/${id}/assessments/${assessmentId}`}
        />
      </ToastProvider>
    </VitaShell>
  );
}
