import type { CSSProperties } from "react";

// Four-part patient-facing disclaimer (docs/notes/0010 §6): synthetic context, no
// automatic clinical conclusion (the sanctioned phrase, verbatim), the human gate, and
// the contact path (this is not an emergency channel). Rendered on every patient-facing
// page (/einladung, /patient-view).
export function Disclaimer() {
  const item: CSSProperties = {
    margin: "0 0 6px",
    fontSize: "12px",
    lineHeight: 1.55,
    color: "var(--text-muted, #5b6b70)",
  };
  return (
    <aside
      aria-label="Wichtige Hinweise"
      style={{
        marginTop: "24px",
        padding: "14px 16px",
        border: "1px solid var(--border-subtle, #dfe5e7)",
        borderRadius: "10px",
        background: "var(--surface-sunken, #f6f8f8)",
      }}
    >
      <p style={item}>
        <strong>Pilotumgebung.</strong> Synthetische Beispieldaten · keine reale
        Patientenversorgung.
      </p>
      <p style={item}>
        Die Inhalte sind{" "}
        <strong>keine automatische Diagnose oder Therapieempfehlung.</strong>
      </p>
      <p style={item}>
        Jeder Bericht wird von Ihrem klinischen Team geprüft und ärztlich
        freigegeben — Sie sehen ausschließlich freigegebene Versionen.
      </p>
      <p style={{ ...item, marginBottom: 0 }}>
        Dieses Angebot ist nicht für Notfälle bestimmt. Bei gesundheitlichen
        Fragen wenden Sie sich an Ihre Klinik.
      </p>
    </aside>
  );
}
