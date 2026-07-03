import { Disclaimer } from "@/components/Disclaimer";
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
    <main
      style={{
        maxWidth: "560px",
        margin: "0 auto",
        padding: "56px 24px",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
      }}
    >
      <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>
        Einladung Ihrer Klinik
      </h1>
      {valid ? (
        <EinladungContent tenant={tenant!} token={token!} />
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
