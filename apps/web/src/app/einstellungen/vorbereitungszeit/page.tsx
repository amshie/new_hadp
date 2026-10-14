import { redirect } from "next/navigation";

import { VitaShell } from "@/components/vitabahn/VitaShell";
import {
  ApiError,
  getPreparationTime,
  me,
  type PreparationTime,
} from "@/lib/api";
import { getMessages } from "@/lib/i18n/server";
import { shellIdentity } from "@/lib/identity";

import { PreparationTimeContent, type Outcome } from "./PreparationTimeContent";
import { SettingsFrame } from "../SettingsFrame";

// The preparation-time metric (owner only): what the clinic states about its own preparation
// time, and what the platform measures from the report lifecycle. The API authorizes the read
// and the write (METRIC_READ / METRIC_RECORD); this page mirrors the role check with a
// deny-by-default load. The outcome of a submitted statement arrives as a code in the URL —
// one of a closed set; anything else is no message at all. The page follows the interface
// language (lib/i18n).
export const dynamic = "force-dynamic";

const FAILURES = [
  "eingabe",
  "minuten",
  "stichprobe",
  "schaetzung",
  "rolle",
  "zuviele",
  "allgemein",
] as const;

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export default async function PreparationTimePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [session, messages] = await Promise.all([
    me().catch(() => null),
    getMessages(),
  ]);
  if (!session) redirect("/login");
  const identity = shellIdentity(session);
  const t = messages.preparationPage;
  const title = messages.settings.preparationTime.title;

  const shell = (children: React.ReactNode) => (
    <VitaShell
      nav="einstellungen"
      crumb={title}
      crumbParent={{ label: messages.settings.title, href: "/einstellungen" }}
      identity={identity}
    >
      <SettingsFrame
        role={session.role}
        current="preparationTime"
        messages={messages}
      >
        {children}
      </SettingsFrame>
    </VitaShell>
  );
  const notice = (text: string) =>
    shell(
      <div style={{ maxWidth: "620px" }}>
        <h1 style={{ fontSize: "22px", marginBottom: "8px" }}>{title}</h1>
        <p style={{ lineHeight: 1.55, color: "var(--text-muted, #5b6b70)" }}>
          {text}
        </p>
      </div>,
    );

  if (session.role !== "owner") return notice(t.ownersOnly);

  let metric: PreparationTime;
  try {
    metric = await getPreparationTime();
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403))
      redirect("/login");
    if (e instanceof ApiError && e.status === 429) return notice(t.tooMany);
    if (e instanceof ApiError && e.status === 503) return notice(t.unavailable);
    throw e;
  }

  const raw = await searchParams;
  const failure = FAILURES.find((f) => f === one(raw.fehler));
  const outcome: Outcome = failure
    ? { failure }
    : one(raw.gespeichert) === "1"
      ? { saved: true }
      : {};

  return shell(
    <PreparationTimeContent
      metric={metric}
      outcome={outcome}
      t={t}
      title={title}
    />,
  );
}
