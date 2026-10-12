// German copy for the closed consent-purpose vocabulary (API: ConsentPurpose). One source for
// the onboarding wizard and the patient page, so a purpose is described the same way wherever
// it is recorded. The purposes and the consent text version are SYNTHETIC-ALPHA placeholders —
// the real taxonomy and wording are a DPO/counsel deliverable.

import type { components } from "@hadp/api-client";

export type ConsentPurpose = components["schemas"]["ConsentIn"]["purpose"];

export const CONSENT_OPTIONS: {
  purpose: ConsentPurpose;
  label: string;
  desc: string;
}[] = [
  {
    purpose: "report_release",
    label: "Freigabe geprüfter Berichte",
    desc: "Ärztlich freigegebene Berichte dürfen der Person bereitgestellt werden.",
  },
  {
    purpose: "data_source_connect",
    label: "Anbindung von Datenquellen",
    desc: "Externe Datenquellen (z. B. Labor) dürfen mit der Akte verknüpft werden.",
  },
  {
    purpose: "analytics",
    label: "Erweiterte Auswertungen",
    desc: "Daten dürfen für zusammenfassende Auswertungen der Klinik verwendet werden.",
  },
];
