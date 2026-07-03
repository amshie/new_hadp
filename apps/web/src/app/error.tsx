"use client";

// Route-level error boundary: a neutral shell instead of Next's default 500 page.
// Deliberately renders NO error details — nothing technical or data-bearing leaks
// into the UI; the server logs (redacted) carry the cause.
export default function AppError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
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
        Ein technischer Fehler ist aufgetreten
      </h1>
      <p style={{ marginBottom: "20px", lineHeight: 1.5 }}>
        Die Ansicht konnte nicht geladen werden. Bitte versuchen Sie es erneut.
      </p>
      <button
        type="button"
        onClick={reset}
        style={{
          padding: "8px 14px",
          borderRadius: "9px",
          border: "1px solid currentColor",
          background: "transparent",
          cursor: "pointer",
          marginRight: "12px",
        }}
      >
        Erneut versuchen
      </button>
      <a href="/overview">Zur Übersicht</a>
    </main>
  );
}
