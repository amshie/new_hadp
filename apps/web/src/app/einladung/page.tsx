import { Disclaimer } from "@/components/Disclaimer";
import { BrandMark } from "@/components/vitabahn/BrandMark";
import { PublicScope } from "@/components/vitabahn/PublicScope";
import { isUuid } from "@/lib/uuid";

import { EinladungContent } from "./EinladungContent";

// Patient invitation page (P3, docs/notes/0010 §6): unauthenticated, deliberately NOT
// wrapped in a staff shell. The tenant param is UUID-guarded BEFORE anything else; an
// invalid link renders a neutral shell and performs no request. No report or clinical
// content is shown before consent — this page only captures the consent decision.
export default async function EinladungPage({
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
          <h1 className="vb-pub-h1">Einladung Ihrer Klinik</h1>
        </header>
        <div className="vb-pub-card">
          {valid ? (
            <EinladungContent tenant={tenant!} token={token!} />
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
