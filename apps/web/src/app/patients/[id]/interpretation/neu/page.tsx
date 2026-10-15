import { notFound, redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, getPatient, interpretation, me, timeline } from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { dayOf } from "@/lib/presenters/domainOverview";
import { isUuid } from "@/lib/uuid";

import {
  AuthorRunContent,
  type EvidenceOption,
  type PrefillDomain,
} from "./AuthorRunContent";

// Interpretation authoring (Phase 1C): the clinician authors a WHOLE run — six domain
// verdicts (CIS + Actionability as two separate closed choices) plus three verdict-free
// tri-state cells each, every determinate cell backed by the patient's own PUBLISHED
// observations. The engine validates and records; it never derives. Clinician-only
// (server-enforced; this page also refuses to render the form for other roles).
export default async function AuthorRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!isUuid(id)) notFound();
  try {
    const [session, patient, matrix, points, messages] = await Promise.all([
      me().catch(() => null),
      getPatient(id),
      interpretation(id),
      timeline(id),
      getMessages(),
    ]);
    if (session?.role !== "clinician") redirect(`/patients/${id}`);

    // Evidence choices: the patient's PUBLISHED observations that no laboratory correction
    // has replaced (the service refuses anything else, fail-closed). Each names its sample day
    // as the clinic reads it, and a value the platform computed says so.
    const seen = new Set<string>();
    const evidenceOptions: EvidenceOption[] = points
      .filter((p) => p.review_status === "published")
      .filter(
        (p) => p.superseded_by_observation_id == null && !p.input_replaced,
      )
      .filter((p) =>
        seen.has(p.observation_id) ? false : (seen.add(p.observation_id), true),
      )
      .map((p) => ({
        id: p.observation_id,
        label: [
          p.original_name,
          dayOf(p.observed_at, p.observed_at_is_date_only),
          ...(p.derived ? [messages.patientPage.evidence.derived] : []),
        ].join(" · "),
      }));

    const prefill: PrefillDomain[] | null = matrix.run_id
      ? matrix.domains.map((d) => ({
          domain_axis: d.domain_axis,
          cis_status: d.cis_status,
          actionability_class: d.actionability_class,
          followup_adequacy: d.followup_adequacy,
          rationale: d.rationale ?? "",
          cells: d.cells.map((c) => ({
            tri_state_axis: c.tri_state_axis,
            state: c.state,
            endpoint_adequacy: c.endpoint_adequacy,
            // A replaced value is not carried into the new run: the cell then asks for
            // evidence again instead of silently keeping a corrected value.
            evidence: c.evidence
              .filter((e) => e.superseded !== true)
              .map((e) => e.observation_id),
            rationale: c.rationale ?? "",
          })),
        }))
      : null;

    return (
      <VitaShell
        nav="patienten"
        crumb={fill(messages.interpretation.crumb, {
          patient: patient.display_name,
        })}
        crumbParent={{ label: patient.display_name, href: `/patients/${id}` }}
        identity={shellIdentity(session)}
      >
        <AuthorRunContent
          patientId={id}
          runNumber={matrix.run_number}
          prefill={prefill}
          evidenceOptions={evidenceOptions}
        />
      </VitaShell>
    );
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.status === 401 || e.status === 403) redirect("/login");
      if (e.status === 404) notFound();
    }
    throw e;
  }
}
