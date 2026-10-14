import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  listAuditEvents,
  me,
  type AuditFilters,
  type AuditPage,
} from "@/lib/api";
import { auditCategory } from "@/lib/auditCopy";
import { clinicDayStart } from "@/lib/clinicTime";
import { getLocale, getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { isUuid } from "@/lib/uuid";

import { AuditContent, type AuditQuery } from "./AuditContent";
import { SettingsFrame, sectionEyebrow } from "../SettingsFrame";

// The clinic's audit trail (owner-only): who did what, and when. The API authorizes the read
// (AUDIT_READ) and returns exactly this clinic's events; this page mirrors the role check with
// a deny-by-default load. Filters and the paging position live in the URL, so a view can be
// reloaded and handed on. Every query parameter is validated before it is used, and one that
// is not what it should be is no filter at all — the form then shows none, so what is shown as
// the selection is always what was asked of the API. The page follows the interface language
// (lib/i18n).
export const dynamic = "force-dynamic";

const CURSOR = /^[A-Za-z0-9_-]{1,200}$/;

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export default async function AuditPageRoute({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [session, messages, locale] = await Promise.all([
    me().catch(() => null),
    getMessages(),
    getLocale(),
  ]);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const t = messages.auditPage;
  const title = messages.settings.auditTrail.title;

  const shell = (children: React.ReactNode) => (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={identity}
    >
      <SettingsFrame
        role={session.role}
        current="auditTrail"
        messages={messages}
      >
        {children}
      </SettingsFrame>
    </VitaShell>
  );
  const notice = (text: string) =>
    shell(
      <div className="vb-set-head">
        <span className="vb-ov-eyebrow">
          {sectionEyebrow("auditTrail", messages)}
        </span>
        <h1 className="vb-ov-h1">{title}</h1>
        <p className="vb-ov-lead">{text}</p>
      </div>,
    );

  if (session.role !== "owner") return notice(t.ownersOnly);

  const raw = await searchParams;
  // "Von" / "Bis einschließlich" are calendar days on the clinic's wall clock; the window the
  // API is asked for runs from the start of the first to the start of the day after the last.
  const from = one(raw.from);
  const to = one(raw.to);
  const since = clinicDayStart(from);
  const until = clinicDayStart(to, 1);
  const target = one(raw.target);
  const actor = one(raw.actor);
  const position = one(raw.cursor);
  const cursor = position && CURSOR.test(position) ? position : undefined;
  const query: AuditQuery = {
    category: auditCategory(one(raw.category)),
    target: isUuid(target) ? target.toLowerCase() : undefined,
    actor: isUuid(actor) ? actor.toLowerCase() : undefined,
    from: since ? from : undefined,
    to: until ? to : undefined,
    hideReads: one(raw.reads) === "0",
  };
  const filters: AuditFilters = {
    category: query.category,
    target_id: query.target,
    actor_user_id: query.actor,
    since: since?.toISOString(),
    until: until?.toISOString(),
    exclude_reads: query.hideReads,
  };

  let page: AuditPage;
  // A position that is not one (a damaged link): the newest entries are shown instead.
  let stalePosition = Boolean(position) && !cursor;
  try {
    try {
      page = await listAuditEvents({ ...filters, cursor });
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 422 && cursor)) throw e;
      stalePosition = true;
      page = await listAuditEvents(filters);
    }
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    if (e instanceof ApiError && e.status === 429) return notice(t.tooMany);
    if (e instanceof ApiError && e.status === 503) return notice(t.unavailable);
    throw e;
  }

  return shell(
    <AuditContent
      page={page}
      query={query}
      continued={Boolean(cursor) && !stalePosition}
      stalePosition={stalePosition}
      t={t}
      title={title}
      eyebrow={sectionEyebrow("auditTrail", messages)}
      locale={locale}
    />,
  );
}
