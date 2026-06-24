# Übergabe an Claude Code

Die HTML-Dateien sind die visuelle Referenz, nicht die endgültige Produktionsarchitektur.

## Empfohlene Komponenten

- `AppShell`
- `SidebarNavigation`
- `Topbar`
- `StatusBadge`
- `PatientIdentity`
- `DataQualityBar`
- `WorklistTable`
- `DomainCard` / `DomainRow`
- `ObservationTable`
- `SourceLink`
- `ReviewWorkflow`
- `ConfirmationDialog`

## Empfohlene Routen

```text
/login
/worklist
/patients/:patientId/assessments/:assessmentId
```

## Prompt für Claude Code

```text
Read CLAUDE.md and every file in HADP-UI-Optimiert-v2 completely. Treat the HTML/CSS prototype as the visual and interaction reference, not as production architecture. Implement the first frontend vertical slice using the repository's existing stack. Preserve accessibility, responsive behavior, cautious medical and compliance wording, source provenance, clinician approval gates, tenant isolation and audit-event requirements. Keep raw observations, derived values and generated narrative as separate data types. Do not add autonomous diagnosis, therapy, medication or supplement recommendations. First produce a file-by-file implementation plan; then implement login, worklist and patient assessment review with unit and end-to-end tests.
```

## Technische Priorität

1. Tokens und App-Shell
2. Login und Session-Zustände
3. Arbeitsliste mit API-Typen
4. Assessment-Domänen und Beobachtungsnachweis
5. Signaturworkflow und Audit-Events
6. End-to-End-Test: Login → Arbeitsliste → Assessment → Signatur
