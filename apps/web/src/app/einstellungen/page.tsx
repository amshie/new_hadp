import Link from "next/link";
import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  consentTexts,
  getPreparationTime,
  listAuditEvents,
  listDeletionRequests,
  listMembers,
  listStaffInvitations,
  me,
  type Me,
  mySessions,
} from "@/lib/api";
import { CLINIC_TIME_ZONE } from "@/lib/clinicTime";
import { CONSENT_OPTIONS } from "@/lib/consentCopy";
import { byCount, fill } from "@/lib/i18n/fill";
import { LOCALES, type Locale } from "@/lib/i18n/locales";
import { LANGUAGE_NAMES, type Messages } from "@/lib/i18n/messages";
import { getLocale, getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";
import {
  mayOpen,
  SETTINGS_SECTIONS,
  type SettingsKey,
} from "@/lib/settingsSections";

import { duration, intlLocale } from "@/lib/format";

import { setLocale } from "./actions";
import { LockIcon, lockedLabel, SettingsFrame } from "./SettingsFrame";
import { ThemeChoice } from "./ThemeChoice";

// Einstellungen: language and appearance for the reader, then every section with what it
// holds right now. Each section's state is read only for a role that may open it — a read
// the role may not make would be refused and recorded as a denied access. Server-side
// authorization on each sub-page and route remains the control; this is navigation only.
export const dynamic = "force-dynamic";

const soft = <T,>(load: Promise<T>): Promise<T | null> =>
  load.catch(() => null);

const DAY_MS = 86_400_000;

// One line per section: what is in it now. Null: it could not be read.
async function sectionStates(
  session: Me,
  locale: Locale,
  messages: Messages,
): Promise<Partial<Record<SettingsKey, string | null>>> {
  const role = session.role ?? "";
  const s = messages.settings.state;
  const may = (key: SettingsKey) =>
    mayOpen(SETTINGS_SECTIONS.find((x) => x.key === key)!, role);
  const now = Date.now();
  const [sessions, texts, members, invitations, prep, deletions, denials] =
    await Promise.all([
      soft(mySessions()),
      soft(consentTexts()),
      may("members") ? soft(listMembers()) : null,
      may("members") ? soft(listStaffInvitations()) : null,
      may("preparationTime") ? soft(getPreparationTime()) : null,
      may("deletionRequests") ? soft(listDeletionRequests()) : null,
      may("auditTrail")
        ? soft(
            listAuditEvents({
              category: "authz",
              since: new Date(now - 7 * DAY_MS).toISOString(),
              limit: 100,
            }),
          )
        : null,
    ]);
  const out: Partial<Record<SettingsKey, string | null>> = {};
  out.profile = `${session.user.display_name} · ${session.user.email}`;
  out.clinicProfile = fill(s.clinicProfile, {
    name: session.active_tenant_name ?? "—",
    zone: CLINIC_TIME_ZONE,
  });
  const names = messages.overview.sources.names;
  out.dataSources = fill(s.dataSources, {
    readers: [names.csv, names.ldt2, names.ldt3].join(", "),
  });
  out.consentTexts = texts
    ? fill(s.consentTexts, {
        version: texts.current_version,
        n: CONSENT_OPTIONS.length,
      })
    : null;
  if (may("retention")) out.retention = s.retention;
  out.security = sessions
    ? `${byCount(
        s.sessions,
        sessions.sessions.filter((x) => x.state === "active").length,
      )} · ${sessions.sign_in === "oidc" ? s.signIn.oidc : s.signIn.dev}`
    : null;
  if (may("members")) {
    if (members && invitations) {
      const open = invitations.filter(
        (i) => i.status === "pending" && Date.parse(i.expires_at) > now,
      ).length;
      out.members = `${byCount(s.members, members.length)} · ${
        open === 0 ? s.noInvitations : byCount(s.invitations, open)
      }`;
    } else out.members = null;
  }
  if (may("preparationTime")) {
    if (prep) {
      const median = prep.measured_last_30_days.median_seconds;
      out.preparationTime = `${
        prep.baseline ? s.baselineSet : s.baselineMissing
      } · ${
        median != null
          ? fill(s.median, {
              value: duration(median, locale, messages.overview.duration),
            })
          : s.noMedian
      }`;
    } else out.preparationTime = null;
  }
  if (may("deletionRequests")) {
    if (deletions) {
      const open = deletions.filter(
        (d) => d.status === "pending" || d.status === "approved",
      ).length;
      out.deletionRequests =
        open === 0 ? s.noDeletions : byCount(s.deletions, open);
    } else out.deletionRequests = null;
  }
  if (may("auditTrail")) {
    out.auditTrail = denials ? byCount(s.denials, denials.items.length) : null;
  }
  return out;
}

export default async function EinstellungenPage() {
  const session = await me().catch(() => null);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const role = session.role ?? "";
  const locale = await getLocale();
  const messages = await getMessages();
  const t = messages.settings;
  const a = messages.appearance;
  const states = await sectionStates(session, locale, messages);
  const now = Date.now();
  const formats = [
    new Intl.NumberFormat(intlLocale(locale)).format(1234.5),
    new Intl.DateTimeFormat(intlLocale(locale), {
      timeZone: CLINIC_TIME_ZONE,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(now),
    CLINIC_TIME_ZONE,
  ].join(" · ");
  const cards = SETTINGS_SECTIONS.filter((s) => s.key !== "appearance");

  return (
    <VitaShell nav="einstellungen" crumb={t.title} identity={identity}>
      <SettingsFrame role={role} current="appearance" messages={messages}>
        <div className="vb-set-head">
          <span className="vb-ov-eyebrow">{t.eyebrow}</span>
          <h1 className="vb-ov-h1">{t.title}</h1>
          <p className="vb-ov-lead">{t.intro}</p>
        </div>
        <section
          className="vb-ov-card"
          aria-labelledby="appearance-title"
          id="sprache"
        >
          <div className="vb-ov-head">
            <div>
              <h2 id="appearance-title" className="vb-ov-h2">
                {a.title}
              </h2>
              <p className="vb-ov-note">{a.note}</p>
            </div>
          </div>
          <div className="vb-ov-body">
            <div className="vb-set-row">
              <div className="vb-set-k">
                <b id="language-label">{a.language.label}</b>
                <span>{a.language.help}</span>
              </div>
              <form
                action={setLocale}
                className="vb-set-seg"
                role="group"
                aria-labelledby="language-label"
              >
                {LOCALES.map((option) => (
                  <button
                    key={option}
                    type="submit"
                    name="locale"
                    value={option}
                    lang={option}
                    aria-pressed={option === locale}
                  >
                    {LANGUAGE_NAMES[option]}
                  </button>
                ))}
              </form>
            </div>
            <div className="vb-set-row">
              <div className="vb-set-k">
                <b>{a.theme.label}</b>
                <span>{a.theme.help}</span>
              </div>
              <ThemeChoice />
            </div>
            <div className="vb-set-row">
              <div className="vb-set-k">
                <b>{a.formats.label}</b>
                <span>{a.formats.help}</span>
              </div>
              <span className="vb-ov-mono">{formats}</span>
            </div>
            <div className="vb-set-row">
              <div className="vb-set-k">
                <b>{a.progress.label}</b>
              </div>
              <details className="vb-ov-details" style={{ marginTop: 0 }}>
                <summary>{a.progress.summary}</summary>
                <p className="vb-ov-note" style={{ marginTop: "8px" }}>
                  {messages.language.progress}
                </p>
              </details>
            </div>
          </div>
        </section>

        <section aria-labelledby="all-sections" style={{ marginTop: "18px" }}>
          <h2 id="all-sections" className="vb-ov-h2">
            {t.all.title}
          </h2>
          <p className="vb-ov-note" style={{ marginBottom: "12px" }}>
            {t.all.note}
          </p>
          <ul className="vb-set-cards">
            {cards.map((s) => {
              const title = t[s.key].title;
              const group = t.nav.groups[s.group];
              if (!mayOpen(s, role)) {
                return (
                  <li key={s.key} className="vb-set-card locked">
                    <div className="vb-set-card-t">
                      <b>{title}</b>
                      <span className="vb-set-lock">
                        <LockIcon />
                        {lockedLabel(s, messages)}
                      </span>
                    </div>
                    <span className="vb-set-card-d">{t[s.key].desc}</span>
                  </li>
                );
              }
              const state = states[s.key];
              return (
                <li key={s.key}>
                  <Link href={s.href} className="vb-set-card">
                    <div className="vb-set-card-t">
                      <b>{title}</b>
                      <span className="vb-ov-eyebrow">{group}</span>
                    </div>
                    <span className="vb-set-card-s">
                      {state ?? t.state.unavailable}
                    </span>
                    <span className="vb-set-card-d">{t[s.key].desc}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      </SettingsFrame>
    </VitaShell>
  );
}
