"use client";

import {
  chooseThemeMode,
  useThemeChoice,
  type ThemeChoice as Choice,
} from "@/components/vitabahn/theme";
import { useI18n } from "@/lib/i18n/I18nProvider";

// Light, dark, or as the device's system is set — kept on this device (components/vitabahn/
// theme.ts). The moon in the topbar switches between light and dark; this is where "System"
// lives.

const CHOICES: Choice[] = ["light", "dark", "system"];

export function ThemeChoice() {
  const t = useI18n().t.appearance.theme;
  const current = useThemeChoice();
  return (
    <div className="vb-set-seg" role="group" aria-label={t.label}>
      {CHOICES.map((choice) => (
        <button
          key={choice}
          type="button"
          aria-pressed={current === choice}
          onClick={() => chooseThemeMode(choice)}
        >
          {t[choice]}
        </button>
      ))}
    </div>
  );
}
