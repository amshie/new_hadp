import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  me,
  reviewQueue,
  type Me,
  type ReviewQueueItem,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { ReviewQueueContent } from "./ReviewQueueContent";

// Review-Queue (Phase 1C): tenant-scoped open review items over the governed path —
// server load, authenticated principal + active tenant, deny-by-default (401/403 →
// /login). Resolution is clinician-only; the API enforces it (hiding is UX only).
async function load(): Promise<{
  items: ReviewQueueItem[];
  session: Me | null;
}> {
  try {
    const [items, session] = await Promise.all([
      reviewQueue(),
      me().catch(() => null),
    ]);
    return { items, session };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      redirect("/login");
    }
    throw e;
  }
}

export default async function ReviewQueuePage() {
  const [{ items, session }, messages] = await Promise.all([
    load(),
    getMessages(),
  ]);
  return (
    <VitaShell
      nav="review"
      crumb={messages.reviewQueue.title}
      identity={shellIdentity(session)}
      translated
    >
      <ReviewQueueContent
        items={items}
        sessionRole={session?.role ?? null}
        path="/review-queue"
      />
    </VitaShell>
  );
}
