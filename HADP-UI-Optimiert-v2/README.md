# HADP – optimierter UI-Prototyp

Ein statischer, responsiver Prototyp für den klinischen HADP-Workflow.

## Start

Öffnen Sie `index.html` oder direkt `auth.html` im Browser.

Empfohlen ist ein kleiner lokaler Webserver:

```bash
python3 -m http.server 8080
```

Danach: `http://localhost:8080`

## Klickbarer Ablauf

1. `auth.html` – Anmeldung, Zwei-Faktor-Bestätigung, gesperrte und abgemeldete Sitzung
2. `worklist.html` – klinische Arbeitsliste mit Filtern und Suche
3. `patient-review.html` – Assessment, Domänen, Quellen, Beobachtungen und Signaturdialog

Im statischen Prototyp genügt auf der 2FA-Seite ein beliebiger sechsstelliger Code.

## Dateien

```text
HADP-UI-Optimiert-v2/
├── index.html
├── auth.html
├── worklist.html
├── patient-review.html
├── DESIGN-REVIEW.md
├── CLAUDE-CODE-HANDOFF.md
├── assets/
│   ├── hadp.css
│   └── hadp.js
└── previews/
    ├── auth-desktop.png
    ├── auth-mobile.png
    ├── worklist-desktop.png
    ├── worklist-mobile.png
    ├── patient-review-desktop.png
    └── patient-review-mobile.png
```

## Wichtige Hinweise

- Sämtliche Patientendaten sind synthetisch.
- Authentifizierung, Persistenz, Audit-Log, Importe, PDF-Export und SSO sind nicht mit einem Backend verbunden.
- Generierte Texte werden als nicht freigegebene Entwürfe dargestellt.
- Aussagen bleiben von strukturierten Beobachtungen und Quellen getrennt.
- Es werden keine Font-Dateien oder externen UI-Bibliotheken benötigt.
