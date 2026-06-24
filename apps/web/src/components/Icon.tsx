import type { CSSProperties } from "react";

// Exact SVG path data lifted from the prototype (HADP-UI-Optimiert-v2 HTML + hadp.js ICONS).
// Static strings only (no user data), rendered as inner markup for faithful reproduction.
export const ICON_PATHS = {
  // navigation
  overview:
    '<path d="M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z"></path>',
  patients:
    '<circle cx="9" cy="8" r="3"></circle><path d="M3.5 19a5.5 5.5 0 0 1 11 0M16 8h5M18.5 5.5v5"></path>',
  download: '<path d="M12 3v12M8 11l4 4 4-4M5 20h14"></path>',
  reports:
    '<path d="M6 3h9l3 3v15H6z"></path><path d="M9 12h6M9 16h6M14 3v4h4"></path>',
  rules:
    '<path d="M4 6h16M4 12h16M4 18h16"></path><circle cx="8" cy="6" r="2"></circle><circle cx="15" cy="12" r="2"></circle><circle cx="10" cy="18" r="2"></circle>',
  auditlog:
    '<path d="M6 3h9l3 3v15H6z"></path><path d="M9 9h6M9 13h6M9 17h4"></path>',
  settings:
    '<circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"></path>',
  // topbar
  building:
    '<path d="M4 20h16M6 20V8l6-4 6 4v12M9 11h.01M12 11h.01M15 11h.01M9 15h.01M12 15h.01M15 15h.01"></path>',
  chevronDown: '<path d="m8 10 4 4 4-4"></path>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"></path>',
  account:
    '<circle cx="12" cy="8" r="4"></circle><path d="M4 21a8 8 0 0 1 16 0"></path>',
  myAudit: '<path d="M6 3h9l3 3v15H6z"></path><path d="M9 12h6M9 16h6"></path>',
  logout: '<path d="M10 17l5-5-5-5M15 12H3M14 4h6v16h-6"></path>',
  // worklist
  calendar:
    '<path d="M4 5h16v14H4zM8 3v4M16 3v4M4 9h16"></path><path d="M8 13h3M8 16h6"></path>',
  people2:
    '<circle cx="9" cy="8" r="3"></circle><circle cx="17" cy="9" r="2.5"></circle><path d="M3 20a6 6 0 0 1 12 0M14 20a5 5 0 0 1 7 0"></path>',
  bars: '<path d="M4 19V9M10 19V5M16 19v-7M22 19H2"></path>',
  search: '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path>',
  sort: '<path d="M8 6h12M8 12h8M8 18h4M4 4v16"></path>',
  docText:
    '<path d="M7 8h10M7 12h7M7 16h4"></path><path d="M5 3h14v18H5z"></path>',
  flask:
    '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"></path><path d="M7.5 15h9"></path>',
  userCircle:
    '<circle cx="12" cy="8" r="3"></circle><path d="M5 20a7 7 0 0 1 14 0"></path>',
  // auth / shared
  mail: '<path d="M4 6h16v12H4z"></path><path d="m4 7 8 6 8-6"></path>',
  lock: '<rect x="4" y="10" width="16" height="10" rx="2"></rect><path d="M8 10V7a4 4 0 0 1 8 0v3"></path>',
  shieldCheck:
    '<path d="M12 3 4.5 6v5.5c0 4.8 3.1 7.8 7.5 9.5 4.4-1.7 7.5-4.7 7.5-9.5V6z"></path><path d="m9 12 2 2 4-4"></path>',
  shieldInfo:
    '<path d="M12 3 4.5 6v5.5c0 4.8 3.1 7.8 7.5 9.5 4.4-1.7 7.5-4.7 7.5-9.5V6z"></path><path d="M12 8v5M12 16h.01"></path>',
  alert:
    '<path d="M12 3 2.8 20h18.4z"></path><path d="M12 9v4M12 17h.01"></path>',
  check: '<path d="m5 12 4 4L19 6"></path>',
  close: '<path d="m6 6 12 12M18 6 6 18"></path>',
  // domains (review)
  shield:
    '<path d="M12 3 4.5 6v5.5c0 4.8 3.1 7.8 7.5 9.5 4.4-1.7 7.5-4.7 7.5-9.5V6z"></path><path d="m9 12 2 2 4-4"></path>',
  heart:
    '<path d="M20.8 5.6a5.2 5.2 0 0 0-7.4 0L12 7l-1.4-1.4a5.2 5.2 0 0 0-7.4 7.4L12 21l8.8-8a5.2 5.2 0 0 0 0-7.4z"></path>',
  brain:
    '<path d="M9.5 4.5A3.5 3.5 0 0 0 6 8v.2A3.5 3.5 0 0 0 4.5 15 3.5 3.5 0 0 0 8 18.5h1.5zM14.5 4.5A3.5 3.5 0 0 1 18 8v.2A3.5 3.5 0 0 1 19.5 15a3.5 3.5 0 0 1-3.5 3.5h-1.5z"></path><path d="M9.5 9H7M14.5 9H17M9.5 14H7.5M14.5 14h2"></path>',
  bone: '<path d="M17.5 3a2.5 2.5 0 0 0-2.3 3.5l-6.7 6.7A2.5 2.5 0 1 0 5 16.5a2.5 2.5 0 1 0 3.3 3.3l6.7-6.7A2.5 2.5 0 1 0 18.5 9a2.5 2.5 0 1 0-1-6z"></path>',
  leaf: '<path d="M20.8 4.2C14 4 6.2 5 4 12c-1.4 4.4 2.3 7.7 6.4 6.5 5.9-1.8 7.5-8.4 10.4-14.3z"></path><path d="M4.8 19.2C8 15.4 11 12.7 16.7 9.6"></path>',
} as const;

export type IconName = keyof typeof ICON_PATHS;

export function Icon({
  name,
  className = "",
  style,
}: {
  name: IconName;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      className={`icon ${className}`.trim()}
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={style}
      dangerouslySetInnerHTML={{ __html: ICON_PATHS[name] }}
    />
  );
}
