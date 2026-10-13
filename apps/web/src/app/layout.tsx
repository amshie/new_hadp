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

import { I18nProvider } from "@/lib/i18n/I18nProvider";
import { getLocale, getMessages } from "@/lib/i18n/server";

export async function generateMetadata() {
  return {
    title: "HADP · Health Analytics",
    description: (await getMessages()).meta.description,
  };
}

// The interface language is the person's choice on this device (Einstellungen), German
// without one: it names the document's language, and client components read it from the
// provider.
export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();
  return (
    <html lang={locale}>
      <body>
        <I18nProvider locale={locale} messages={messages}>
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
