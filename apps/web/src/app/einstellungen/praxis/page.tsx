import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { clinicProfile, me } from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { SettingsFrame } from "../SettingsFrame";

import { ClinicForm } from "./ClinicForm";

// Praxisprofil (docs/notes/0016, part 3): the clinic's name and address, and the time zone
// laboratory times are read in. Every staff role reads it; the owner changes it (the API
// authorizes TENANT_PROFILE_EDIT). No logo: the pilot accepts no images.
export const dynamic = "force-dynamic";

export default async function PraxisPage() {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const profile = await clinicProfile().catch(() => null);
  const t = messages.clinicPage;
  const title = messages.settings.clinicProfile.title;
  const owner = session.role === "owner";

  return (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={shellIdentity(session)}
    >
      <SettingsFrame
        role={session.role}
        current="clinicProfile"
        messages={messages}
      >
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">
            {messages.settings.nav.groups.clinic}
          </span>
          <h1 className="vb-ov-h1">{title}</h1>
          <p className="vb-ov-lead">{t.lead}</p>
        </div>
        <section className="vb-ov-card" aria-labelledby="clinic-profile">
          <div className="vb-ov-head">
            <h2 id="clinic-profile" className="vb-ov-h2">
              {t.profile}
            </h2>
          </div>
          <div className="vb-ov-body">
            {profile == null ? (
              <p className="vb-ov-unavailable">{t.unavailable}</p>
            ) : (
              <>
                {owner ? (
                  <ClinicForm name={profile.name} address={profile.address} />
                ) : (
                  <dl className="vb-set-dl">
                    <div className="vb-set-row">
                      <dt className="vb-set-k">
                        <b>{t.name}</b>
                      </dt>
                      <dd>{profile.name}</dd>
                    </div>
                    <div className="vb-set-row">
                      <dt className="vb-set-k">
                        <b>{t.address}</b>
                      </dt>
                      <dd style={{ whiteSpace: "pre-line" }}>
                        {profile.address ?? t.noAddress}
                      </dd>
                    </div>
                  </dl>
                )}
                <dl className="vb-set-dl" style={{ marginTop: "8px" }}>
                  <div className="vb-set-row">
                    <dt className="vb-set-k">
                      <b>{t.zone}</b>
                      <span>{t.zoneHelp}</span>
                    </dt>
                    <dd className="vb-ov-mono">{profile.lab_time_zone}</dd>
                  </div>
                  <div className="vb-set-row">
                    <dt className="vb-set-k">
                      <b>{t.logo}</b>
                    </dt>
                    <dd>{t.logoNote}</dd>
                  </div>
                </dl>
                {!owner && <p className="vb-ov-note">{t.ownerOnly}</p>}
              </>
            )}
          </div>
        </section>
      </SettingsFrame>
    </VitaShell>
  );
}
