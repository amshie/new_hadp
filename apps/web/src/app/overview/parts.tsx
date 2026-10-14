import type { ReactNode } from "react";

import type { BadgeMeta } from "@/lib/presenters/dashboard";

// The overview's building blocks. The look lives in styles/vitabahn.css (.vb-ov-*).

export function Card({
  labelledBy,
  id,
  children,
}: {
  labelledBy: string;
  id?: string;
  children: ReactNode;
}) {
  return (
    <section className="vb-ov-card" aria-labelledby={labelledBy} id={id}>
      {children}
    </section>
  );
}

export function CardHead({
  id,
  title,
  note,
  aside,
  level = 3,
}: {
  id: string;
  title: string;
  note?: string;
  aside?: ReactNode;
  level?: 2 | 3;
}) {
  const Heading = level === 2 ? "h2" : "h3";
  return (
    <div className="vb-ov-head">
      <div style={{ minWidth: 0 }}>
        <Heading id={id} className={level === 2 ? "vb-ov-h2" : "vb-ov-h3"}>
          {title}
        </Heading>
        {note && <p className="vb-ov-note">{note}</p>}
      </div>
      {aside != null && <div className="vb-ov-aside">{aside}</div>}
    </div>
  );
}

export function KeyValue({
  label,
  note,
  value,
}: {
  label: string;
  note?: string;
  value: ReactNode;
}) {
  return (
    <div className="vb-ov-kv">
      <span>
        {label}
        {note && <small>{note}</small>}
      </span>
      <b>{value}</b>
    </div>
  );
}

export function Pill({ meta }: { meta: BadgeMeta }) {
  return (
    <span
      className="vb-ov-pill"
      style={{ color: meta.fg, background: meta.bg, borderColor: meta.bd }}
    >
      {meta.label}
    </span>
  );
}
