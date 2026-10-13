import { useSyncExternalStore } from "react";

// The dashboard theme chosen on this device: kept in localStorage, read once per page load,
// and given to the components through useSyncExternalStore. While a page hydrates, React
// takes the server's answer (light: the server has no localStorage), so the markup matches,
// and renders the stored choice right after; on a client navigation it reads the choice at
// once, so a dark theme does not flash light.

const THEME_KEY = "vb-theme";

let darkTheme: boolean | null = null;
const listeners = new Set<() => void>();

function isDarkTheme(): boolean {
  if (darkTheme === null) {
    try {
      darkTheme = localStorage.getItem(THEME_KEY) === "dark";
    } catch {
      darkTheme = false;
    }
  }
  return darkTheme;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useDarkTheme(): boolean {
  return useSyncExternalStore(subscribe, isDarkTheme, () => false);
}

export function chooseTheme(dark: boolean): void {
  darkTheme = dark;
  try {
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  } catch {
    /* not kept for the next visit; this one still switches */
  }
  listeners.forEach((listener) => listener());
}
