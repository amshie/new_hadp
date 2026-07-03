import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, me, reviewQueue, type ReviewQueueItem } from "@/lib/api";

import { ReviewQueueContent } from "./ReviewQueueContent";

// Review-Queue (Phase 1C): tenant-scoped open review items over the governed path —
// server load, authenticated principal + active tenant, deny-by-default (401/403 →
// /login). Resolution is clinician-only; the API enforces it (hiding is UX only).
async function load(): Promise<{
  items: ReviewQueueItem[];
  role: string | null;
}> {
  try {
    const [items, session] = await Promise.all([
      reviewQueue(),
      me().catch(() => null),
    ]);
    return { items, role: session?.role ?? null };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      redirect("/login");
    }
    throw e;
  }
}

export default async function ReviewQueuePage() {
  const { items, role } = await load();
  return (
    <VitaShell nav="review" crumb="Review-Queue">
      <ReviewQueueContent
        items={items}
        sessionRole={role}
        path="/review-queue"
      />
    </VitaShell>
  );
}
