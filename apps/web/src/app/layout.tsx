import type { ReactNode } from "react";
// Fonts ship with the build. Each package holds the font files and their @font-face rules
// (one per script, loaded by the browser only for the characters a page uses); nothing is
// fetched from a third party when the app is built or when a page is opened.
// Inter: the workspace type. Archivo (display), Hanken Grotesk (UI) and IBM Plex Mono (data):
// the VitaBahn dashboard typography (ADR-0005). The families are named in styles/tokens.css.
import "@fontsource-variable/inter/wght.css";
import "@fontsource-variable/archivo/wght.css";
import "@fontsource-variable/hanken-grotesk/wght.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";

import "../styles/tokens.css";
import "../styles/hadp.css";
import "../styles/vitabahn.css";

export const metadata = {
  title: "HADP · Health Analytics",
  description:
    "Klinischer, quellengebundener Workspace — menschliche Prüfung vor jeder Freigabe.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
