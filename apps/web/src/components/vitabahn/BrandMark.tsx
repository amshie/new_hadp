import type { CSSProperties } from "react";

// The one HADP mark: the teal tile with the check and the wordmark beside it. The dashboard's
// sidebar, the sign-in page and the pages a patient or an invited colleague opens all show
// this one — never a second logo (docs/notes/0017).
//
// `onDark` is for a dark panel (the sidebar, the sign-in brand panel): the wordmark is white
// there; elsewhere it takes the text colour of the theme.
export function BrandMark({
  size = 40,
  onDark = false,
  wordmark = true,
}: {
  size?: number;
  onDark?: boolean;
  wordmark?: boolean;
}) {
  const tile: CSSProperties = {
    width: `${size}px`,
    height: `${size}px`,
    flex: "none",
    borderRadius: "var(--radius-md)",
    background: "linear-gradient(150deg, var(--teal-500), var(--teal-700))",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 12px rgba(9,50,45,0.35)",
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "12px" }}>
      <span style={tile} aria-hidden="true">
        <svg
          width={Math.round(size * 0.6)}
          height={Math.round(size * 0.6)}
          viewBox="0 0 64 64"
          fill="none"
        >
          <path
            d="M13 22 L30 53 L55 9"
            stroke="#fff"
            strokeWidth="6.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="55" cy="9" r="5" fill="var(--vital-300)" />
        </svg>
      </span>
      {wordmark && (
        <span style={{ lineHeight: 1.1 }}>
          <span
            style={{
              display: "block",
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: `${Math.round(size * 0.45)}px`,
              letterSpacing: "-0.01em",
              color: onDark ? "#fff" : "var(--text-strong)",
            }}
          >
            HADP
          </span>
          <span
            style={{
              display: "block",
              fontFamily: "var(--font-mono)",
              fontSize: "9.5px",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: onDark ? "var(--slate-400)" : "var(--text-muted)",
              marginTop: "3px",
            }}
          >
            Health Analytics
          </span>
        </span>
      )}
    </span>
  );
}
