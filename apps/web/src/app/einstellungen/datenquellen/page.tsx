import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { me, sources } from "@/lib/api";
import { ago } from "@/lib/format";
import { byCount, fill } from "@/lib/i18n/fill";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import { presentSources } from "@/lib/presenters/today";

import { SettingsFrame } from "../SettingsFrame";

// Datenquellen & Import (docs/notes/0016, part 3): the laboratory file readers this platform
// has, when each was last used in this clinic, and what happens to a value once it is read
// in. Read only — there is nothing a clinic configures here yet. Every staff role.
export const dynamic = "force-dynamic";

export default async function DatenquellenPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const lines = await sources().catch(() => null);
  const now = Date.now();
  const t = messages.sourcesPage;
  const names = messages.overview.sources.names;
  const title = messages.settings.dataSources.title;

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame
        role={session.role}
        current="dataSources"
        messages={messages}
      >
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.clinic}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <section className="vb-ov-card" aria-labelledby="sources-readers">
          <div className="vb-ov-head">
            <div>
              <h2 id="sources-readers" className="vb-ov-h2">
                {t.readers}
              </h2>
              <p className="vb-ov-note">{t.readersNote}</p>
            </div>
          </div>
          <div className="vb-ov-body">
            {lines == null ? (
              <p className="vb-ov-unavailable">{t.unavailable}</p>
            ) : (
              <ul className="vb-ov-srclist">
                {presentSources(lines).map((src) => (
                  <li key={src.parserName ?? "other"}>
                    <div>
                      <b>
                        {src.key === "other" && src.parserName
                          ? src.parserName
                          : names[src.key]}
                      </b>
                      <small>{t.what[src.key]}</small>
                      <small>
                        {src.lastImportAt
                          ? [
                              fill(t.last, {
                                when: ago(
                                  src.lastImportAt,
                                  now,
                                  messages.dashboard.time,
                                ),
                              }),
                              byCount(t.jobs, src.jobs),
                              byCount(t.rows, src.rows),
                            ].join(" · ")
                          : t.never}
                      </small>
                    </div>
                    <span className="vb-ov-tag">
                      {src.jobs > 0
                        ? messages.overview.sources.state.used
                        : messages.overview.sources.state.ready}
                    </span>
                  </li>
                ))}
                <li>
                  <div>
                    <b>{t.wearables}</b>
                    <small>{t.wearablesNote}</small>
                  </div>
                  <span className="vb-ov-tag">
                    {messages.overview.sources.state.none}
                  </span>
                </li>
              </ul>
            )}
            <p className="vb-ov-note">{t.pdf}</p>
          </div>
        </section>
        <section
          className="vb-ov-card"
          aria-labelledby="sources-after"
          style={{ marginTop: "16px" }}
        >
          <div className="vb-ov-head">
            <h2 id="sources-after" className="vb-ov-h2">
              {t.after}
            </h2>
          </div>
          <div className="vb-ov-body">
            <ol className="vb-steps">
              <li>{t.steps.stored}</li>
              <li>{t.steps.published}</li>
              <li>{t.steps.review}</li>
              <li>{t.steps.original}</li>
            </ol>
          </div>
        </section>
      </SettingsFrame>
    </VitaShell>
  );
}
