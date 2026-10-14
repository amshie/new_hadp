// Labels for the audit trail (go-live plan A9), German and English (ADR-0007). An audit action
// is a stable code the API writes; the label says what the event records, and no more than
// that. The three tables are held against the API's own audit writes
// (apps/api/tests/test_audit_read.py): a label for an action that is never written, or a
// written action without a label, fails there — and the compiler holds that every label has
// both languages. A code this file does not know is still shown — as it is.
// Covered by the web copy scan (apps/api/tests/test_web_copy_language.py).
//
// "Einlesen" is "import" here, not "read": on this page a read is a read access.

import type { AuditCategory } from "./api";
import type { Locale } from "./i18n/locales";

const ACTION_LABELS: Record<string, Record<Locale, string>> = {
  "tenant.select": { de: "Praxis ausgewählt", en: "Clinic selected" },
  "tenant.profile.read": {
    de: "Praxisprofil gelesen",
    en: "Clinic profile read",
  },
  "tenant.profile_changed": {
    de: "Praxisprofil geändert",
    en: "Clinic profile changed",
  },
  "authz.denied": {
    de: "Zugriff verweigert (Rolle)",
    en: "Access denied (role)",
  },
  "audit.read": { de: "Audit-Protokoll gelesen", en: "Audit trail read" },
  "audit.own.read": {
    de: "Eigene Vorgänge gelesen",
    en: "Own activity read",
  },
  "patient.create": { de: "Akte angelegt", en: "Record created" },
  "patient.read": { de: "Akte geöffnet", en: "Record opened" },
  "patient.list": { de: "Aktenliste gelesen", en: "Record list read" },
  "patient.duplicate_check": { de: "Dublettenprüfung", en: "Duplicate check" },
  "observation.read": { de: "Werte gelesen", en: "Values read" },
  "interpretation.read": {
    de: "Interpretation gelesen",
    en: "Interpretation read",
  },
  "interpretation.authored": {
    de: "Interpretation erfasst",
    en: "Interpretation recorded",
  },
  "document.upload": { de: "Datei hochgeladen", en: "File uploaded" },
  "document.list": { de: "Dateiliste gelesen", en: "File list read" },
  "import.run": { de: "Einlesevorgang ausgeführt", en: "Import carried out" },
  "import.refused": { de: "Einlesen abgelehnt", en: "Import refused" },
  "review_queue.read": { de: "Review-Queue gelesen", en: "Review queue read" },
  "review_item.resolved": {
    de: "Review-Eintrag entschieden",
    en: "Review item decided",
  },
  "consent.read": { de: "Einwilligungen gelesen", en: "Consents read" },
  "consent.texts.read": {
    de: "Einwilligungstexte gelesen",
    en: "Consent texts read",
  },
  "consent.granted": {
    de: "Einwilligung dokumentiert",
    en: "Consent documented",
  },
  "consent.withdrawn": {
    de: "Widerruf dokumentiert",
    en: "Withdrawal documented",
  },
  "report.draft_generated": {
    de: "Berichtsentwurf erstellt",
    en: "Report draft created",
  },
  "report.draft_edited": { de: "Bericht überarbeitet", en: "Report reworked" },
  "report.redrafted": {
    de: "Neuer Entwurf nach Laborkorrektur",
    en: "New draft after a laboratory correction",
  },
  "report.approved": { de: "Bericht genehmigt", en: "Report approved" },
  "report.rejected": { de: "Bericht zurückgewiesen", en: "Report rejected" },
  "report.released": { de: "Bericht freigegeben", en: "Report released" },
  // The event knows that the holder of a link opened the report — not who that was.
  "report.patient_view": {
    de: "Bericht über einen Zugriffslink geöffnet",
    en: "Report opened through an access link",
  },
  "report.patient_view_denied": {
    de: "Zugriff über einen Zugriffslink abgewiesen",
    en: "Access through an access link refused",
  },
  // After 30 refusals in a minute the trail takes no more single entries for that minute.
  "report.patient_view_denials_unrecorded": {
    de: "Zugriffslinks: weitere Abweisungen bis zu einer Minute lang nicht einzeln protokolliert",
    en: "Access links: further refusals not recorded one by one for up to a minute",
  },
  "invitation.create": {
    de: "Patienteneinladung erstellt",
    en: "Patient invitation created",
  },
  "invitation.revoked": {
    de: "Patienteneinladung widerrufen",
    en: "Patient invitation revoked",
  },
  "invitation.redeemed": {
    de: "Patienteneinladung eingelöst",
    en: "Patient invitation redeemed",
  },
  "invitation.redeem_denied": {
    de: "Einlösen einer Patienteneinladung abgewiesen",
    en: "Redeeming a patient invitation refused",
  },
  "invitation.redeem_denials_unrecorded": {
    de: "Patienteneinladungen: weitere Abweisungen bis zu einer Minute lang nicht einzeln protokolliert",
    en: "Patient invitations: further refusals not recorded one by one for up to a minute",
  },
  "staff_invite.create": {
    de: "Teameinladung erstellt",
    en: "Team invitation created",
  },
  "staff_invite.revoked": {
    de: "Teameinladung widerrufen",
    en: "Team invitation revoked",
  },
  "staff_invite.redeemed": {
    de: "Teameinladung eingelöst",
    en: "Team invitation redeemed",
  },
  "staff_invite.redeem_denied": {
    de: "Einlösen einer Teameinladung abgewiesen",
    en: "Redeeming a team invitation refused",
  },
  "staff_invite.redeem_denials_unrecorded": {
    de: "Teameinladungen: weitere Abweisungen bis zu einer Minute lang nicht einzeln protokolliert",
    en: "Team invitations: further refusals not recorded one by one for up to a minute",
  },
  "member.role_changed": { de: "Rolle geändert", en: "Role changed" },
  "member.removed": { de: "Mitglied entfernt", en: "Member removed" },
  "privacy.export": { de: "Datenauskunft erstellt", en: "Data export created" },
  "privacy.export_refused": {
    de: "Datenauskunft abgelehnt",
    en: "Data export refused",
  },
  "privacy.deletion_requested": {
    de: "Löschung beantragt",
    en: "Deletion requested",
  },
  "privacy.deletion_approved": {
    de: "Löschantrag freigegeben",
    en: "Deletion request approved",
  },
  "privacy.deletion_rejected": {
    de: "Löschantrag abgelehnt",
    en: "Deletion request rejected",
  },
  "privacy.deletion_cancelled": {
    de: "Löschantrag zurückgezogen",
    en: "Deletion request withdrawn",
  },
  "privacy.erasure_executed": {
    de: "Löschung ausgeführt",
    en: "Deletion carried out",
  },
  "privacy.erasure_storage_incomplete": {
    de: "Löschung: Dateispeicher unvollständig",
    en: "Deletion: file storage incomplete",
  },
  "worklist.read": { de: "Übersicht gelesen", en: "Overview read" },
  "worklist.coverage.read": {
    de: "Übersicht gelesen (Datenlage)",
    en: "Overview read (data coverage)",
  },
  "worklist.throughput.read": {
    de: "Übersicht gelesen (Durchsatz)",
    en: "Overview read (throughput)",
  },
  "worklist.sources.read": {
    de: "Übersicht gelesen (Datenquellen)",
    en: "Overview read (data sources)",
  },
  "worklist.preparation.read": {
    de: "Vorbereitung je Akte gelesen",
    en: "Preparation by record read",
  },
  "metric.read": {
    de: "Kennzahl Vorbereitungszeit gelesen",
    en: "Preparation time metric read",
  },
  "metric.statement_recorded": {
    de: "Angabe zur Vorbereitungszeit erfasst",
    en: "Preparation time figure recorded",
  },
};

