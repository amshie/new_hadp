# Design-Review

## Gesamturteil

Die ursprüngliche Richtung war bereits gut: seriöse Teal-Farbwelt, klare Karten, zurückhaltende Statusfarben und eine passende klinische Anmutung. Für ein überzeugendes MVP fehlten vor allem ein durchgängiger App-Rahmen, konsistente Icons, bessere mobile Darstellung und vorsichtigere Produkttexte.

## Änderungen in dieser Version

### 1. Einheitliches Produktsystem

Arbeitsliste und Patientenreview verwenden dieselbe Seitenleiste, Topbar, Typografie, Abstände und Komponentenlogik. Die drei Ansichten wirken dadurch wie Teile einer Plattform statt wie separate Mockups.

### 2. Klinischere visuelle Sprache

Emoji wurden durch konsistente SVG-Icons ersetzt. Farbe wird nie als einziges Signal verwendet; Status bleibt zusätzlich über Text, Symbol und Form erkennbar.

### 3. Klarere medizinische Semantik

- Zeitliche Veränderung und aktueller Regelstatus werden getrennt angezeigt.
- „Confidence“ wurde als Datenqualität bzw. Datenabdeckung formuliert, nicht als diagnostische Sicherheit.
- Systemtexte sind eindeutig als nicht freigegebene Entwürfe gekennzeichnet.
- Quellen und gemessene Beobachtungen bleiben sichtbar und nachvollziehbar.

### 4. Vorsichtigere Compliance-Kommunikation

Nicht belegbare Aussagen wie pauschale „GDPR Compliance“ oder konkrete Verschlüsselungsversprechen wurden vermieden. Der Prototyp benennt stattdessen Designprinzipien und kennzeichnet synthetische Daten sowie fehlende Backend-Funktionen.

### 5. Mobile Optimierung

- Arbeitslistenzeilen werden auf kleinen Bildschirmen zu lesbaren Karten.
- Domänen werden mobil als Karten statt als breite Tabelle dargestellt.
- Review-Aktionen verdecken keine Inhalte.
- Alle dichten Evidenztabellen bleiben horizontal scrollbar.

### 6. Zugänglichkeit

Enthalten sind semantische Labels, Tastaturbedienung, sichtbare Fokuszustände, Skip-Links, ARIA-Zustände, Escape-Verhalten für Menüs und Dialoge sowie Unterstützung für reduzierte Bewegung.

## Nächster UX-Test

Mit 5–8 Clinicians einen einzigen Ablauf testen:

**Vorgang finden → Grund für die Prüfung verstehen → Quelle kontrollieren → Review signieren oder zurückstellen.**

Zu messen sind Bearbeitungszeit, Fehlklicks, Rückfragen zu Begriffen und Stellen, an denen Nutzer Quellen nicht schnell genug finden.
