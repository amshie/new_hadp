// German labels for the audit trail (go-live plan A9). An audit action is a stable code the
// API writes; the label says what happened in plain words. A code without a label is shown as
// it is — a new action must never disappear from the trail because nobody named it yet.
// Covered by the web copy scan (apps/api/tests/test_web_copy_language.py).

const ACTION_LABELS: Record<string, string> = {
  "tenant.select": "Praxis ausgewählt",
  "auth.logout": "Abgemeldet",
  "authz.denied": "Zugriff verweigert (Rolle)",
  "csrf.denied": "Anfrage abgewiesen (Sicherheitsprüfung)",
  rate_limited: "Anfrage gedrosselt",
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
  "document.import": "Datei eingelesen",
  "import.run": "Werte übernommen",
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
  "report.release": "Freigabe angefordert",
  "report.patient_view": "Bericht von der Patientin geöffnet",
  "report.patient_view_denied": "Berichtszugriff abgewiesen",
  patient_view: "Patientenansicht aufgerufen",
  "invitation.create": "Patienteneinladung erstellt",
  "invitation.revoked": "Patienteneinladung widerrufen",
  "invitation.redeem": "Patienteneinladung geöffnet",
  "invitation.redeemed": "Patienteneinladung eingelöst",
  "invitation.redeem_denied": "Patienteneinladung abgewiesen",
  "staff_invite.create": "Teameinladung erstellt",
  "staff_invite.revoked": "Teameinladung widerrufen",
  "staff_invite.redeem": "Teameinladung geöffnet",
  "staff_invite.redeemed": "Teameinladung eingelöst",
  "staff_invite.redeem_denied": "Teameinladung abgewiesen",
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

// The part of an action before its first dot. Offered as a filter; the order is the order of
// the list a reader scans.
export const AUDIT_CATEGORIES: { key: string; label: string }[] = [
  { key: "patient", label: "Akten" },
  { key: "report", label: "Berichte" },
  { key: "interpretation", label: "Interpretation" },
  { key: "document", label: "Dateien" },
  { key: "import", label: "Übernahme von Werten" },
  { key: "review_item", label: "Review-Entscheidungen" },
  { key: "consent", label: "Einwilligungen" },
  { key: "privacy", label: "Löschung und Datenauskunft" },
  { key: "invitation", label: "Patienteneinladungen" },
  { key: "staff_invite", label: "Teameinladungen" },
  { key: "member", label: "Mitglieder" },
  { key: "tenant", label: "Eintritt in die Praxis" },
  { key: "authz", label: "Verweigerte Zugriffe" },
  { key: "audit", label: "Lesen dieses Protokolls" },
];

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
