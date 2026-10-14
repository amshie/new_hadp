import { redirect } from "next/navigation";

import { EmptyState } from "@/components/vitabahn/EmptyState";
import { VitaShell } from "@/components/vitabahn/VitaShell";
import { consentTexts, me } from "@/lib/api";
import { CONSENT_OPTIONS } from "@/lib/consentCopy";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { SettingsFrame } from "../SettingsFrame";

// Einwilligungstexte (docs/notes/0016, part 3): the consent purposes, the text version a
// consent recorded now refers to, and how many consents the clinic recorded under each
// version. Read only — a new wording arrives as a new version, never as an edit here. The
// wording of the purposes stays German, as recorded (ADR-0007). Every staff role.
export const dynamic = "force-dynamic";

export default async function EinwilligungenPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const texts = await consentTexts().catch(() => null);
  const t = messages.consentTextsPage;
  const title = messages.settings.consentTexts.title;
  const label = (purpose: string) =>
    CONSENT_OPTIONS.find((o) => o.purpose === purpose)?.label ?? purpose;

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame
        role={session.role}
        current="consentTexts"
        messages={messages}
      >
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.governance}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <section className="vb-ov-card" aria-labelledby="consent-current">
          <div className="vb-ov-head">
            <div>
              <h2 id="consent-current" className="vb-ov-h2">
                {t.current}
                {texts && (
                  <span className="vb-ov-mono" style={{ marginLeft: 10 }}>
                    {texts.current_version}
                  </span>
                )}
              </h2>
              <p className="vb-ov-note">{t.currentNote}</p>
            </div>
          </div>
          <div className="vb-ov-body">
            <h3 className="vb-ov-h4" style={{ marginTop: 0 }}>
              {t.purposes}
            </h3>
            <ul className="vb-ov-srclist" lang="de">
              {CONSENT_OPTIONS.map((o) => (
                <li key={o.purpose}>
                  <div>
                    <b>{o.label}</b>
                    <small>{o.desc}</small>
                  </div>
                </li>
              ))}
            </ul>
            <p className="vb-ov-note">{t.placeholder}</p>
          </div>
        </section>
        <section
          className="vb-ov-card"
          aria-labelledby="consent-counts"
          style={{ marginTop: "16px" }}
        >
          <div className="vb-ov-head">
            <h2 id="consent-counts" className="vb-ov-h2">
              {t.counts}
            </h2>
          </div>
          <div className="vb-ov-body" style={{ overflowX: "auto" }}>
            {texts == null ? (
              <p className="vb-ov-unavailable">{t.unavailable}</p>
            ) : texts.counts.length === 0 ? (
              <EmptyState quiet style={{ padding: 0 }}>
                {t.none}
              </EmptyState>
            ) : (
              <table className="vb-ov-table">
                <caption className="sr-only">{t.caption}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t.columns.purpose}</th>
                    <th scope="col">{t.columns.version}</th>
                    <th scope="col">{t.columns.granted}</th>
                    <th scope="col">{t.columns.withdrawn}</th>
                  </tr>
                </thead>
                <tbody>
                  {texts.counts.map((c) => (
                    <tr key={`${c.purpose}-${c.consent_text_version}`}>
                      <th scope="row" lang="de">
                        {label(c.purpose)}
                      </th>
                      <td className="vb-ov-mono">{c.consent_text_version}</td>
                      <td>{c.granted}</td>
                      <td>{c.withdrawn}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </SettingsFrame>
    </VitaShell>
  );
}
