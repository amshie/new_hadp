import type { CSSProperties, ReactNode } from "react";

// One empty state for every list that has nothing to show: a title when the page has one, and
// a line that says why. `quiet` is the in-section form — left-aligned, small — for a table or
// a tier inside a card; the default is centred, for a list that is the page's content.
export function EmptyState({
  title,
  children,
  quiet = false,
  role,
  style,
}: {
  title?: string;
  children: ReactNode;
  quiet?: boolean;
  role?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`vb-empty${quiet ? " is-quiet" : ""}`}
      role={role}
      style={style}
    >
      {title && <b>{title}</b>}
      <span>{children}</span>
    </div>
  );
}
