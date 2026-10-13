import type { Locale } from "../locales";

import { de, type Messages } from "./de";
import { en } from "./en";

export type { Messages };

export const MESSAGES: Record<Locale, Messages> = { de, en };

// How each language names itself — always in its own words, whatever the interface shows.
export const LANGUAGE_NAMES: Record<Locale, string> = {
  de: "Deutsch",
  en: "English",
};
