# 0018 — The clinic's words, not the platform's

Status: implemented (synthetic Alpha). The second of the design review's priorities
(2026-10-14): engineering vocabulary had reached the interface. What changed, and where:

- **Patienten**: the two always-empty columns (Risiko, Datenqualität) and the Ø Datenqualität
  figure are gone (ADR-0006, addendum 4). The lead and the help texts no longer say
  "tenant-bezogen", "RLS-geschützt", "Gate G1" or "ADR-0006"; "Mandant" is "Praxis" everywhere
  a person reads it (the shell's clinic label, the sign-in error, the duplicate check).
- **Roles**: the clinician's role is "Ärztin/Arzt" in German (it was the English word among
  "Assistenz", "Ärztliche Leitung", "Inhaber"). The English stays "Clinician". The API's role
  values are unchanged.
- **Interpretation**: "Run erfassen (append-only)" is "Interpretation erfassen"; a correction
  is "Interpretation erfassen · Korrektur nach Lauf n"; the lead says a correction is kept as a
  new run and nothing is overwritten, in those words. A run is "Lauf n" on the report page.
- **Bericht**: the code column (LOINC or catalog code) is muted mono text; it looked like a link
  and was none.
- **Audit-Protokoll**: the keys of an event's detail are labelled in words
  (`apps/web/src/lib/auditCopy.ts`, `DETAIL_LABELS`): "Anzahl: 25 · Nach Zeitraum gefiltert:
  nein" instead of `count: 25 · by_time: nein`. The values stay as written. A key the table
  does not know is shown as it is.

Nothing here changes what is recorded or who may do what; it changes what the page calls it.
