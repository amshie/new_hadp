import { cookies } from "next/headers";

import {
  DEFAULT_LOCALE,
  isLocale,
  LOCALE_COOKIE,
  type Locale,
} from "./locales";
import { MESSAGES, type Messages } from "./messages";

// The language of this request: the person's choice on this device, German without one. A
// cookie that holds anything else counts as no choice.
export async function getLocale(): Promise<Locale> {
  const chosen = (await cookies()).get(LOCALE_COOKIE)?.value;
  return isLocale(chosen) ? chosen : DEFAULT_LOCALE;
}

export async function getMessages(): Promise<Messages> {
  return MESSAGES[await getLocale()];
}
