import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  type AuditEvent,
  coverage,
  type Coverage,
  type DeletionRequestView,
  getPreparationTime,
  listAuditEvents,
  listDeletionRequests,
  listStaffInvitations,
  me,
  type Me,
  ownActivity,
  type PreparationTime,
  type Source,
  sources,
  type StaffInvitationListItem,
  throughput,
  type Throughput,
  worklist,
  type WorklistRow,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { presentOverview, type OverviewView } from "@/lib/presenters/dashboard";

import { OverviewContent } from "./OverviewContent";

// Übersicht (docs/notes/0015): governed server load over the real tenant-scoped API
// (authenticated principal + active tenant via the session cookie + RLS), deny-by-default —
// ApiError 401/403 → /login.
//
// Each role loads only what it may read: a request the role may not make would be refused
// and recorded as a denied access in the clinic's trail. Everything but the work list is a
// secondary card: if its endpoint fails, that card says so and the page stands.

export interface OverviewData {
  role: string | null;
  // When the page was put together (ms since epoch): every "since" and "as of" on it is
  // measured from here, on the server and in the browser alike.
  now: number;
  rows: WorklistRow[];
  view: OverviewView;
  throughput: Throughput | null;
  coverage: Coverage | null;
  sources: Source[] | null;
  deletionRequests: DeletionRequestView[] | null;
  invitations: StaffInvitationListItem[] | null;
  preparation: PreparationTime | null;
  // The clinic's trail for the owner; one's own actions for everyone else.
  activity: AuditEvent[] | null;
  activityScope: "clinic" | "own";
}

const soft = <T,>(load: Promise<T>): Promise<T | null> =>
  load.catch(() => null);

async function load(): Promise<{ data: OverviewData; session: Me }> {
  const messages = await getMessages();
  try {
    const session = await me();
    const role = session.role ?? null;
    const owner = role === "owner";
    const governs = owner || role === "medical_director";
    const [rows, thru, cov, src, deletions, invitations, prep, activity] =
      await Promise.all([
        worklist(),
        soft(throughput(30)),
        soft(coverage()),
        soft(sources()),
        governs ? soft(listDeletionRequests()) : Promise.resolve(null),
        owner ? soft(listStaffInvitations()) : Promise.resolve(null),
        owner ? soft(getPreparationTime()) : Promise.resolve(null),
        owner
          ? soft(
              listAuditEvents({ limit: 25, exclude_reads: true }).then(
                (page) => page.items,
              ),
            )
          : soft(ownActivity(20)),
      ]);
    const data: OverviewData = {
      role,
      now: Date.now(),
      rows,
      view: presentOverview(rows, messages.dashboard),
      throughput: thru,
      coverage: cov,
      sources: src,
      deletionRequests: deletions,
      invitations,
      preparation: prep,
      activity,
      activityScope: owner ? "clinic" : "own",
    };
    return { data, session };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    throw e;
  }
}

export default async function OverviewPage() {
  const messages = await getMessages();
  const { data, session } = await load();
  return (
    <VitaShell
      nav="uebersicht"
      crumb={messages.overview.title}
      identity={shellIdentity(session)}
    >
      <OverviewContent data={data} />
    </VitaShell>
  );
}
