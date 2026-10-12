import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { ApiError, listAuditEvents, me, type AuditPage } from "@/lib/api";
import { AUDIT_CATEGORIES } from "@/lib/auditCopy";
import { shellIdentity } from "@/lib/identity";
import { isUuid } from "@/lib/uuid";

import { AuditContent, type AuditQuery } from "./AuditContent";

// The clinic's audit trail (owner-only): who did what, and when. The API authorizes the read
// (AUDIT_READ) and returns exactly this clinic's events; this page mirrors the role check with
// a deny-by-default load. Filters and the paging position live in the URL, so a view can be
// reloaded and handed on. Every query parameter is validated before it reaches the API.
export const dynamic = "force-dynamic";

const CATEGORY_KEYS = new Set(AUDIT_CATEGORIES.map((c) => c.key));

function instant(value: string | undefined): string | undefined {
  if (!value || value.length > 40) return undefined;
  const at = new Date(value);
  return Number.isNaN(at.getTime()) ? undefined : at.toISOString();
}

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export default async function AuditPageRoute({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);

  const shell = (children: React.ReactNode) => (
    <VitaShell
      nav="einstellungen"
      crumb="Audit-Protokoll"
      crumbParent={{ label: "Einstellungen", href: "/einstellungen" }}
      identity={identity}
    >
      {children}
    </VitaShell>
  );

  if (session.role !== "owner") {
    return shell(
      <div style={{ maxWidth: "620px" }}>
        <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>
          Audit-Protokoll
        </h1>
        <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
          Das Audit-Protokoll ist nur für Inhaber verfügbar.
        </p>
      </div>,
    );
  }

  const raw = await searchParams;
  const category = one(raw.category);
  const target = one(raw.target);
  const cursor = one(raw.cursor);
  const query: AuditQuery = {
    category: category && CATEGORY_KEYS.has(category) ? category : undefined,
    target: target && isUuid(target) ? target : undefined,
    since: instant(one(raw.since)),
    until: instant(one(raw.until)),
    reads: one(raw.reads) === "1",
  };

  let page: AuditPage;
  let stalePosition = false;
  try {
    page = await listAuditEvents({
      category: query.category,
      target_id: query.target,
      since: query.since,
      until: query.until,
      exclude_reads: !query.reads,
      cursor: cursor && cursor.length <= 200 ? cursor : undefined,
    });
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    // A position that is not one (a damaged link): show the newest entries instead.
    if (!(e instanceof ApiError && e.status === 422 && cursor)) throw e;
    stalePosition = true;
    page = await listAuditEvents({
      category: query.category,
      target_id: query.target,
      since: query.since,
      until: query.until,
      exclude_reads: !query.reads,
    });
  }

  return shell(
    <AuditContent
      page={page}
      query={query}
      continued={Boolean(cursor) && !stalePosition}
      stalePosition={stalePosition}
    />,
  );
}
