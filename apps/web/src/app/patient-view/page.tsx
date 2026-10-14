import { cookies } from "next/headers";
import type { ReactNode } from "react";

import { Disclaimer } from "@/components/Disclaimer";
import { BrandMark } from "@/components/vitabahn/BrandMark";
import { PublicScope } from "@/components/vitabahn/PublicScope";
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
//
// What the page shows (docs/notes/0017): the practice that released the report at the top,
// the day of release, the released statements as the clinician approved them, and the
// values they cite as the source wrote them — name, value, unit, the source's reference
// text, the day of sampling. Nothing is computed here.
export const dynamic = "force-dynamic";

// A day as the patient reads it (de-DE). Rendered on the server, so the zone is named
// explicitly — the DACH pilot default, the same one the API reads laboratory times in.
function dayLabel(iso: string | null): string | null {
  const at = iso ? new Date(iso) : null;
  if (!at || Number.isNaN(at.getTime())) return null;
  return at.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: CLINIC_TIME_ZONE,
  });
}

// A date-only value ("2025-06-10") is a day already; it is not moved through a zone.
function sampledOn(day: string): string {
  const [y, m, d] = day.split("-");
  return y && m && d ? `${d}.${m}.${y}` : day;
}

export default async function PatientViewPage() {
  const creds = decodePv((await cookies()).get(PV_COOKIE)?.value);

  const shell = (children: ReactNode) => (
    <PublicScope>
      <main lang="de" className="vb-pub">
        {children}
        <Disclaimer />
        <footer className="vb-pub-foot">
          <BrandMark size={28} />
        </footer>
      </main>
    </PublicScope>
  );

  // UUID-guard the tenant BEFORE any request (mirrors /einladung).
  if (!creds || !isUuid(creds.tenant)) {
    return shell(
      <div className="vb-pub-card">
        <p>Dieser Link ist nicht oder nicht mehr gültig.</p>
      </div>,
    );
  }
  try {
    const view = await patientView(creds.tenant, creds.token);
    const releasedOn = dayLabel(view.released_at);
    const values = view.values ?? [];
    return shell(
      <article>
        <header className="vb-pub-head">
          {view.clinic && (
            <div className="vb-ov-eyebrow">{view.clinic.name}</div>
          )}
          <h1 className="vb-pub-h1">Ihr Bericht</h1>
          <p className="vb-pub-meta">
            Ärztlich freigegeben
            {releasedOn ? ` am ${releasedOn}` : ""} · synthetische Demo-Inhalte
          </p>
        </header>

        <p className="vb-pub-lead">
          Diese Zusammenfassung gibt Ihre Messwerte wieder – mit dem
          Referenzintervall der jeweiligen Quelle (zum Beispiel Ihres Labors),
          soweit es übernommen wurde. Bitte besprechen Sie die Inhalte mit Ihrem
          klinischen Team.
        </p>

        {values.length > 0 && (
          <section className="vb-pub-card" aria-labelledby="pv-values">
            <h2 id="pv-values" className="vb-pub-h2">
              Ihre Werte
            </h2>
            <div className="vb-pub-tablewrap">
              <table className="vb-pub-table">
                <thead>
                  <tr>
                    <th scope="col">Wert</th>
                    <th scope="col">Ergebnis</th>
                    <th scope="col">Referenz der Quelle</th>
                    <th scope="col">Gemessen</th>
                  </tr>
                </thead>
                <tbody>
                  {values.map((v) => (
                    <tr key={v.observation_id}>
                      <th scope="row">{v.name}</th>
                      <td className="is-num">
                        {v.value}
                        {v.unit ? ` ${v.unit}` : ""}
                      </td>
                      <td className="is-num">{v.reference ?? "—"}</td>
                      <td className="is-num">{sampledOn(v.observed_on)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="vb-pub-card" aria-labelledby="pv-statements">
          <h2 id="pv-statements" className="vb-pub-h2">
            Was Ihr klinisches Team festgehalten hat
          </h2>
          <div className="vb-pub-statements">
            {view.statements.map((s) => (
              <p key={s.id}>{s.text}</p>
            ))}
          </div>
        </section>

        {view.clinic && (
          <p className="vb-pub-released-by">
            Freigegeben von {view.clinic.name}
            {view.clinic.address ? `\n${view.clinic.address}` : ""}
          </p>
        )}
      </article>,
    );
  } catch {
    // Do not reveal whether the link is wrong, expired, revoked, or unreleased.
    return shell(
      <div className="vb-pub-card">
        <p>Dieser Bericht ist nicht verfügbar.</p>
      </div>,
    );
  }
}
