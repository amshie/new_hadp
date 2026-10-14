import { useSyncExternalStore } from "react";

// The dashboard theme chosen on this device: light, dark, or as the device's system is set.
// Kept in localStorage, read once per page load, and given to the components through
// useSyncExternalStore. While a page hydrates, React takes the server's answer (light: the
// server has no localStorage), so the markup matches, and renders the stored choice right
// after; on a client navigation it reads the choice at once, so a dark theme does not flash
// light. Nothing chosen is light, as before the choice existed.

const THEME_KEY = "vb-theme";
const SYSTEM_DARK = "(prefers-color-scheme: dark)";

export type ThemeChoice = "light" | "dark" | "system";

let choice: ThemeChoice | null = null;
const listeners = new Set<() => void>();

function stored(): ThemeChoice {
  if (choice === null) {
    try {
      const value = localStorage.getItem(THEME_KEY);
      choice = value === "dark" || value === "system" ? value : "light";
    } catch {
      choice = "light";
    }
  }
  return choice;
}

function systemDark(): boolean {
  try {
    return window.matchMedia(SYSTEM_DARK).matches;
  } catch {
    return false;
  }
}

function isDarkTheme(): boolean {
  const current = stored();
  return current === "dark" || (current === "system" && systemDark());
}

function notify(): void {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  // Following the system: a change of the device's setting changes the page.
  let media: MediaQueryList | null = null;
  try {
    media = window.matchMedia(SYSTEM_DARK);
    media.addEventListener("change", listener);
  } catch {
    media = null;
  }
  return () => {
    listeners.delete(listener);
    media?.removeEventListener("change", listener);
  };
}

export function useDarkTheme(): boolean {
  return useSyncExternalStore(subscribe, isDarkTheme, () => false);
}

export function useThemeChoice(): ThemeChoice {
  return useSyncExternalStore(subscribe, stored, () => "light");
}

export function chooseThemeMode(next: ThemeChoice): void {
  choice = next;
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* not kept for the next visit; this one still switches */
  }
  notify();
}

// The topbar's switch: always an explicit light or dark.
export function chooseTheme(dark: boolean): void {
  chooseThemeMode(dark ? "dark" : "light");
}
