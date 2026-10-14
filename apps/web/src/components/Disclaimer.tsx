// Four-part patient-facing disclaimer (docs/notes/0010 §6): synthetic context, no
// automatic clinical conclusion (the sanctioned phrase, verbatim), the human gate, and
// the contact path (this is not an emergency channel). Rendered on every patient-facing
// page (/einladung, /patient-view). Styled by `.vb-pub-disclaimer` (styles/vitabahn.css).
export function Disclaimer() {
  return (
    <aside aria-label="Wichtige Hinweise" className="vb-pub-disclaimer">
      <p>
        <strong>Pilotumgebung.</strong> Synthetische Beispieldaten · keine reale
        Patientenversorgung.
      </p>
      <p>
        Die Inhalte sind{" "}
        <strong>keine automatische Diagnose oder Therapieempfehlung.</strong>
      </p>
      <p>
        Jeder Bericht wird von Ihrem klinischen Team geprüft und ärztlich
        freigegeben — Sie sehen ausschließlich freigegebene Versionen.
      </p>
      <p>
        Dieses Angebot ist nicht für Notfälle bestimmt. Bei gesundheitlichen
        Fragen wenden Sie sich an Ihre Klinik.
      </p>
    </aside>
  );
}
