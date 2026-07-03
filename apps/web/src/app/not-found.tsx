import Link from "next/link";

// Neutral 404 for unknown routes and notFound() throws — no route details echoed.
export default function NotFound() {
  return (
    <main
      style={{
        maxWidth: "560px",
        margin: "0 auto",
        padding: "64px 24px",
        fontFamily: "var(--font-sans, system-ui, sans-serif)",
      }}
    >
      <h1 style={{ fontSize: "22px", marginBottom: "10px" }}>
        Seite nicht gefunden
      </h1>
      <p style={{ marginBottom: "20px", lineHeight: 1.5 }}>
        Die angeforderte Seite existiert nicht oder ist nicht verfügbar.
      </p>
      <Link href="/overview">Zur Übersicht</Link>
    </main>
  );
}
