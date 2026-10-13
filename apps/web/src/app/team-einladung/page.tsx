import { Disclaimer } from "@/components/Disclaimer";
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
    <main
      lang="de"
      style={{
        maxWidth: "560px",
        margin: "0 auto",
        padding: "56px 24px",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
      }}
    >
      <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>
        Einladung ins Klinik-Team
      </h1>
      {valid ? (
        <TeamEinladungContent tenant={tenant!} token={token!} />
      ) : (
        <p style={{ lineHeight: 1.55 }}>
          Dieser Einladungslink ist nicht oder nicht mehr gültig. Bitte wenden
          Sie sich an Ihre Klinik.
        </p>
      )}
      <Disclaimer />
    </main>
  );
}
