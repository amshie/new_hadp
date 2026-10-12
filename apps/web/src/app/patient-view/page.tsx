import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { Disclaimer } from "@/components/Disclaimer";
import { patientView } from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { decodePv, PV_COOKIE } from "@/lib/patientView";
import { isUuid } from "@/lib/uuid";

// Patient-facing report view (released content only). de-DE like every other surface;
// the four-part disclaimer renders on every state. The failure state is neutral — it
// never reveals whether a link is wrong, expired, revoked, or unreleased.
//
// The token is read ONLY from the httpOnly hadp_pv cookie set by /patient-view/oeffnen —
// never from the URL — so it stays out of the address bar, history, and referrers.
export const dynamic = "force-dynamic";

// The day of release as the patient reads it (de-DE). Rendered on the server, so the zone is
// named explicitly — the DACH pilot default, the same one the API reads laboratory times in.
function releaseDay(iso: string | null): string | null {
  const at = iso ? new Date(iso) : null;
  if (!at || Number.isNaN(at.getTime())) return null;
  return at.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: CLINIC_TIME_ZONE,
  });
}

export default async function PatientViewPage() {
  const creds = decodePv((await cookies()).get(PV_COOKIE)?.value);

  const shell = (children: ReactNode) => (
    <main
      style={{
        maxWidth: "640px",
        margin: "0 auto",
        padding: "56px 24px",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
      }}
    >
      {children}
      <Disclaimer />
    </main>
  );

  // UUID-guard the tenant BEFORE any request (mirrors /einladung).
  if (!creds || !isUuid(creds.tenant)) {
    return shell(<p>Dieser Link ist nicht oder nicht mehr gültig.</p>);
  }
  try {
    const view = await patientView(creds.tenant, creds.token);
    const releasedOn = releaseDay(view.released_at);
    return shell(
      <div>
        <h1 style={{ fontSize: "22px", marginBottom: "6px" }}>Ihr Bericht</h1>
        <p style={{ color: "var(--text-muted, #5b6b70)", fontSize: "13px" }}>
          Ärztlich freigegeben
          {releasedOn ? ` am ${releasedOn}` : ""} · synthetische Demo-Inhalte
        </p>
        <p style={{ lineHeight: 1.55, fontSize: "14px" }}>
          Diese Zusammenfassung gibt Ihre Messwerte wieder – mit dem
          Referenzintervall der jeweiligen Quelle (zum Beispiel Ihres Labors),
          soweit es übernommen wurde. Bitte besprechen Sie die Inhalte mit Ihrem
          klinischen Team.
        </p>
        {view.statements.map((s) => (
          <div
            key={s.id}
            style={{
              margin: "12px 0",
              padding: "14px 16px",
              border: "1px solid var(--border-subtle, #dfe5e7)",
              borderRadius: "10px",
              lineHeight: 1.55,
              fontSize: "14px",
            }}
          >
            <p style={{ margin: 0 }}>{s.text}</p>
          </div>
        ))}
      </div>,
    );
  } catch {
    // Do not reveal whether the link is wrong, expired, revoked, or unreleased.
    return shell(<p>Dieser Bericht ist nicht verfügbar.</p>);
  }
}
