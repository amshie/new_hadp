import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { me, myTenants } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { roleName, shellIdentity } from "@/lib/identity";

import { SettingsFrame } from "../SettingsFrame";

// Profil (docs/notes/0016, part 3): how the reader appears in this clinic and in the audit
// trail, and the clinics they belong to. Read only — the name and address come from the
// sign-in. Every signed-in role; the API reads only the reader's own account.
export const dynamic = "force-dynamic";

export default async function ProfilPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const tenants = await myTenants().catch(() => null);
  const t = messages.profilePage;
  const title = messages.settings.profile.title;
  const rows: [string, string][] = [
    [t.name, session.user.display_name],
    [t.email, session.user.email],
    [t.role, roleName(messages.roles, session.role)],
    [t.clinic, session.active_tenant_name ?? "—"],
  ];

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame role={session.role} current="profile" messages={messages}>
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.personal}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <section className="vb-ov-card" aria-labelledby="profile-account">
          <div className="vb-ov-head">
            <h2 id="profile-account" className="vb-ov-h2">
              {t.account}
            </h2>
          </div>
          <div className="vb-ov-body">
            <dl className="vb-set-dl">
              {rows.map(([label, value]) => (
                <div key={label} className="vb-set-row">
                  <dt className="vb-set-k">
                    <b>{label}</b>
                  </dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <p className="vb-ov-note">{t.source}</p>
          </div>
        </section>
        {tenants && tenants.length > 0 && (
          <section
            className="vb-ov-card"
            aria-labelledby="profile-clinics"
            style={{ marginTop: "16px" }}
          >
            <div className="vb-ov-head">
              <div>
                <h2 id="profile-clinics" className="vb-ov-h2">
                  {t.clinics}
                </h2>
                <p className="vb-ov-note">{t.clinicsNote}</p>
              </div>
            </div>
            <div className="vb-ov-body">
              <ul className="vb-ov-srclist">
                {tenants.map((m) => (
                  <li key={m.tenant_id}>
                    <div>
                      {m.tenant_name}
                      <small>{roleName(messages.roles, m.role)}</small>
                    </div>
                    {m.tenant_id === session.active_tenant_id && (
                      <span className="vb-ov-tag">{t.current}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
      </SettingsFrame>
    </VitaShell>
  );
}
