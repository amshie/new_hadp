import type { ReactNode } from "react";
import {
  Inter,
  Archivo,
  Hanken_Grotesk,
  IBM_Plex_Mono,
} from "next/font/google";

import "../styles/tokens.css";
import "../styles/hadp.css";
import "../styles/vitabahn.css";

// Load Inter explicitly so type matches the prototype previews (no system-font fallback).
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// VitaBahn dashboard typography (ADR-0005): Archivo (display), Hanken Grotesk (UI),
// IBM Plex Mono (data). Exposed as CSS variables consumed by the .vb-scope tokens.
const archivo = Archivo({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-archivo",
  display: "swap",
});
const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-hanken",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata = {
  title: "HADP · Health Analytics",
  description:
    "Klinischer, quellengebundener Workspace — menschliche Prüfung vor jeder Freigabe.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="de"
      className={`${inter.variable} ${archivo.variable} ${hanken.variable} ${plexMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
