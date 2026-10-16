import { notFound, redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  getIntakeBatch,
  me,
  type IntakeBatch,
  type Me,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { isUuid } from "@/lib/uuid";

import { IntakeBatchContent } from "./IntakeBatchContent";

// The confirmation screen of the lab intake agent: one proposal (one PDF), every value beside
// the page region it was read from, and the clinician's decision per value. Governed server
// load: authenticated principal + active tenant (401/403 → /login), deny-by-default, the API
// decides who may read and who may decide (intake.read / intake.decide).
async function load(
  batchId: string,
): Promise<{ batch: IntakeBatch; session: Me | null }> {
  try {
    const [batch, session] = await Promise.all([
      getIntakeBatch(batchId),
      me().catch(() => null),
    ]);
    return { batch, session };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}

export default async function IntakeBatchPage({
  params,
}: {
  params: Promise<{ batchId: string }>;
}) {
  const { batchId } = await params;
  if (!isUuid(batchId)) notFound();
  const [{ batch, session }, messages] = await Promise.all([
    load(batchId),
    getMessages(),
  ]);
  return (
    <VitaShell
      nav="patienten"
      crumb={messages.intakePage.crumb}
      crumbParent={{
        label: batch.patient_display_name,
        href: `/patients/${batch.patient_id}`,
      }}
      identity={shellIdentity(session)}
    >
      <IntakeBatchContent batch={batch} sessionRole={session?.role ?? null} />
    </VitaShell>
  );
}
