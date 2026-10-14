import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { me, mySessions } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { getLocale, getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { SettingsFrame } from "../SettingsFrame";

import { EndOthers } from "./EndOthers";

// Sicherheit & Sitzungen (docs/notes/0016, part 3): how the reader signs in, their latest
// sessions, and ending every other one. Every signed-in role, about their own account only.
// The second factor belongs to the clinic's sign-in service; this page says which sign-in is
// in use and claims nothing about a factor it cannot see.
export const dynamic = "force-dynamic";

export default async function SicherheitPage() {
  const [session, messages, locale] = await Promise.all([
    me().catch(() => null),
    getMessages(),
    getLocale(),
  ]);
  if (!session) redirect("/login");
  const sessions = await mySessions().catch(() => null);
  const t = messages.securityPage;
  const title = messages.settings.security.title;
  const oidc = sessions?.sign_in === "oidc";
  const others =
    sessions?.sessions.filter((s) => s.state === "active" && !s.current)
      .length ?? 0;

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame role={session.role} current="security" messages={messages}>
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.personal}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <section className="vb-ov-card" aria-labelledby="security-signin">
          <div className="vb-ov-head">
            <h2 id="security-signin" className="vb-ov-h2">
              {t.signIn.title}
            </h2>
          </div>
          <div className="vb-ov-body">
            <dl className="vb-set-dl">
              <div className="vb-set-row">
                <dt className="vb-set-k">
                  <b>{t.signIn.method}</b>
                </dt>
                <dd>
                  {sessions ? (oidc ? t.signIn.oidc : t.signIn.dev) : "—"}
                </dd>
              </div>
              <div className="vb-set-row">
                <dt className="vb-set-k">
                  <b>{t.signIn.mfa}</b>
                </dt>
                <dd>
                  {sessions ? (oidc ? t.signIn.mfaOidc : t.signIn.mfaDev) : "—"}
                </dd>
              </div>
            </dl>
          </div>
        </section>
        <section
          className="vb-ov-card"
          aria-labelledby="security-sessions"
          style={{ marginTop: "16px" }}
        >
          <div className="vb-ov-head">
            <div>
              <h2 id="security-sessions" className="vb-ov-h2">
                {t.sessions.title}
              </h2>
              <p className="vb-ov-note">{t.sessions.note}</p>
            </div>
          </div>
          <div className="vb-ov-body">
            {sessions == null ? (
              <p className="vb-ov-unavailable">{t.sessions.unavailable}</p>
            ) : (
              <>
                <div style={{ overflowX: "auto" }}>
                  <table className="vb-ov-table">
                    <caption className="sr-only">{t.sessions.caption}</caption>
                    <thead>
                      <tr>
                        <th scope="col">{t.sessions.columns.started}</th>
                        <th scope="col">{t.sessions.columns.state}</th>
                        <th scope="col">{t.sessions.columns.until}</th>
                        <th scope="col">{t.sessions.columns.clinic}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.sessions.map((s) => (
                        <tr key={s.id}>
                          <td>{dateTime(s.started_at, locale)}</td>
                          <td>
                            {t.sessions.states[s.state]}
                            {s.current && (
                              <span
                                className="vb-ov-tag"
                                style={{ marginLeft: 8 }}
                              >
                                {t.sessions.current}
                              </span>
                            )}
                          </td>
                          <td>
                            {dateTime(s.ended_at ?? s.expires_at, locale)}
                          </td>
                          <td>{s.clinic ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <EndOthers others={others} />
              </>
            )}
          </div>
        </section>
      </SettingsFrame>
    </VitaShell>
  );
}
