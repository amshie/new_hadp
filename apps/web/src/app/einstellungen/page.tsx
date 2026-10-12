import Link from "next/link";
import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { me } from "@/lib/api";
import { shellIdentity } from "@/lib/identity";

// Einstellungen landing page: a role-gated index of the settings sections. The sidebar
// "Einstellungen" item points here (not straight to Mitglieder, which is owner-only), so every
// role sees the sections it may actually open — e.g. the medical director reaches Löschanträge.
// Server-side authorization on each sub-page remains the control; this is navigation only.
export const dynamic = "force-dynamic";

const SECTIONS: {
  href: string;
  title: string;
  desc: string;
  roles: string[];
}[] = [
  {
    href: "/einstellungen/mitglieder",
    title: "Mitglieder",
    desc: "Team verwalten, Rollen ändern und Kolleg:innen einladen.",
    roles: ["owner"],
  },
  {
    href: "/einstellungen/loeschantraege",
    title: "Löschanträge",
    desc: "Anträge auf Patientenlöschung prüfen und ausführen (Vier-Augen-Prinzip).",
    roles: ["owner", "medical_director"],
  },
  {
    href: "/einstellungen/audit",
    title: "Audit-Protokoll",
    desc: "Nachvollziehen, wer in der Praxis wann auf welche Akte zugegriffen und was geändert hat.",
    roles: ["owner"],
  },
];

export default async function EinstellungenPage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const role = session.role ?? "";
  const sections = SECTIONS.filter((s) => s.roles.includes(role));

  return (
    <VitaShell nav="einstellungen" crumb="Einstellungen" identity={identity}>
      <div style={{ maxWidth: "820px" }}>
        <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>Einstellungen</h1>
        <p
          style={{
            color: "var(--text-muted, #5b6b70)",
            fontSize: "13px",
            marginBottom: "22px",
            lineHeight: 1.55,
          }}
        >
          Verwaltung des Mandanten. Die verfügbaren Bereiche richten sich nach
          Ihrer Rolle.
        </p>

        {sections.length === 0 ? (
          <p style={{ color: "var(--text-muted, #5b6b70)", fontSize: "13px" }}>
            Für Ihre Rolle sind derzeit keine Einstellungen verfügbar.
          </p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: "14px",
            }}
          >
            {sections.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                style={{
                  display: "block",
                  padding: "18px 20px",
                  borderRadius: "12px",
                  border: "1px solid var(--border-subtle, #dfe5e7)",
                  background: "var(--surface-card, #fff)",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                    marginBottom: "6px",
                  }}
                >
                  <strong
                    style={{
                      fontSize: "15px",
                      color: "var(--text-strong, #17292f)",
                    }}
                  >
                    {s.title}
                  </strong>
                  <svg
                    aria-hidden="true"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--text-muted, #5b6b70)"
                    strokeWidth="1.9"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </div>
                <span
                  style={{
                    fontSize: "12.5px",
                    color: "var(--text-muted, #5b6b70)",
                    lineHeight: 1.5,
                  }}
                >
                  {s.desc}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </VitaShell>
  );
}
