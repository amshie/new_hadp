// German labels for the audit trail (go-live plan A9). An audit action is a stable code the
// API writes; the label says what the event records, and no more than that. The three tables
// are held against the API's own audit writes (apps/api/tests/test_audit_read.py): a label for
// an action that is never written, or a written action without a label, fails there. A code
// this file does not know is still shown — as it is.
// Covered by the web copy scan (apps/api/tests/test_web_copy_language.py).

import type { AuditCategory } from "./api";

const ACTION_LABELS: Record<string, string> = {
  "tenant.select": "Praxis ausgewählt",
  "authz.denied": "Zugriff verweigert (Rolle)",
  "audit.read": "Audit-Protokoll gelesen",
  "patient.create": "Akte angelegt",
  "patient.read": "Akte geöffnet",
  "patient.list": "Aktenliste gelesen",
  "patient.duplicate_check": "Dublettenprüfung",
  "observation.read": "Werte gelesen",
  "interpretation.read": "Interpretation gelesen",
  "interpretation.authored": "Interpretation erfasst",
  "document.upload": "Datei hochgeladen",
  "document.list": "Dateiliste gelesen",
  "import.run": "Einlesevorgang ausgeführt",
  "import.refused": "Einlesen abgelehnt",
  "review_queue.read": "Review-Queue gelesen",
  "review_item.resolved": "Review-Eintrag entschieden",
  "consent.read": "Einwilligungen gelesen",
  "consent.granted": "Einwilligung dokumentiert",
  "consent.withdrawn": "Widerruf dokumentiert",
  "report.draft_generated": "Berichtsentwurf erstellt",
  "report.draft_edited": "Bericht überarbeitet",
  "report.redrafted": "Neuer Entwurf nach Laborkorrektur",
  "report.approved": "Bericht genehmigt",
  "report.rejected": "Bericht zurückgewiesen",
  "report.released": "Bericht freigegeben",
  // The event knows that the holder of a link opened the report — not who that was.
  "report.patient_view": "Bericht über einen Zugriffslink geöffnet",
  "report.patient_view_denied": "Zugriff über einen Zugriffslink abgewiesen",
  "invitation.create": "Patienteneinladung erstellt",
  "invitation.revoked": "Patienteneinladung widerrufen",
  "invitation.redeemed": "Patienteneinladung eingelöst",
  "invitation.redeem_denied": "Einlösen einer Patienteneinladung abgewiesen",
  "staff_invite.create": "Teameinladung erstellt",
  "staff_invite.revoked": "Teameinladung widerrufen",
  "staff_invite.redeemed": "Teameinladung eingelöst",
  "staff_invite.redeem_denied": "Einlösen einer Teameinladung abgewiesen",
  "member.role_changed": "Rolle geändert",
  "member.removed": "Mitglied entfernt",
  "privacy.export": "Datenauskunft erstellt",
  "privacy.export_refused": "Datenauskunft abgelehnt",
  "privacy.deletion_requested": "Löschung beantragt",
  "privacy.deletion_approved": "Löschantrag freigegeben",
  "privacy.deletion_rejected": "Löschantrag abgelehnt",
  "privacy.deletion_cancelled": "Löschantrag zurückgezogen",
  "privacy.erasure_executed": "Löschung ausgeführt",
  "privacy.erasure_storage_incomplete": "Löschung: Dateispeicher unvollständig",
  "worklist.read": "Übersicht gelesen",
  "worklist.coverage.read": "Übersicht gelesen (Datenlage)",
  "worklist.throughput.read": "Übersicht gelesen (Durchsatz)",
};

export function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

// The families of events a clinic's trail can hold — the API's closed set (the part of an
// action before its first dot). In the order a reader scans the filter.
const CATEGORY_LABELS: Record<AuditCategory, string> = {
  patient: "Akten",
  observation: "Werte",
  interpretation: "Interpretation",
  report: "Berichte",
  document: "Dateien",
  import: "Einlesevorgänge",
  review_item: "Review-Entscheidungen",
  review_queue: "Review-Queue",
  consent: "Einwilligungen",
  privacy: "Löschung und Datenauskunft",
  invitation: "Patienteneinladungen",
  staff_invite: "Teameinladungen",
  member: "Mitglieder",
  tenant: "Eintritt in die Praxis",
  authz: "Verweigerte Zugriffe",
  worklist: "Übersicht",
  audit: "Lesen dieses Protokolls",
};

export const AUDIT_CATEGORIES = (
  Object.keys(CATEGORY_LABELS) as AuditCategory[]
).map((key) => ({ key, label: CATEGORY_LABELS[key] }));

export function auditCategory(
  value: string | undefined,
): AuditCategory | undefined {
  return AUDIT_CATEGORIES.find((c) => c.key === value)?.key;
}

const TARGET_LABELS: Record<string, string> = {
  patient: "Akte",
  report: "Bericht",
  report_version: "Berichtsfassung",
  source_document: "Datei",
  import_job: "Einlesevorgang",
  review_item: "Review-Eintrag",
  interpretation_run: "Interpretation",
  membership: "Mitgliedschaft",
  patient_invitation: "Patienteneinladung",
  staff_invitation: "Teameinladung",
  deletion_request: "Löschantrag",
  tenant: "Praxis",
};

export function targetLabel(type: string | null): string {
  if (!type) return "—";
  return TARGET_LABELS[type] ?? type;
}
