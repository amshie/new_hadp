import { Disclaimer } from "@/components/Disclaimer";
import { BrandMark } from "@/components/vitabahn/BrandMark";
import { PublicScope } from "@/components/vitabahn/PublicScope";
import { isUuid } from "@/lib/uuid";

import { TeamEinladungContent } from "./TeamEinladungContent";

// Staff-invitation redeem page: unauthenticated, deliberately NOT wrapped in a staff shell.
// The colleague self-onboards by creating their account; the tenant param is UUID-guarded
// BEFORE anything else and an invalid link renders a neutral shell with no request. The role
// is fixed by the invitation on the server — it is never shown or chosen here.
export default async function TeamEinladungPage({
  searchParams,
}: {
  searchParams: Promise<{ tenant?: string; token?: string }>;
}) {
  const { tenant, token } = await searchParams;
  const valid = Boolean(tenant && token && isUuid(tenant));

  return (
    <PublicScope>
      <main lang="de" className="vb-pub">
        <header className="vb-pub-head">
          <h1 className="vb-pub-h1">Einladung ins Klinik-Team</h1>
        </header>
        <div className="vb-pub-card">
          {valid ? (
            <TeamEinladungContent tenant={tenant!} token={token!} />
          ) : (
            <p>
              Dieser Einladungslink ist nicht oder nicht mehr gültig. Bitte
              wenden Sie sich an Ihre Klinik.
            </p>
          )}
        </div>
        <Disclaimer />
        <footer className="vb-pub-foot">
          <BrandMark size={28} />
        </footer>
      </main>
    </PublicScope>
  );
}
