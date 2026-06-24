import type { ReactNode } from "react";
import { Inter } from "next/font/google";

import "../styles/tokens.css";
import "../styles/hadp.css";

// Load Inter explicitly so type matches the prototype previews (no system-font fallback).
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "HADP · Health Analytics",
  description:
    "Klinischer, quellengebundener Workspace — menschliche Prüfung vor jeder Freigabe.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