export function actionLabel(action: string, locale: Locale): string {
  return ACTION_LABELS[action]?.[locale] ?? action;
}

// The families of events a clinic's trail can hold — the API's closed set (the part of an
// action before its first dot). In the order a reader scans the filter.
const CATEGORY_LABELS: Record<AuditCategory, Record<Locale, string>> = {
  patient: { de: "Akten", en: "Records" },
  observation: { de: "Werte", en: "Values" },
  interpretation: { de: "Interpretation", en: "Interpretation" },
  report: { de: "Berichte", en: "Reports" },
  document: { de: "Dateien", en: "Files" },
  import: { de: "Einlesevorgänge", en: "Imports" },
  review_item: { de: "Review-Entscheidungen", en: "Review decisions" },
  review_queue: { de: "Review-Queue", en: "Review queue" },
  consent: { de: "Einwilligungen", en: "Consents" },
  privacy: { de: "Löschung und Datenauskunft", en: "Deletion and data export" },
  invitation: { de: "Patienteneinladungen", en: "Patient invitations" },
  staff_invite: { de: "Teameinladungen", en: "Team invitations" },
  member: { de: "Mitglieder", en: "Members" },
  tenant: { de: "Eintritt in die Praxis", en: "Entering the clinic" },
  authz: { de: "Verweigerte Zugriffe", en: "Denied access" },
  worklist: { de: "Übersicht", en: "Overview" },
  audit: { de: "Lesen dieses Protokolls", en: "Reading this trail" },
  metric: { de: "Kennzahlen", en: "Metrics" },
};

const CATEGORY_KEYS = Object.keys(CATEGORY_LABELS) as AuditCategory[];

export function auditCategories(
  locale: Locale,
): { key: AuditCategory; label: string }[] {
  return CATEGORY_KEYS.map((key) => ({
    key,
    label: CATEGORY_LABELS[key][locale],
  }));
}

