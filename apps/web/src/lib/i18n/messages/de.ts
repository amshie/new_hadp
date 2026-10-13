// German wording of the interface — the source: its keys are the keys every other language
// must have (messages/en.ts is typed against this object, so a missing or an extra key does
// not compile). Covered by the web copy scan (apps/api/tests/test_web_copy_language.py).
export const de = {
  shell: {
    navAria: "Hauptnavigation",
    workspace: "Arbeitsbereich",
    overview: "Übersicht",
    patients: "Patienten",
    reviewQueue: "Review-Queue",
    administration: "Verwaltung",
    settings: "Einstellungen",
    pilot: "Pilotumgebung",
    pilotNote: "Synthetische Beispieldaten · keine reale Patientenversorgung.",
    signOut: "Abmelden",
    clinic: "Mandant: ",
    toggleTheme: "Theme wechseln",
    skipLink: "Zum Hauptinhalt springen",
    brandAria: "HADP Übersicht",
  },
  roles: {
    owner: "Inhaber",
    clinician: "Clinician",
    assistant: "Assistenz",
    medical_director: "Ärztliche Leitung",
  },
  meta: {
    description:
      "Klinischer, quellengebundener Workspace — menschliche Prüfung vor jeder Freigabe.",
  },
  login: {
    homeAria: "HADP Startseite",
    kicker: "Klinischer Arbeitsbereich",
    title:
      "Gesundheitsdaten verstehen. Entscheidungen nachvollziehbar dokumentieren.",
    lead: "Ein ruhiger, quellengebundener Workspace für Longevity- und Präventionskliniken – mit menschlicher Prüfung vor jeder Freigabe.",
    trustAria: "Merkmale dieser Umgebung",
    sessionsLimited: "Sitzungen sind zeitlich begrenzt",
    audited: "Zugriffe und Änderungen werden für das Audit protokolliert",
    pilot:
      "Pilotumgebung mit synthetischen Beispieldaten – keine reale Patientenversorgung",
    sectionAria: "Anmeldung",
    eyebrow: "Klinischer Zugang",
    heading: "Anmelden",
    devNote:
      "Pilotumgebung mit synthetischen Beispieldaten. Die Anmeldung erfolgt hier ohne Passwort – mit der E-Mail-Adresse eines eingerichteten Kontos.",
    noneHeading: "Anmeldung nicht eingerichtet",
    noneNote:
      "Für diese Umgebung ist kein Anmeldeverfahren eingerichtet. Eine Anmeldung ist derzeit nicht möglich.",
    unreachableHeading: "Anmeldung derzeit nicht möglich",
    unreachableNote:
      "Der Anmeldedienst ist nicht erreichbar. Bitte versuchen Sie es in einigen Minuten erneut.",
    retry: "Erneut versuchen",
    emailLabel: "E-Mail-Adresse",
    submit: "Anmelden",
    pending: "Anmeldung läuft …",
    purposeNote:
      "Der Zugriff auf Patientendaten ist zweckgebunden und wird protokolliert.",
    errorNoClinic: "Kein Mandant für dieses Konto verfügbar.",
    errorFailed: "Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
  },
  notFound: {
    title: "Seite nicht gefunden",
    note: "Die angeforderte Seite existiert nicht oder ist nicht verfügbar.",
    back: "Zur Übersicht",
  },
  settings: {
    title: "Einstellungen",
    intro:
      "Verwaltung des Mandanten. Die verfügbaren Bereiche richten sich nach Ihrer Rolle.",
    noSections: "Für Ihre Rolle sind keine weiteren Bereiche verfügbar.",
    members: {
      title: "Mitglieder",
      desc: "Team verwalten, Rollen ändern und Kolleg:innen einladen.",
    },
    deletionRequests: {
      title: "Löschanträge",
      desc: "Anträge auf Patientenlöschung prüfen und ausführen (Vier-Augen-Prinzip).",
    },
    auditTrail: {
      title: "Audit-Protokoll",
      desc: "Die protokollierten Vorgänge der Praxis einsehen: wer, wann, welcher Vorgang, an welchem Datensatz.",
    },
    preparationTime: {
      title: "Vorbereitungszeit",
      desc: "Ausgangswert und Folgeangaben der Praxis erfassen und die gemessene Durchlaufzeit der Berichte einsehen.",
    },
  },
  language: {
    title: "Sprache",
    note: "Die Sprache der Oberfläche auf diesem Gerät. Inhalte wie Berichte, Bezeichnungen aus dem Labor und Namen bleiben in der Sprache, in der sie erfasst wurden.",
    // Says exactly what is done. To be widened with every part, and removed with the last page.
    progress:
      "Englisch wird Seite für Seite ergänzt: die Navigation, die Anmeldung und diese Übersicht der Einstellungen sind umgestellt; alle übrigen Seiten erscheinen vorerst auf Deutsch.",
    selected: "ausgewählt",
    choose: "Sprache der Oberfläche",
  },
};

// The same shape with any wording in it.
type Wording<T> = {
  [K in keyof T]: T[K] extends string ? string : Wording<T[K]>;
};
export type Messages = Wording<typeof de>;
