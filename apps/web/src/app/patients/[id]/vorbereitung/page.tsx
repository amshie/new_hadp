import { notFound, redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  coreCatalog,
  getPatient,
  interpretation,
  me,
  timeline,
} from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { presentDomainOverview } from "@/lib/presenters/domainOverview";
import { presentVisitPrep } from "@/lib/presenters/visitPrep";
import { isUuid } from "@/lib/uuid";

import { VisitPrepCard } from "../VisitPrepCard";

// The page before a visit, on its own and fit to print (docs/notes/0022): the same facts the
// patient page shows at its top, read over the same governed loads (authenticated principal,
// active tenant, RLS, every read audited by the API). A tombstoned record has nothing to
// prepare and goes back to its page.
export default async function VisitPrepPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!isUuid(id)) notFound();
  let patient;
  let points;
  let matrix;
  let catalog;
  try {
    [patient, points, matrix, catalog] = await Promise.all([
      getPatient(id),
      timeline(id),
      interpretation(id),
      coreCatalog(),
    ]);
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403) redirect("/login");
      if (e.status === 404) notFound();
    }
    throw e;
  }
  if (patient.erased === true) redirect(`/patients/${id}`);
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  const overview = presentDomainOverview(points, catalog, matrix);
  const prep = presentVisitPrep(overview);
  const t = messages.patientPage.visitPrep;
  const ref = patient.external_ref ?? "—";
  return (
    <VitaShell
      nav="patienten"
      crumb={t.title}
      crumbParent={{
        label: patient.display_name,
        href: `/patients/${id}`,
      }}
      identity={shellIdentity(session)}
    >
      <div className="vb-ov-pagehead" style={{ marginBottom: "18px" }}>
        <div style={{ minWidth: 0 }}>
          <span className="vb-ov-eyebrow">{ref}</span>
          <h1 className="vb-ov-h1">
            {fill(t.pageTitle, { name: patient.display_name })}
          </h1>
        </div>
      </div>
      <VisitPrepCard
        prep={prep}
        overview={overview}
        patientId={id}
        standalone
      />
    </VitaShell>
  );
}