export function auditCategory(
  value: string | undefined,
): AuditCategory | undefined {
  return CATEGORY_KEYS.find((key) => key === value);
}

const TARGET_LABELS: Record<string, Record<Locale, string>> = {
  patient: { de: "Akte", en: "Record" },
  report: { de: "Bericht", en: "Report" },
  report_version: { de: "Berichtsfassung", en: "Report version" },
  source_document: { de: "Datei", en: "File" },
  import_job: { de: "Einlesevorgang", en: "Import" },
  review_item: { de: "Review-Eintrag", en: "Review item" },
  interpretation_run: { de: "Interpretation", en: "Interpretation" },
  membership: { de: "Mitgliedschaft", en: "Membership" },
  patient_invitation: { de: "Patienteneinladung", en: "Patient invitation" },
  staff_invitation: { de: "Teameinladung", en: "Team invitation" },
  deletion_request: { de: "Löschantrag", en: "Deletion request" },
  tenant: { de: "Praxis", en: "Clinic" },
  preparation_time_statement: {
    de: "Angabe zur Vorbereitungszeit",
    en: "Preparation time figure",
  },
};

export function targetLabel(type: string | null, locale: Locale): string {
  if (!type) return "—";
  return TARGET_LABELS[type]?.[locale] ?? type;
}

// The keys of an event's detail, as the API writes them, in words. An event's detail is a
// small record of codes, counts and flags — never a value, a name or an e-mail address
// (docs/notes/0015) — and the trail shows all of it; a key this table does not know is shown
// as it is. The values stay as written: a code is a code, a count a count.
const DETAIL_LABELS: Record<string, Record<Locale, string>> = {
  action: { de: "Aktion", en: "Action" },
  attempted: { de: "Versucht", en: "Attempted" },
  attempted_tenant: { de: "Versuchte Praxis", en: "Attempted clinic" },
  basis: { de: "Grundlage", en: "Basis" },
  by_actor: { de: "Nach Person gefiltert", en: "Filtered by person" },
  by_target: { de: "Nach Datensatz gefiltert", en: "Filtered by record" },
  by_time: { de: "Nach Zeitraum gefiltert", en: "Filtered by period" },
  byte_size: { de: "Größe (Bytes)", en: "Size (bytes)" },
  candidates: { de: "Treffer", en: "Matches" },
  category: { de: "Bereich", en: "Area" },
  changed: { de: "Geänderte Felder", en: "Changed fields" },
  code: { de: "Code", en: "Code" },
  continued: { de: "Fortgesetzt", en: "Continued" },
  count: { de: "Anzahl", en: "Count" },
  created: { de: "Angelegt", en: "Created" },
  days: { de: "Tage", en: "Days" },
  definition: { de: "Messvorschrift", en: "Definition" },
  domains: { de: "Domänen", en: "Domains" },
  exclude_reads: { de: "Ohne Lesezugriffe", en: "Without read accesses" },
  failed_objects: { de: "Fehlgeschlagene Objekte", en: "Failed objects" },
  jobs: { de: "Vorgänge", en: "Jobs" },
  kind: { de: "Art", en: "Kind" },
  method: { de: "Verfahren", en: "Method" },
  metric: { de: "Kennzahl", en: "Metric" },
  new_role: { de: "Neue Rolle", en: "New role" },
  old_role: { de: "Bisherige Rolle", en: "Previous role" },
  open: { de: "Offen", en: "Open" },
  patient_access_withdrawn: {
    de: "Zugriffslinks zurückgezogen",
    en: "Access links withdrawn",
  },
  patient_id: { de: "Akte", en: "Record" },
  provider: { de: "Anbieter", en: "Provider" },
  purpose: { de: "Zweck", en: "Purpose" },
  reason: { de: "Grund", en: "Reason" },
  reason_category: { de: "Grundkategorie", en: "Reason category" },
  recorded: { de: "Aufgezeichnet", en: "Recorded" },
  removed_role: { de: "Entfernte Rolle", en: "Removed role" },
  role: { de: "Rolle", en: "Role" },
  row_index: { de: "Zeile", en: "Row" },
  run_number: { de: "Lauf", en: "Run" },
  status: { de: "Status", en: "Status" },
  superseded_observation_id: {
    de: "Ersetzter Wert",
    en: "Replaced value",
  },
  total: { de: "Gesamt", en: "Total" },
  version_no: { de: "Fassung", en: "Version" },
  versions: { de: "Fassungen", en: "Versions" },
  window_seconds: { de: "Zeitfenster (Sekunden)", en: "Window (seconds)" },
};

export function detailLabel(key: string, locale: Locale): string {
  return DETAIL_LABELS[key]?.[locale] ?? key;
}
