import Link from "next/link";
import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import { me } from "@/lib/api";
import { LOCALES } from "@/lib/i18n/locales";
import { LANGUAGE_NAMES, type Messages } from "@/lib/i18n/messages";
import { getLocale, getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { setLocale } from "./actions";

// Einstellungen landing page: a role-gated index of the settings sections. The sidebar
// "Einstellungen" item points here (not straight to Mitglieder, which is owner-only), so every
// role sees the sections it may actually open — e.g. the medical director reaches Löschanträge.
// Server-side authorization on each sub-page remains the control; this is navigation only.
// The language choice is for everyone who is signed in, whatever their role.
export const dynamic = "force-dynamic";

type SectionKey = keyof Pick<
  Messages["settings"],
  "members" | "deletionRequests" | "auditTrail" | "preparationTime"
>;

const SECTIONS: { href: string; key: SectionKey; roles: string[] }[] = [
  { href: "/einstellungen/mitglieder", key: "members", roles: ["owner"] },
  {
    href: "/einstellungen/loeschantraege",
    key: "deletionRequests",
    roles: ["owner", "medical_director"],
  },
  { href: "/einstellungen/audit", key: "auditTrail", roles: ["owner"] },
  {
    href: "/einstellungen/vorbereitungszeit",
    key: "preparationTime",
    roles: ["owner"],
  },
];

export default async function EinstellungenPage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const role = session.role ?? "";
  const locale = await getLocale();
  const messages = await getMessages();
  const t = messages.settings;
  const sections = SECTIONS.filter((s) => s.roles.includes(role)).map((s) => ({
    href: s.href,
    title: t[s.key].title,
    desc: t[s.key].desc,
  }));

  return (
    <VitaShell
      nav="einstellungen"
      crumb={t.title}
      identity={identity}
      translated
    >
      <div style={{ maxWidth: "820px" }}>
        <h1 style={{ fontSize: "22px", marginBottom: "4px" }}>{t.title}</h1>
        <p
          style={{
            color: "var(--text-muted, #5b6b70)",
            fontSize: "13px",
            marginBottom: "22px",
            lineHeight: 1.55,
          }}
        >
          {t.intro}
        </p>

        <section
          aria-labelledby="language-title"
          style={{
            padding: "18px 20px",
            borderRadius: "12px",
            border: "1px solid var(--border-subtle, #dfe5e7)",
            background: "var(--surface-card, #fff)",
            marginBottom: "22px",
          }}
        >
          <h2
            id="language-title"
            style={{
              fontSize: "15px",
              margin: "0 0 4px",
              color: "var(--text-strong, #17292f)",
            }}
          >
            {messages.language.title}
          </h2>
          <p
            style={{
              fontSize: "12.5px",
              color: "var(--text-muted, #5b6b70)",
              lineHeight: 1.5,
              margin: "0 0 12px",
            }}
          >
            {messages.language.note}
          </p>
          <form
            action={setLocale}
            role="group"
            aria-label={messages.language.choose}
            style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}
          >
            {LOCALES.map((option) => {
              const current = option === locale;
              return (
                <button
                  key={option}
                  type="submit"
                  name="locale"
                  value={option}
                  lang={option}
                  aria-pressed={current}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "8px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                    border: current
                      ? "1.5px solid var(--brand, #0f6b5f)"
                      : "1px solid var(--border-default, #c9d3d6)",
                    background: current
                      ? "var(--brand-soft, #e3f1ee)"
                      : "var(--surface-card, #fff)",
                    color: "var(--text-strong, #17292f)",
                  }}
                >
                  {LANGUAGE_NAMES[option]}
                  {current && (
                    <span style={{ fontWeight: 400 }}>
                      {" "}
                      · {messages.language.selected}
                    </span>
                  )}
                </button>
              );
            })}
          </form>
          <p
            style={{
              fontSize: "12px",
              color: "var(--text-muted, #5b6b70)",
              lineHeight: 1.5,
              margin: "12px 0 0",
            }}
          >
            {messages.language.progress}
          </p>
        </section>

        {sections.length === 0 ? (
          <p style={{ color: "var(--text-muted, #5b6b70)", fontSize: "13px" }}>
            {t.noSections}
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
