import Link from "next/link";
import type { ReactNode } from "react";

import { roleName } from "@/lib/identity";
import type { Messages } from "@/lib/i18n/messages";
import {
  mayOpen,
  SETTINGS_GROUPS,
  SETTINGS_SECTIONS,
  type SettingsKey,
  type SettingsSection,
} from "@/lib/settingsSections";
import { fill } from "@/lib/i18n/fill";

// Every page of Einstellungen: the sub-navigation in three groups beside the page's own
// content. It stays on every sub-page, so each has a way to the others, not only the
// breadcrumb. A section the role may not open is shown locked — named, not a link.

export function lockedLabel(
  section: SettingsSection,
  messages: Messages,
): string {
  const roles = (section.roles ?? [])
    .map((r) => roleName(messages.roles, r))
    .join(messages.settings.nav.and);
  return fill(messages.settings.nav.locked, { roles });
}

export function sectionTitle(key: SettingsKey, messages: Messages): string {
  return messages.settings[key].title;
}

// The group a section sits in, as the page's eyebrow above its title.
export function sectionEyebrow(key: SettingsKey, messages: Messages): string {
  const section = SETTINGS_SECTIONS.find((s) => s.key === key);
  return section ? messages.settings.nav.groups[section.group] : "";
}

function LockIcon() {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

export function SettingsFrame({
  role,
  current,
  messages,
  children,
}: {
  role: string | null | undefined;
  current: SettingsKey;
  messages: Messages;
  children: ReactNode;
}) {
  const t = messages.settings;
  return (
    <div className="vb-set">
      <nav className="vb-set-nav" aria-label={t.nav.label}>
        {SETTINGS_GROUPS.map((group) => (
          <div key={group} className="vb-set-group">
            <span className="vb-set-grouplabel">{t.nav.groups[group]}</span>
            <ul>
              {SETTINGS_SECTIONS.filter((s) => s.group === group).map((s) => {
                const title = sectionTitle(s.key, messages);
                if (!mayOpen(s, role)) {
                  return (
                    <li key={s.key}>
                      <span
                        className="vb-set-link"
                        aria-disabled="true"
                        title={lockedLabel(s, messages)}
                      >
                        {title}
                        <span className="vb-set-lock">
                          <LockIcon />
                          <span className="sr-only">
                            {lockedLabel(s, messages)}
                          </span>
                        </span>
                      </span>
                    </li>
                  );
                }
                return (
                  <li key={s.key}>
                    <Link
                      href={s.href}
                      className="vb-set-link"
                      aria-current={s.key === current ? "page" : undefined}
                    >
                      {title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
      <div className="vb-set-main">{children}</div>
    </div>
  );
}

export { LockIcon };
