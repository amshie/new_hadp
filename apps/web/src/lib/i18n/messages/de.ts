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
  // The dialog to add a patient (components/vitabahn/AddPatientDialog.tsx) and the server
  // actions behind it (app/patients/actions.ts). The wording of the consent purposes is not
  // here: it is versioned text (lib/consentCopy.ts) and stays as it was recorded.
  addPatient: {
    open: "Patient hinzufügen",
    subtitle: "Synthetische Demodaten · kein realer Patient.",
    steps: "Schritte",
    stepNames: {
      identity: "Identität",
      consent: "Einwilligung",
      review: "Prüfung",
    },
    stepLabel: "{n}. {label}",
    stepDone: "{n}. {label} – abgeschlossen",
    optional: "(optional)",
    cancel: "Abbrechen",
    back: "Zurück",
    next: "Weiter",
    close: "Schließen",
    openRecord: "Akte öffnen",
    discard: {
      title: "Eingaben verwerfen?",
      note: "Die bisherigen Angaben werden nicht gespeichert.",
      keep: "Weiter bearbeiten",
      confirm: "Verwerfen",
    },
    identity: {
      title: "Identität & Stammdaten",
      name: "Name",
      namePlaceholder: "z. B. Maria Beispiel",
      dob: "Geburtsdatum",
      ref: "Externe ID",
      refPlaceholder: "z. B. SYN-0042",
      refHint: "Referenz Ihres Praxissystems.",
      duplicateNote:
        "Vor dem Anlegen wird im Mandanten auf mögliche Duplikate geprüft.",
    },
    consent: {
      title: "Einwilligungen",
      note: "Vor Ort erteilte Einwilligungen werden mit Zeitstempel, Zweck und erfassender Person dokumentiert (unveränderliches Protokoll). Alternativ kann die Person sie später selbst über den Einladungslink erteilen.",
      channel:
        "Erfassung: persönlich vor Ort · Zweckkatalog der Pilotumgebung (synthetische Daten).",
    },
    review: {
      title: "Prüfen & Bestätigen",
      name: "Name",
      dob: "Geburtsdatum",
      age: { one: "· {n} Jahr", other: "· {n} Jahre" },
      ref: "Externe ID",
      consents: "Einwilligungen",
      noConsents: "Keine dokumentiert",
      create: "Patient anlegen",
      creating: "Wird angelegt …",
    },
    duplicates: {
      running: "Duplikatprüfung läuft …",
      unavailable: "Duplikatprüfung derzeit nicht verfügbar.",
      retry: "Erneut prüfen",
      strong: "Möglicherweise bereits vorhanden",
      similar: "Ähnlicher Eintrag im Mandanten",
      match: {
        external_ref: "Gleiche externe ID",
        name_dob: "Name + Geburtsdatum",
        name: "Gleicher Name",
      },
      createAnyway:
        "Trotzdem neu anlegen — es handelt sich um eine andere Person.",
      none: "Keine Übereinstimmungen im Mandanten gefunden.",
    },
    done: {
      title: "Patient angelegt",
      summary: "· synthetischer Demodatensatz · {consents}.",
      consents: {
        one: "{n} Einwilligung dokumentiert",
        other: "{n} Einwilligungen dokumentiert",
      },
      noConsents: "keine Einwilligungen dokumentiert",
      inviteTitle: "Einladung zur eigenständigen Einwilligung",
      inviteNote:
        "Die Person kann Einwilligungen auch selbst über einen einmaligen Einladungslink erteilen.",
      inviteLink: "Einladungslink",
      copy: "Kopieren",
      copied: "Kopiert",
      validUntil:
        "Gültig bis {when} · wird nur einmal angezeigt — bitte sicher und persönlich übermitteln.",
      createLink: "Einladungslink erstellen",
      creatingLink: "Wird erstellt …",
      another: "Weitere Person anlegen",
    },
    errors: {
      nameRequired: "Bitte einen Namen angeben.",
      nameTooLong: "Der Name darf höchstens 200 Zeichen haben.",
      dobInvalid: "Bitte ein gültiges Geburtsdatum angeben.",
      dobFuture: "Das Geburtsdatum darf nicht in der Zukunft liegen.",
      dobTooEarly: "Bitte ein Geburtsdatum ab {year} angeben.",
      refTooLong: "Die externe ID darf höchstens 120 Zeichen haben.",
      signInAgain: "Nicht berechtigt. Bitte erneut anmelden.",
      duplicate:
        "Im Mandanten existiert bereits ein Eintrag mit diesen Angaben.",
      checkInput: "Anlegen fehlgeschlagen. Bitte Eingaben prüfen.",
      failed: "Anlegen fehlgeschlagen. Bitte erneut versuchen.",
    },
    invitationErrors: {
      invalidPatient: "Ungültige Patientenreferenz.",
      notAllowed: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      tooMany: "Zu viele Einladungen. Bitte später erneut.",
      failed: "Einladung fehlgeschlagen. Bitte erneut versuchen.",
    },
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
      "Englisch wird Seite für Seite ergänzt: die Navigation, die Anmeldung, die Übersicht, die Patientenliste und diese Übersicht der Einstellungen sind umgestellt; alle übrigen Seiten erscheinen vorerst auf Deutsch. Der Wortlaut der Einwilligungszwecke bleibt Deutsch.",
    selected: "ausgewählt",
    choose: "Sprache der Oberfläche",
  },
};

// The same shape with any wording in it.
type Wording<T> = {
  [K in keyof T]: T[K] extends string ? string : Wording<T[K]>;
};
export type Messages = Wording<typeof de>;
