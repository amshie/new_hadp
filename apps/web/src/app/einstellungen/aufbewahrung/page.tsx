import Link from "next/link";
import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { listDeletionRequests, me } from "@/lib/api";
import { fill } from "@/lib/i18n/fill";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { SettingsFrame } from "../SettingsFrame";

// Aufbewahrung & Export (docs/notes/0016, part 3): what the clinic has in place for retention,
// data export, deletion and restore — and, plainly, what it does not yet have. Owner only (the
// owner requests deletions and creates exports); the API authorizes each read.
export const dynamic = "force-dynamic";

export default async function AufbewahrungPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const owner = session.role === "owner";
  const deletions = owner
    ? await listDeletionRequests().catch(() => null)
    : null;
  const t = messages.retentionPage;
  const title = messages.settings.retention.title;
  const open =
    deletions?.filter((d) => d.status === "pending" || d.status === "approved")
      .length ?? 0;
  const executed =
    deletions?.filter((d) => d.status === "executed").length ?? 0;

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame
        role={session.role}
        current="retention"
        messages={messages}
      >
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.governance}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">
            {owner
              ? t.lead
              : fill(messages.settings.nav.locked, {
                  roles: messages.roles.owner,
                })}
          </p>
        </div>
        {owner && (
          <section className="vb-ov-card" aria-labelledby="retention-items">
            <div className="vb-ov-head">
              <h2 id="retention-items" className="vb-ov-h2">
                {title}
              </h2>
            </div>
            <div className="vb-ov-body">
              <dl className="vb-set-dl">
                <div className="vb-set-row">
                  <dt className="vb-set-k">
                    <b>{t.policy}</b>
                  </dt>
                  <dd>{t.policyNote}</dd>
                </div>
                <div className="vb-set-row">
                  <dt className="vb-set-k">
                    <b>{t.export}</b>
                  </dt>
                  <dd>{t.exportNote}</dd>
                </div>
                <div className="vb-set-row">
                  <dt className="vb-set-k">
                    <b>{t.deletion}</b>
                    <span>
                      {deletions
                        ? fill(t.deletionState, { open, executed })
                        : t.unavailable}
                    </span>
                  </dt>
                  <dd>
                    {t.deletionNote}{" "}
                    <Link href="/einstellungen/loeschantraege">
                      {t.deletionLink}
                    </Link>
                  </dd>
                </div>
                <div className="vb-set-row">
                  <dt className="vb-set-k">
                    <b>{t.backup}</b>
                  </dt>
                  <dd>{t.backupNote}</dd>
                </div>
              </dl>
            </div>
          </section>
        )}
      </SettingsFrame>
    </VitaShell>
  );
}
