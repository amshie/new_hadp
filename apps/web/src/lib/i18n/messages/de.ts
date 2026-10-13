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
  dashboard: {
    // The latest report's place in the workflow — a closed set of states, never a clinical one.
    status: {
      review: "In Prüfung",
      approved: "Genehmigt",
      released: "Freigegeben",
      rejected: "Zurückgewiesen",
      none: "Kein Entwurf",
    },
    reportVersion: "Bericht · v{version}",
    time: {
      now: "gerade eben",
      minutes: "vor {n} Min.",
      hours: "vor {n} Std.",
      yesterday: "gestern",
      days: "vor {n} T",
    },
  },
  overview: {
    kicker: "Klinischer Arbeitsbereich",
    title: "Übersicht",
    waiting: { one: "{n} Review", other: "{n} Reviews" },
    waitingRest: {
      one: "wartet auf Ihre Prüfung. Quellengebundene Entwürfe müssen vor jeder Freigabe geprüft werden. Synthetische Beispieldaten.",
      other:
        "warten auf Ihre Prüfung. Quellengebundene Entwürfe müssen vor jeder Freigabe geprüft werden. Synthetische Beispieldaten.",
    },
    kpis: {
      openReviews: {
        label: "Offene Reviews",
        help: "Klinische Prüfung ausstehend",
      },
      approved: { label: "Genehmigt", help: "Warten auf ärztliche Freigabe" },
      released: { label: "Freigegeben", help: "An die Patientin freigegeben" },
      patients: { label: "Patienten", help: "Tenant-bezogen · RLS-geschützt" },
    },
    worklist: {
      title: "Klinische Arbeitsliste",
      note: "Nach Berichtsstatus · keine automatische Diagnose oder Therapieempfehlung.",
      tabs: {
        open: "Offene Reviews",
        approved: "Genehmigt",
        released: "Freigegeben",
        all: "Alle",
      },
      search: "Patient oder ID suchen",
      columns: {
        patient: "Patient",
        assessment: "Assessment",
        status: "Status",
        updated: "Aktualisiert",
      },
      openRow: "Patient {name}, {ref} öffnen",
      emptyTitle: "Keine passenden Vorgänge",
      emptyNote: "Ändern Sie den Filter oder den Suchbegriff.",
    },
    snapshot: {
      title: "Berichtsstatus",
      note: {
        one: "Aktueller Bestand · Momentaufnahme · {n} Patient",
        other: "Aktueller Bestand · Momentaufnahme · {n} Patienten",
      },
    },
    coverage: {
      title: "Datenlage",
      note: {
        one: "Abdeckung über {n} reale Beobachtung · keine Qualitätsbewertung",
        other:
          "Abdeckung über {n} reale Beobachtungen · keine Qualitätsbewertung",
      },
      ring: "PUBLIZIERT",
      published: "Publiziert",
      withReference: "Mit Referenzintervall",
      latest: "Neueste Beobachtung",
    },
    gated: {
      throughput: {
        title: "Review-Durchsatz",
        reason:
          "Durchsatz-Zeitreihe ist derzeit nicht abrufbar. Eigener Backend-Slice (report_versions nach Status).",
      },
      coverage: {
        title: "Datenlage",
        reason:
          "Abdeckung über die Beobachtungen ist derzeit nicht abrufbar. Pro Patient zeigt die Detailansicht die reale Datenlage.",
      },
      activity: {
        title: "Letzte Aktivität",
        reason:
          "Audit-Feed benötigt einen tenant-scoped Lese-Endpoint über die Append-only-Events. Eigener Backend-Slice.",
      },
      imports: {
        title: "Importe & Quellen",
        reason:
          "Import-Status benötigt einen Lese-Endpoint über import_jobs. Eigener Backend-Slice.",
      },
    },
    throughput: {
      title: "Review-Durchsatz",
      note: "Entwürfe erstellt vs. Reviews signiert · echte Zeitstempel",
      days14: "14 T",
      days30: "30 T",
      signed: "Signiert",
      created: "Erstellt",
      totalSigned: "Signiert gesamt",
      totalCreated: "Erstellt gesamt",
      avgSigned: "Ø Signiert / Tag",
      showTable: "Datentabelle anzeigen",
      day: "Tag",
      summary:
        "Review-Durchsatz über {days} Tage: {signed} signiert, {created} erstellt, Ø {avg} signiert pro Tag.",
    },
  },
  patients: {
    kicker: "Mandant · {clinic}",
    title: "Patienten",
    count: { one: "{n} Patientin", other: "{n} Patienten" },
    lead: "· tenant-bezogen, RLS-geschützt · pseudonymisierte, synthetische Beispieldaten.",
    chips: {
      total: { label: "Gesamt", help: "Im Mandanten · RLS-geschützt" },
      withReport: {
        label: "Mit Bericht",
        help: "Mindestens ein Berichtsentwurf",
      },
      open: {
        label: "Offene Assessments",
        help: "Klinische Prüfung ausstehend",
      },
      quality: {
        label: "Ø Datenqualität",
        help: "Kein Datenqualitätsmodell (Gate G1)",
      },
    },
    notAvailable: "n. v.",
    gatedTitle: "Kein zugelassener Echtdaten-Indikator (ADR-0006)",
    directory: {
      title: "Patientenverzeichnis",
      note: "Pseudonymisiert · keine automatische Diagnose oder Therapieempfehlung. Risiko- und Datenqualitäts-Spalten sind in der Echtdaten-Ansicht deaktiviert (kein zugelassener Quell-/Modellwert — ADR-0006).",
    },
    tabs: {
      all: "Alle",
      open: "Offene Reviews",
      released: "Freigegeben",
      none: "Ohne Bericht",
    },
    search: "Patient oder ID suchen",
    emptyTitle: "Noch keine Patientinnen und Patienten angelegt",
    emptyNote:
      "Legen Sie die erste Akte an — geführt in drei Schritten, mit Duplikatprüfung und dokumentierter Einwilligung.",
    firstRecord: "Erste Akte anlegen",
    columns: {
      patient: "Patient",
      age: "Alter",
      risk: "Risiko",
      quality: "Datenqualität",
      lastAssessment: "Letztes Assessment",
      status: "Status",
    },
    openRow: "Patient {name}, {ref} öffnen",
    noneTitle: "Keine Patienten in dieser Ansicht",
    noneNote: "Wählen Sie einen anderen Filter oder ändern Sie die Suche.",
    showing: "Zeige {shown} von {total}",
    loading: "Patientenverzeichnis wird geladen …",
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
      "Englisch wird Seite für Seite ergänzt: die Navigation, die Anmeldung, die Übersicht, die Patientenliste und diese Übersicht der Einstellungen sind umgestellt; der Dialog „Patient hinzufügen“ und alle übrigen Seiten erscheinen vorerst auf Deutsch.",
    selected: "ausgewählt",
    choose: "Sprache der Oberfläche",
  },
};

// The same shape with any wording in it.
type Wording<T> = {
  [K in keyof T]: T[K] extends string ? string : Wording<T[K]>;
};
export type Messages = Wording<typeof de>;
