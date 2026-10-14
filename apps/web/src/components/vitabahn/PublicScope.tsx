"use client";

import { useSyncExternalStore, type ReactNode } from "react";

// The theme scope of the pages that have no signed-in person: sign-in, a patient's report,
// an invitation. They follow the device's setting (nobody has chosen a theme here), with
// the same tokens as the dashboard (styles/tokens.css, `.vb-scope`). The server renders
// light, the client switches on hydration — as the dashboard does with its stored choice.

const SYSTEM_DARK = "(prefers-color-scheme: dark)";

function subscribe(listener: () => void): () => void {
  try {
    const media = window.matchMedia(SYSTEM_DARK);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  } catch {
    return () => {};
  }
}

function systemDark(): boolean {
  try {
    return window.matchMedia(SYSTEM_DARK).matches;
  } catch {
    return false;
  }
}

export function PublicScope({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const dark = useSyncExternalStore(subscribe, systemDark, () => false);
  return (
    <div
      className={`vb-scope vb-public${className ? ` ${className}` : ""}`}
      data-theme={dark ? "dark" : "light"}
    >
      {children}
    </div>
  );
}
