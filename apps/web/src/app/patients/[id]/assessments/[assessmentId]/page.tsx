import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import {
  ApiError,
  getPatient,
  getReport,
  interpretation,
  me,
  timeline,
} from "@/lib/api";
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
  const [view, session] = await Promise.all([
    loadView(id, assessmentId),
    me().catch(() => null),
  ]);

  return (
    <AppShell
      active="patients"
      breadcrumbs={
        <nav className="breadcrumbs" aria-label="Brotkrümelnavigation">
          <Link href="/worklist">Arbeitsliste</Link>
          <span>/</span>
          <span>{view.patientName}</span>
        </nav>
      }
    >
      <ReviewContent
        view={view}
        sessionRole={session?.role ?? null}
        path={`/patients/${id}/assessments/${assessmentId}`}
      />
    </AppShell>
  );
}
