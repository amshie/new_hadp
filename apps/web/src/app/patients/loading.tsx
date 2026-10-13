"use client";

import { useDarkTheme } from "@/components/vitabahn/theme";
import { useI18n } from "@/lib/i18n/I18nProvider";

// Route-level loading state for the Patienten directory (the page renders its own
// VitaShell, so this shows a shell-free, token-true skeleton while the governed
// server load — patients + worklist over the tenant-scoped API — is in flight.
// A client component: it has to be there at once, and it reads the interface language and
// the theme (a dark theme's skeleton is dark, as the page that follows).

const bar = (width: string, height = "14px") => ({
  width,
  height,
  borderRadius: "var(--radius-sm)",
  background: "var(--surface-sunken)",
  border: "1px solid var(--border-subtle)",
});

export default function PatientsLoading() {
  const t = useI18n().t.patients;
  const dark = useDarkTheme();
  return (
    <div
      className="vb-scope"
      data-theme={dark ? "dark" : "light"}
      style={{
        minHeight: "100vh",
        background: "var(--bg-page)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
      }}
    >
      <style>{`@keyframes vb-skeleton-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.45; } }`}</style>
      <div
        role="status"
        aria-live="polite"
        style={{
          width: "min(560px, 100%)",
          background: "var(--surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-sm)",
          padding: "28px",
        }}
      >
        <div
          aria-hidden="true"
          style={{
            display: "grid",
            gap: "12px",
            animation: "vb-skeleton-pulse 1.4s ease-in-out infinite",
          }}
        >
          <div style={bar("38%", "20px")} />
          <div style={bar("70%")} />
          <div style={bar("100%", "44px")} />
          <div style={bar("100%", "44px")} />
          <div style={bar("62%")} />
        </div>
        <p
          style={{
            margin: "18px 0 0",
            fontSize: "12.5px",
            fontFamily: "var(--font-text)",
            color: "var(--text-muted)",
            textAlign: "center",
          }}
        >
          {t.loading}
        </p>
      </div>
    </div>
  );
}
