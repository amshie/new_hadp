import Link from "next/link";

import { getMessages } from "@/lib/i18n/server";

// Neutral 404 for unknown routes and notFound() throws — no route details echoed.
export default async function NotFound() {
  const t = (await getMessages()).notFound;
  return (
    <main
      style={{
        maxWidth: "560px",
        margin: "0 auto",
        padding: "64px 24px",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
      }}
    >
      <h1 style={{ fontSize: "22px", marginBottom: "10px" }}>{t.title}</h1>
      <p style={{ marginBottom: "20px", lineHeight: 1.5 }}>{t.note}</p>
      <Link href="/overview">{t.back}</Link>
    </main>
  );
}
