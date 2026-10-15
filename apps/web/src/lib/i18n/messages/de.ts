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
    clinic: "Praxis: ",
    toggleTheme: "Theme wechseln",
    skipLink: "Zum Hauptinhalt springen",
    brandAria: "HADP Übersicht",
    menu: "Menü",
    closeMenu: "Menü schließen",
  },
  roles: {
    owner: "Inhaber",
    clinician: "Ärztin/Arzt",
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
    errorNoClinic: "Für dieses Konto ist keine Praxis eingerichtet.",
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
    lead: {
      none: "Nichts wartet gerade auf Sie.",
      one: "{n} Vorgang wartet auf Sie.",
      other: "{n} Vorgänge warten auf Sie.",
    },
    // A sentence for the reader's role, after the count.
    leadRole: {
      clinician: "Quellengebundene Entwürfe werden vor jeder Freigabe geprüft.",
      medical_director:
        "Freigegeben wird nur, was klinisch geprüft und genehmigt ist.",
      assistant:
        "Prüfen, Genehmigen und Freigeben bleiben den klinischen Rollen.",
      owner: "Für die Praxis: Team, Löschanträge und Vorbereitungszeit.",
    },
    synthetic: "Synthetische Beispieldaten.",
    statband: {
      label: "Kennzahlen",
      openReviews: {
        label: "Offene Reviews",
        help: "Klinische Prüfung ausstehend",
      },
      toRelease: {
        label: "Zur Freigabe",
        help: "Warten auf ärztliche Freigabe",
      },
      valuesInReview: {
        label: "Werte in Prüfung",
        help: "Review-Queue, noch nicht veröffentlicht",
      },
      released: {
        label: "Freigegeben · {days}\u00a0T",
        help: "Je Tag, der älteste links",
        unavailable: "Derzeit nicht abrufbar",
      },
      patients: {
        label: "Patienten",
        help: "{withReport} mit Bericht · {without} ohne Entwurf",
      },
    },
    today: {
      title: "Heute",
      note: "Nach Arbeitsstand und Alter geordnet, nicht nach klinischer Dringlichkeit. Die Reihenfolge ist Workflow, kein Urteil.",
      asOf: "Stand {time}",
      tiers: {
        now: { title: "Jetzt", tag: "wartet auf Sie" },
        soon: { title: "Demnächst", tag: "neue Werte" },
        fyi: { title: "Zur Kenntnis", tag: "keine Aktion nötig" },
      },
      count: { one: "{n} Eintrag", other: "{n} Einträge" },
      empty: {
        now: "Nichts wartet auf Ihre Rolle.",
        soon: "Keine neuen Werte und keine Akte ohne Entwurf.",
        fyi: "Nichts Neues in den letzten 7 Tagen.",
      },
      waited: "wartet seit {since}",
      kinds: {
        review_draft: {
          what: "Bericht v{version}: klinische Prüfung offen",
          action: "Prüfen",
        },
        rework_rejected: {
          what: "Bericht v{version} zurückgewiesen: Überarbeitung offen",
          action: "Überarbeiten",
        },
        decide_values: {
          what: {
            one: "{n} Wert wartet auf Entscheidung",
            other: "{n} Werte warten auf Entscheidung",
          },
          action: "Entscheiden",
        },
        release: {
          what: "Bericht v{version} genehmigt: Freigabe offen",
          action: "Öffnen",
        },
        decide_deletion: {
          what: "Antrag auf Löschung: Entscheidung offen",
          action: "Entscheiden",
        },
        execute_deletion: {
          what: "Löschung genehmigt, noch nicht ausgeführt",
          action: "Anzeigen",
        },
        upload_values: {
          what: "Noch keine Werte in der Akte",
          action: "Akte öffnen",
        },
        invitation_open: {
          title: "Einladung · {role}",
          what: "Noch nicht eingelöst · läuft ab am {until}",
          action: "Anzeigen",
        },
        prep_baseline: {
          title: "Vorbereitungszeit",
          what: "Der Ausgangswert der Praxis ist noch nicht erfasst",
          action: "Erfassen",
        },
        prep_follow_up: {
          title: "Vorbereitungszeit",
          what: "Seit über {days} Tagen keine neue Angabe",
          action: "Erfassen",
        },
        values_since_run: {
          what: {
            one: "{n} Wert nach der letzten Interpretation empfangen",
            other: "{n} Werte nach der letzten Interpretation empfangen",
          },
          detail: "Letzte Interpretation: Lauf {run}",
          action: "Akte öffnen",
        },
        no_draft: {
          what: {
            one: "{n} veröffentlichter Wert, noch kein Entwurf",
            other: "{n} veröffentlichte Werte, noch kein Entwurf",
          },
          action: "Akte öffnen",
        },
        approved_waiting: {
          what: "Bericht v{version} genehmigt: wartet auf die ärztliche Freigabe",
          action: "Anzeigen",
        },
        deletion_waiting: {
          what: "Antrag auf Löschung: wartet auf die Ärztliche Leitung",
          action: "Anzeigen",
        },
        released_recently: {
          title: {
            one: "{n} Bericht freigegeben",
            other: "{n} Berichte freigegeben",
          },
          ref: "letzte 7 Tage",
          action: "Arbeitsliste",
        },
      },
    },
    // Seit zuletzt (docs/notes/0024): what arrived or moved in a record since the person
    // last opened it. The opening sets the mark; a step of their own is not news to them.
    changes: {
      title: "Seit zuletzt",
      note: "Was in einer Akte ankam oder sich bewegte, seit Sie sie zuletzt geöffnet haben. Das Öffnen der Akte setzt den Stand; eigene Schritte zählen nicht.",
      count: { one: "{n} Akte mit Neuem", other: "{n} Akten mit Neuem" },
      empty: "Nichts Neues in den Akten, die Sie bereits geöffnet haben.",
      neverOpened: {
        one: "{n} Akte haben Sie noch nie geöffnet.",
        other: "{n} Akten haben Sie noch nie geöffnet.",
      },
      unavailable: "Derzeit nicht abrufbar.",
      opened: "zuletzt geöffnet {since}",
      values: { one: "{n} neuer Wert", other: "{n} neue Werte" },
      pending: { one: "{n} Wert in Prüfung", other: "{n} Werte in Prüfung" },
      run: "Interpretation: Lauf {n} erfasst",
      report: "Bericht v{version}: {status}",
      changed: "Neuestes {since}",
      action: "Akte öffnen",
      showAll: "Alle {n} anzeigen",
      showFewer: "Weniger anzeigen",
    },
    worklist: {
      title: "Arbeitsliste",
      note: "Nach Berichtsstatus · keine automatische Diagnose oder Therapieempfehlung.",
      tabs: {
        open: "Offene Reviews",
        approved: "Zur Freigabe",
        released: "Freigegeben",
        rejected: "Zurückgewiesen",
        none: "Kein Entwurf",
        all: "Alle",
      },
      search: "Patient oder ID suchen",
      prepLink: "Vorbereitung je Akte",
      columns: {
        patient: "Patient",
        state: "Stand",
        next: "Nächster Schritt",
        values: "Werte",
        updated: "Aktualisiert",
      },
      next: {
        clinical_review: { title: "Klinische Prüfung", who: "durch {role}" },
        release: { title: "Freigabe", who: "durch {role}" },
        rework: {
          title: "Überarbeitung",
          who: "eine neue Fassung nach der Zurückweisung",
        },
        none: { title: "Kein Schritt offen", who: "freigegeben {since}" },
        draft: {
          title: "Entwurf erstellen",
          who: "aus den veröffentlichten Werten",
        },
        import: {
          title: "Werte einlesen",
          who: "noch keine Werte in der Akte",
        },
      },
      inReview: "{n} in Prüfung",
      openRow: "Patient {name}, {ref} öffnen",
      emptyTitle: "Keine passenden Vorgänge",
      emptyNote: "Ändern Sie den Filter oder den Suchbegriff.",
    },
    practice: {
      title: "Praxis · {days} Tage",
      note: "Entwürfe erstellt und Reviews signiert, je Kalenderwoche · echte Zeitstempel.",
      range: "{from} – {to}",
      week: "KW {week}",
      created: "Erstellt",
      signed: "Signiert",
      released: "Freigegeben",
      chartLabel:
        "Entwürfe erstellt und Reviews signiert, je Kalenderwoche. Jede Zahl steht auch in der Tabelle.",
      showTable: "Als Tabelle anzeigen",
      columns: {
        week: "Kalenderwoche",
        days: "Tage im Zeitraum",
      },
      median: "Median vom ersten Entwurf bis zur Genehmigung · 30 T",
      medianNote: "Durchlaufzeit, keine Arbeitszeit",
      tooFew: "Ab {minimum} Berichten · bisher {n}",
      change: "Vorbereitungszeit je Termin",
      changeNote:
        "Letzte Folgeangabe gegenüber dem Ausgangswert ({from} → {to} min, Angaben der Praxis) · Pilotkriterium: mindestens −{target} %",
      changeNoteNone:
        "Letzte Folgeangabe gegenüber dem Ausgangswert, beide Angaben der Praxis",
      noFollowUp: "Noch keine Folgeangabe",
      baseline: "Ausgangswert der Praxis",
      baselineNote: "Selbstangabe, Median je Termin",
      baselineValue: "{n} min",
      noBaseline: "Noch nicht erfasst",
      foot: "Zwei verschiedene Größen; sie werden nicht miteinander verrechnet. Mehr unter Einstellungen › Vorbereitungszeit.",
      unavailable: "Die Zahlen der Praxis sind derzeit nicht abrufbar.",
    },
    duration: {
      minutes: "{n} Min.",
      hours: "{n} Std.",
      days: "{n} T",
    },
    data: {
      title: "Datenlage",
      note: {
        one: "Zählung über {n} Beobachtung · keine Qualitätsbewertung.",
        other: "Zählung über {n} Beobachtungen · keine Qualitätsbewertung.",
      },
      published: "Veröffentlicht",
      withReference: "Mit Quellreferenzintervall",
      withKpi: "Einem Katalogmarker zugeordnet",
      latest: "Neueste Beobachtung",
      unavailable: "Die Datenlage ist derzeit nicht abrufbar.",
    },
    sources: {
      title: "Quellen",
      names: {
        csv: "CSV (HADP-Layout)",
        ldt2: "LDT 2",
        ldt3: "LDT 3",
        other: "Von Hand oder über die Schnittstelle",
        wearables: "Wearables",
      },
      last: {
        one: "Zuletzt {when} · {n} Zeile",
        other: "Zuletzt {when} · {n} Zeilen",
      },
      neverFile: "Noch keine Datei eingelesen",
      neverOther: "Noch nichts erfasst",
      wearablesNote: "Keine Anbindung in Pilotphase 1",
      state: {
        used: "genutzt",
        ready: "bereit",
        none: "nicht verbunden",
      },
      unavailable: "Die Quellen sind derzeit nicht abrufbar.",
    },
    activity: {
      title: "Letzte Aktivität",
      noteClinic:
        "Aus dem Audit-Protokoll der Praxis, ohne Lesezugriffe und Anmeldungen · dieselben Bezeichnungen wie unter Einstellungen › Audit-Protokoll.",
      noteOwn:
        "Ihre eigenen Vorgänge, ohne Lesezugriffe und Anmeldungen. Das vollständige Protokoll liest der Inhaber.",
      open: "Protokoll öffnen",
      empty: "Noch keine Vorgänge.",
      unavailable: "Die Aktivität ist derzeit nicht abrufbar.",
    },
  },
  // The practice view: the page before a visit for every record at once (docs/notes/0023).
  practicePrep: {
    kicker: "Praxis · {clinic}",
    title: "Vorbereitung je Akte",
    lead: "Was seit der letzten Interpretation in jeder Akte hinzugekommen ist, was alt ist und was fehlt – gezählt, nicht bewertet. Jede Zeile führt zur Vorbereitungsseite der Akte.",
    note: "Reihenfolge nach Berichtsstatus; jede Spalte lässt sich sortieren. Keine automatische Diagnose oder Therapieempfehlung.",
    count: { one: "{n} Akte", other: "{n} Akten" },
    shown: "{shown} von {total} Akten",
    search: "Patient oder ID suchen",
    filters: {
      all: "Alle",
      newValues: "Neue Werte",
      outside: "Außerhalb des Quellreferenzintervalls",
      stale: "Älter als {days} Tage",
      missing: "Kernmarker ohne Wert",
      pending: "In Prüfung",
      noVerdict: "Ohne Urteil",
      noRun: "Ohne Interpretation",
    },
    columns: {
      patient: "Patient",
      status: "Stand",
      run: "Letzte Interpretation",
      newValues: "Neu seit Lauf",
      outside: "Außerhalb",
      stale: "Älter als {days} T",
      missing: "Ohne Wert",
      pending: "In Prüfung",
      noVerdict: "Ohne Urteil",
    },
    sort: "Nach {column} sortieren",
    sortedBy: "Sortiert nach {column}",
    run: "Lauf {n} · {date}",
    noRun: "Keine",
    newOutside: "{n} außerhalb",
    open: "Vorbereitung für {name} öffnen",
    empty: "Keine Akte entspricht dem Filter.",
    none: "Noch keine Akte in dieser Praxis.",
    coreNote:
      "Von {n} Kernmarkern des Katalogs. Ein Wert steht, wenn er veröffentlicht ist und keine Laborkorrektur ihn ersetzt hat.",
  },
  patients: {
    kicker: "Praxis · {clinic}",
    title: "Patienten",
    count: { one: "{n} Patientin", other: "{n} Patienten" },
    lead: "· pseudonymisierte, synthetische Beispieldaten.",
    prepLink: "Vorbereitung je Akte",
    chips: {
      total: { label: "Gesamt", help: "In dieser Praxis" },
      withReport: {
        label: "Mit Bericht",
        help: "Mindestens ein Berichtsentwurf",
      },
      open: {
        label: "Offene Assessments",
        help: "Klinische Prüfung ausstehend",
      },
    },
    directory: {
      title: "Patientenverzeichnis",
      note: "Pseudonymisiert · keine automatische Diagnose oder Therapieempfehlung.",
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
        "Vor dem Anlegen wird in dieser Praxis auf mögliche Duplikate geprüft.",
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
      similar: "Ähnlicher Eintrag in dieser Praxis",
      match: {
        external_ref: "Gleiche externe ID",
        name_dob: "Name + Geburtsdatum",
        name: "Gleicher Name",
      },
      createAnyway:
        "Trotzdem neu anlegen — es handelt sich um eine andere Person.",
      none: "Keine Übereinstimmungen in dieser Praxis gefunden.",
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
        "In dieser Praxis existiert bereits ein Eintrag mit diesen Angaben.",
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
  // The patient page (app/patients/[id]): its header and actions, the data coverage, the three
  // cards (consent, laboratory files, data export), its dialogs, and what its server actions
  // answer. NOT here, and German on the page whatever the interface says: the closed
  // vocabularies the page shows — the names of the six domain axes, follow-up adequacy, the
  // position against the reference interval, the comparability notes (ADR-0007: their English
  // needs the medical director) — and the wording of the consent purposes (versioned text).
  patientPage: {
    // The page in three tabs (docs/notes/0025).
    tabs: {
      label: "Bereiche der Akte",
      vorbereitung: "Vorbereitung",
      werte: "Werte",
      akte: "Akte",
    },
    back: "Zurück zu Patienten",
    cancel: "Abbrechen",
    close: "Schließen",
    notAllowed: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
    invalidPatient: "Ungültige Patientenreferenz.",
    recordUnavailable: "Diese Akte ist nicht verfügbar.",
    erased: {
      title: "Dieser Datensatz wurde gelöscht",
      note: "Die Daten dieser Person wurden anonymisiert und unwiderruflich entfernt (Beobachtungen, Dokumente und Berichte). Der Eintrag bleibt nur als Nachweis im Prüfprotokoll bestehen.",
    },
    // Where the latest report stands — a workflow state, never a clinical one.
    reportStatus: {
      draft: "Klinische Prüfung offen",
      approved: "An ärztliche Freigabe weitergeleitet",
      released: "Freigegeben",
      rejected: "Zurückgewiesen",
      none: "Kein Entwurf",
    },
    age: { one: "{n} Jahr", other: "{n} Jahre" },
    ageUnknown: "Alter unbekannt",
    noReport: "Kein Bericht",
    born: "geb. {date}",
    lastValues: "Letzte Werte vom {date}",
    noValuesYet: "Noch keine Werte",
    lastRun: "Letzte Interpretation: Lauf {n} · {date}",
    noRunYet: "Noch keine Interpretation",
    reportVersion: "Bericht · v{version}",
    actions: {
      openReport: "Bericht öffnen",
      createDraft: "Berichtsentwurf erstellen",
      creatingDraft: "Entwurf wird erstellt …",
      recordInterpretation: "Interpretation erfassen",
      invite: "Patient einladen",
      requestDeletion: "Löschung beantragen",
    },
    coverage: {
      title: "Datenlage",
      note: "Deterministisch aus den Beobachtungen · keine klinische Qualitätsbewertung.",
      observations: "Beobachtungen",
      published: "veröffentlicht",
      withReference: "mit Referenz",
      latest: "letzte Messung",
      today: "heute",
      days: "{n} T",
    },
    // The page before a visit: facts since the latest interpretation run, each a line that
    // leads to its value (docs/notes/0022). Counted and copied, never rated.
    visitPrep: {
      title: "Vorbereitung",
      sinceRun: "Seit Lauf {n} · erfasst am {date}",
      noRun:
        "Noch keine Interpretation erfasst – es gibt kein „seit“, nur den heutigen Stand",
      note: "Zusammengestellt aus den erfassten Werten; jede Zeile führt zum Wert. Keine automatische Diagnose oder Therapieempfehlung.",
      open: "Als Seite öffnen",
      print: "Drucken",
      backToRecord: "Zur Akte",
      pageTitle: "Vorbereitung · {name}",
      quiet: "Nichts hinzugekommen, nichts gewechselt, nichts offen.",
      quietNoRun: "Keine Werte erfasst.",
      // What stands today (docs/notes/0025): counts and positions, the clinician's verdicts.
      today: {
        title: "Lage heute",
        asOf: "neueste Messung vom {date}",
        noValues: "Noch kein veröffentlichter Wert.",
        tally: {
          withValue: "Marker mit Wert",
          outside: "außerhalb des Intervalls",
          within: "im Intervall",
          noReference: "ohne Referenz der Quelle",
          derived: "berechnet, nicht gemessen",
          pending: "in Prüfung · nicht veröffentlicht",
        },
        outsideTitle: "Außerhalb des Quellreferenzintervalls",
        ofAll: "{n} von {total}",
        noneOutside:
          "Kein Marker, dessen letzter Wert außerhalb des Quellreferenzintervalls liegt.",
        columns: {
          marker: "Marker",
          trend: "Verlauf",
          value: "Letzter Wert",
          reference: "Ref",
          position: "Lage",
          measured: "Gemessen",
        },
        trend: { one: "Verlauf: {n} Messung", other: "Verlauf: {n} Messungen" },
        measurements: { one: "{n} Messung", other: "{n} Messungen" },
        trendNote:
          "Verlauf: ein Punkt im Intervallband je Messung; eine Linie nur zwischen Werten, die die Plattform als vergleichbar erkannt hat.",
        noReferenceNote:
          "{n} Werte ohne Referenzintervall der Quelle (z. B. Blutdruck, Puls, Körpermaße) stehen in der Werteliste, nicht hier.",
        toValues: "Zu den Werten",
        verdictsTitle: "Letzte Interpretation",
        runMeta: "Lauf {n} · erfasst am {date}",
        noRunMeta: "noch keine erfasst",
        verdictColumns: {
          domain: "Domäne",
          outside: "Außerh.",
          cis: "CIS",
          actionability: "Actionability",
          followup: "Follow-up",
        },
        withValue: "{x} von {n} mit Wert",
        noVerdict: "kein Urteil erfasst",
        verdictsNote:
          "Urteile der Ärztin oder des Arztes, wie erfasst · keine Berechnung.",
        verdictsCounts:
          "{inadequate} mit inadäquatem Follow-up · {unassessed} nicht bewertet.",
      },
      since: {
        title: "Seit Lauf {n} · {date}",
        noRunTitle: "Seit der letzten Interpretation",
        none: "Keine neuen Werte seit der letzten Interpretation.",
        noRun: "Noch keine Interpretation erfasst.",
      },
      gaps: {
        title: "Alt und fehlend",
        note: "von {n} Kernmarkern des Katalogs: älter als {days} Tage oder ohne veröffentlichten Wert – als Vorlage für den nächsten Laborauftrag",
        allFrom: "alle vom {date}",
        from: "{n} vom {date}",
        never: "nie erfasst",
        show: { one: "{n} Marker anzeigen", other: "{n} Marker anzeigen" },
        hide: "Marker ausblenden",
        noneStale: "Kein Kernmarker mit letztem Wert älter als {days} Tage.",
        noneMissing:
          "Jeder Kernmarker des Katalogs hat einen veröffentlichten Wert.",
      },
      groups: {
        newValues: {
          one: "{n} neuer Wert seit Lauf {run}",
          other: "{n} neue Werte seit Lauf {run}",
        },
        newOutside: {
          one: "davon {n} außerhalb des Quellreferenzintervalls",
          other: "davon {n} außerhalb des Quellreferenzintervalls",
        },
        moved: {
          one: "{n} Marker mit gewechselter Lage",
          other: "{n} Marker mit gewechselter Lage",
        },
        stale: {
          one: "{n} Kernmarker mit letztem Wert älter als {days} Tage",
          other: "{n} Kernmarker mit letztem Wert älter als {days} Tage",
        },
        missing: {
          one: "{n} Kernmarker ohne veröffentlichten Wert",
          other: "{n} Kernmarker ohne veröffentlichten Wert",
        },
        pending: { one: "{n} Wert in Prüfung", other: "{n} Werte in Prüfung" },
        unassigned: {
          one: "{n} Wert ohne Katalogmarker",
          other: "{n} Werte ohne Katalogmarker",
        },
        noVerdict: {
          one: "{n} Domäne ohne Urteil in Lauf {run}",
          other: "{n} Domänen ohne Urteil in Lauf {run}",
        },
        citesReplaced: {
          one: "{n} Domäne stützt sich auf einen vom Labor korrigierten Wert",
          other:
            "{n} Domänen stützen sich auf einen vom Labor korrigierten Wert",
        },
      },
      line: {
        // "LDL-Cholesterin 142 mg/dL · Referenz der Quelle 0–115 · gemessen am 02.09.2026"
        reference: "Referenz der Quelle {range}",
        noReference: "ohne Referenz der Quelle",
        measured: "gemessen am {date}",
        derived: "berechnet aus Werten bis {date}",
        moved: "{from} → {to}",
        movedDays: "vorher {previous}, jetzt {latest}",
        lastValue: "letzter Wert vom {date}",
        unassigned: "ohne Katalogmarker",
        pendingNote:
          "In der Review-Queue – erst nach einer Entscheidung veröffentlicht.",
        unassignedNote: "In der Domänenübersicht unter „Ohne Katalogmarker“.",
        open: "Marker {name} öffnen",
        toDomain: "Zur Domäne {axis}",
        toQueue: "Zur Review-Queue",
      },
    },
    // Before a visit: counts of recorded values, each a filter of the domain lists.
    prep: {
      title: "Vor dem Termin",
      note: "Gezählt aus den erfassten Werten. Jede Zahl filtert die Domänenlisten darunter; keine ist eine Bewertung.",
      lastRun: "Letzte Interpretation: Lauf {n} · {date}",
      noRun: "Noch keine Interpretation erfasst",
      facts: {
        since_run: {
          label: {
            one: "Wert seit der letzten Interpretation",
            other: "Werte seit der letzten Interpretation",
          },
          note: "Empfangen nach dem {date}",
          noRun: "Ohne Interpretation gibt es kein „seit“",
        },
        outside: {
          label: {
            one: "Marker außerhalb des Quellreferenzintervalls",
            other: "Marker außerhalb des Quellreferenzintervalls",
          },
          note: "Nach dem letzten veröffentlichten Wert",
        },
        pending: {
          label: { one: "Wert in Prüfung", other: "Werte in Prüfung" },
          note: "Nicht veröffentlicht, in keiner Veränderung berechnet",
        },
        missing: {
          label: {
            one: "Kernmarker ohne veröffentlichten Wert",
            other: "Kernmarker ohne veröffentlichten Wert",
          },
          note: "Von {n} Kernmarkern des Katalogs",
        },
      },
      filtered: {
        since_run:
          "Angezeigt werden nur Marker mit einem Wert, der nach der letzten Interpretation empfangen wurde.",
        outside:
          "Angezeigt werden nur Marker, deren letzter veröffentlichter Wert außerhalb des Quellreferenzintervalls liegt.",
        pending: "Angezeigt werden nur Marker mit einem Wert in Prüfung.",
        missing: "Angezeigt werden nur Kernmarker ohne veröffentlichten Wert.",
      },
      showAll: "Alle Marker anzeigen",
    },
    domains: {
      title: "Domänen",
      note: "Die sechs Domänen des Interpretationsmodells. Werte gehören über den KPI-Katalog zu einer Domäne – auch bevor eine Interpretation erfasst ist.",
      go: "{axis}: zur Markerliste",
      coreMarkers: { one: "{n} Kernmarker", other: "{n} Kernmarker" },
      coverage: "{x} von {n} mit veröffentlichtem Wert",
      noCore: "Keine Kernmarker im Katalog",
      noValue: "Noch kein veröffentlichter Wert",
      outside: {
        one: "{n} Marker außerhalb des Quellreferenzintervalls",
        other: "{n} Marker außerhalb des Quellreferenzintervalls",
      },
      outsideNone: "Kein letzter Wert außerhalb des Quellreferenzintervalls",
      pending: { one: "{n} Wert in Prüfung", other: "{n} Werte in Prüfung" },
      pendingNone: "Nichts in Prüfung",
      latest: "Letzter veröffentlichter Wert vom {date}",
      // The clinician's own verdict, quoted — never derived here.
      interpretation: "Ärztliche Interpretation",
      // The state of a run on a domain's card — workflow, not a verdict.
      reviewed: "Geprüft",
      draft: "Entwurf",
      none: "Kein Lauf",
      run: "Lauf {n} · erfasst am {date}",
      // The name of the fact; its value is a closed vocabulary and stays German.
      adequacy: "Follow-up-Adäquanz:",
      sinceRun: {
        one: "{n} Wert nach dieser Interpretation empfangen",
        other: "{n} Werte nach dieser Interpretation empfangen",
      },
      citesReplaced:
        "Stützt sich auf einen vom Labor korrigierten Wert — Interpretation prüfen.",
      notInterpreted: "Noch nicht interpretiert",
    },
    evidence: {
      eyebrow: "Domäne",
      note: "Quellengebundene Beobachtungen · Lage relativ zum Quellreferenzintervall · keine automatische Diagnose oder Therapieempfehlung.",
      counts: "{x} von {n} Kernmarkern mit veröffentlichtem Wert",
      filteredCount: {
        one: "{n} Zeile im Filter",
        other: "{n} Zeilen im Filter",
      },
      columns: {
        marker: "Marker",
        value: "Letzter Wert",
        change: "Veränderung",
        position: "Lage z. Referenz",
        bar: "Referenzlage",
        measured: "Gemessen",
      },
      open: "Marker {name} öffnen",
      // The catalog's name for a marker no source has named for this record.
      catalogName: "Name im Katalog",
      measurementClass: {
        laboratory: "Labor",
        vital_sign: "Vitalparameter",
        anthropometric: "Anthropometrie",
        body_composition: "Körperzusammensetzung",
        functional_test: "Funktionstest",
        wearable: "Wearable",
        imaging: "Bildgebung",
        derived: "Berechnet",
        omics: "Omics",
      },
      missing: "Kein Wert erfasst",
      showMissing: {
        one: "{n} Kernmarker ohne Wert anzeigen",
        other: "{n} Kernmarker ohne Wert anzeigen",
      },
      hideMissing: "Kernmarker ohne Wert ausblenden",
      pending: { one: "{n} Wert in Prüfung", other: "{n} Werte in Prüfung" },
      corrected: "vom Labor korrigiert",
      // A value the platform computed from other values of the record; no source reported it.
      derived: "berechnet",
      derivedTitle:
        "Von der Plattform aus anderen Werten dieser Akte berechnet – kein gemessener Wert.",
      noChange: "—",
      ago: {
        today: "heute",
        days: { one: "vor {n} Tag", other: "vor {n} Tagen" },
        months: { one: "vor {n} Monat", other: "vor {n} Monaten" },
      },
      alsoRelevant: "Auch hier relevant",
      alsoRelevantNote:
        "Geführt und gezählt in ihrer eigenen Domäne; hier zur Übersicht.",
      superseded: "durch Laborkorrektur ersetzt",
      inputReplaced: "Eingangswert durch Laborkorrektur ersetzt",
      empty: "Keine Beobachtungen in dieser Domäne.",
      emptyFilter: "Kein Marker dieser Domäne passt zum Filter.",
      noScale: "keine Skala",
      reference: "Ref {range}",
    },
    // A marker's history: its sparkline in the domain list and its chart in the dialog.
    history: {
      column: "Verlauf",
      title: "Verlauf",
      chartLabel:
        "Verlauf von {name}. Jeder Wert steht auch in der Tabelle darunter.",
      summary: {
        none: "{name}: noch kein veröffentlichter Wert.",
        one: "{name}: ein veröffentlichter Wert vom {to}: {value}.",
        other:
          "{name}: {n} veröffentlichte Werte zwischen dem {from} und dem {to}; der letzte ist {value}.",
      },
      pending: {
        one: "{n} Wert ist in Prüfung.",
        other: "{n} Werte sind in Prüfung.",
      },
      replaced: {
        one: "{n} Wert wurde durch eine Laborkorrektur ersetzt.",
        other: "{n} Werte wurden durch eine Laborkorrektur ersetzt.",
      },
      notDrawn: {
        one: "{n} Wert ist nicht eingezeichnet (abgelehnt oder ohne Zahl) und steht nur in der Tabelle.",
        other:
          "{n} Werte sind nicht eingezeichnet (abgelehnt oder ohne Zahl) und stehen nur in der Tabelle.",
      },
      legend: {
        value: "Veröffentlichter Wert",
        joined: "Linie: Veränderung berechnet",
        interval: "Quellreferenzintervall, je Wert",
        outside: "Außerhalb des Quellreferenzintervalls",
        pending: "In Prüfung",
        replaced: "Durch Laborkorrektur ersetzt",
      },
      today: "heute",
      foot: "Nur erfasste Werte: keine Trendlinie, keine Glättung, keine Prognose. Eine Linie verbindet zwei Werte nur, wenn die Plattform zwischen ihnen eine Veränderung berechnet hat.",
    },
    unassigned: {
      title: "Keinem Katalogmarker zugeordnet",
      note: "Werte, die der Import keinem Marker zuordnen konnte. Sie bleiben hier sichtbar und werden in der Review-Queue entschieden; bis dahin gehören sie zu keiner Domäne.",
      openQueue: "Review-Queue öffnen",
    },
    // Where a value stands in the review of imported values.
    valueStatus: {
      published: "veröffentlicht",
      pending: "in Prüfung – nicht veröffentlicht",
      rejected: "im Review abgelehnt",
    },
    // How a shown value relates to what the source wrote.
    sourceNote: {
      text: {
        short: "Angabe im Wortlaut",
        full: "Aus der Angabe der Quelle liest die Plattform hier keine Zahl – etwa bei einem Textergebnis, einem Zusatz am Wert oder einer Schreibweise, die sie nicht eindeutig lesen kann. Angezeigt wird die Angabe im Wortlaut.",
      },
      converted: {
        short: "umgerechnet aus {source}",
        full: "Die Quelle nennt {source}; der Wert – und das Referenzintervall, soweit eines angezeigt ist – wurde in {unit} umgerechnet.",
        unitOfMetric: "die Einheit der Kennzahl",
      },
      source_unit: {
        short: "Einheit der Quelle",
        full: "Der Wert steht so, wie die Quelle ihn nennt, in ihrer Einheit – ein angezeigtes Referenzintervall ebenso. Der Wert ist nicht normalisiert; eine Veränderung zum Vorwert wird deshalb nicht berechnet.",
      },
      derived: {
        short: "berechnet aus {inputs}",
        full: "Kein gemessener Wert: Die Plattform hat ihn nach der Formel {formula} aus {inputs} berechnet. Keine Quelle hat ihn gemeldet.",
        otherValues: "anderen Werten dieser Akte",
        and: "und",
      },
    },
    marker: {
      kicker: "Marker-Detail ·",
      reference: "Referenz",
      change: "Veränderung",
      source: "Quelle / Code",
      status: "Review-Status",
      noPosition:
        "Für einen nicht veröffentlichten Wert wird keine Lage zum Referenzintervall angegeben.",
      positionNote:
        "Lage relativ zum Quellreferenzintervall · keine automatische Diagnose oder Therapieempfehlung.",
      // Every value of the marker, oldest last: what the latest one stands on.
      values: "Alle Werte dieses Markers",
      valueColumns: {
        measured: "Gemessen",
        value: "Wert",
        asReported: "Laut Quelle",
        reference: "Referenz der Quelle",
        status: "Status",
        change: "Veränderung",
      },
    },
    audit: {
      title: "Audit-Status",
      note: "Fortschritt von Datenerfassung bis Patientenfreigabe (aus dem Berichtsstatus abgeleitet).",
      none: "Noch kein Berichtsentwurf — der Audit-Lifecycle beginnt mit der Entwurfserstellung.",
      steps: {
        capture: { label: "Datenerfassung", done: "Werte veröffentlicht" },
        draft: { label: "Entwurf erstellt", done: "Quellengebunden" },
        clinical: {
          label: "Klinischer Review",
          done: "Signiert",
          active: "In Bearbeitung",
          pending: "Ausstehend",
          rejected: "Version zurückgewiesen",
        },
        release: {
          label: "Ärztliche Freigabe",
          done: "Abgeschlossen",
          active: "In Prüfung",
          pending: "Ausstehend",
          rejected: "Nicht erfolgt",
        },
        patient: {
          label: "Patientenfreigabe",
          done: "Freigegeben",
          pending: "Nicht möglich",
          rejected: "Zurückgewiesen — Überarbeitung nötig",
        },
      },
    },
    invite: {
      title: "Patient einladen?",
      note: "Erstellt einen einmalig einlösbaren, zeitlich begrenzten Einladungslink, über den die Einwilligung (Berichtsfreigabe) erfasst wird. Der Link wird genau einmal angezeigt. Synthetische Demo: kein realer Patient.",
      doneTitle: "Einladung erstellt — Einmal-Link",
      doneNote:
        "Den Link manuell und sicher außerhalb des Systems teilen — kein automatischer Versand. Er ist einmalig einlösbar, zeitlich begrenzt und wird nur jetzt angezeigt. Synthetische Demo: kein realer Patient.",
      link: "Einladungslink (einmalig angezeigt)",
      copy: "Link kopieren",
      copied: "Link kopiert",
      create: "Einladung erstellen",
    },
    deletion: {
      title: "Löschung beantragen",
      noteBefore:
        "Dies stellt einen Antrag auf endgültige Löschung der Daten von",
      noteAfter:
        ". Es wird nichts sofort gelöscht — die Ärztliche Leitung muss den Antrag freigeben (Vier-Augen-Prinzip), die Ausführung erfolgt gesondert und ist unwiderruflich.",
      reason: "Grund",
      // Keyed by the API's DeletionReason.
      reasons: {
        patient_request: "Betroffenenanfrage (Art. 17)",
        withdrawn_consent: "Einwilligung widerrufen",
        data_minimization: "Datenminimierung",
      },
      submit: "Löschung beantragen",
      submitting: "Wird beantragt …",
      doneTitle: "Löschantrag gestellt",
      doneNote:
        "Die Ärztliche Leitung prüft den Antrag (Vier-Augen-Prinzip). Bis zur Freigabe und gesonderten Ausführung bleibt der Datensatz unverändert. Sie finden den Antrag unter Einstellungen → Löschanträge.",
      errors: {
        invalidReason: "Ungültiger Grund.",
        alreadyOpen:
          "Für diesen Patienten besteht bereits ein offener Löschantrag.",
        failed: "Löschantrag fehlgeschlagen. Bitte erneut versuchen.",
      },
    },
    consent: {
      title: "Einwilligungen",
      note: "Stand je Zweck. Jeder Eintrag ist ein neuer, zugeordneter und auditierter Vermerk — frühere Einträge werden nie geändert.",
      readOnly:
        " Das Dokumentieren ist dem Praxisteam vorbehalten (Nur-Lese-Ansicht).",
      active: "Aktiv",
      inactive: "Nicht aktiv",
      notDocumented: "Nicht dokumentiert",
      granted: "Erteilt am {day} ({how}) · Textversion {version}",
      withdrawn: "Widerrufen am {day} ({how}) · Textversion {version}",
      channels: { in_person: "vor Ort erklärt" },
      recordGrant: "Einwilligung dokumentieren",
      recordWithdrawal: "Widerruf dokumentieren",
      // Around the name of the one purpose that is enforced, shown as it is recorded.
      footnoteBefore:
        "Synthetische Demo: Zwecke und Einwilligungstext sind Platzhalter. Technisch durchgesetzt wird derzeit nur die",
      footnoteAfter:
        "(ohne aktive Einwilligung keine Freigabe; ein Widerruf entzieht bestehende Zugriffslinks). Die übrigen Zwecke werden dokumentiert, aber noch nicht technisch durchgesetzt.",
      grantTitle: "Einwilligung dokumentieren?",
      withdrawTitle: "Widerruf dokumentieren?",
      grantNote:
        "Sie dokumentieren, dass die Person diesem Zweck vor Ort zugestimmt hat. Der Vermerk wird Ihnen zugeordnet und auditiert; er lässt sich nicht ändern, nur durch einen Widerruf ergänzen.",
      withdrawNote:
        "Sie dokumentieren, dass die Person ihre Einwilligung vor Ort widerrufen hat. Der Vermerk wird Ihnen zugeordnet und auditiert; die frühere Einwilligung bleibt als Eintrag erhalten.",
      withdrawReleaseNote:
        " Bestehende Zugriffslinks der Person werden sofort ungültig; eine neue Freigabe ist erst nach erneuter Einwilligung möglich.",
      confirmGrant: "Dokumentieren",
      errors: {
        unknownPurpose: "Unbekannter Einwilligungszweck.",
        unknownAction: "Unbekannte Aktion.",
        notSaved: "Nicht gespeichert. Bitte erneut versuchen.",
      },
    },
    lab: {
      title: "Labordaten",
      note: "Strukturierte Labordatei (CSV im HADP-Layout, LDT 2 oder LDT 3) für genau diese Akte. Die Originaldatei wird gespeichert und dann eingelesen; die Werte werden unverändert übernommen. Nicht eindeutige Werte gehen in die Review-Queue — sie werden erst nach einer klinischen Entscheidung veröffentlicht.",
      choose: "Labordatei wählen",
      noFile: "Keine Datei gewählt",
      upload: "Hochladen und einlesen",
      uploading: "Wird eingelesen …",
      readOnly:
        "Hochladen und Einlesen ist dem Praxisteam vorbehalten (Nur-Lese-Ansicht).",
      read: "Eingelesen ({parser} v{version}): ",
      readBefore:
        "Diese Datei wurde bereits eingelesen — Ergebnis des ersten Einlesens: ",
      counts: {
        published: "{n} veröffentlicht",
        review: "{n} zur Prüfung",
        duplicate: "{n} bereits vorhanden",
        notImported: "{n} nicht übernommen",
      },
      toQueue: "Zur Review-Queue",
      stored: " Die Originaldatei ist gespeichert und unten aufgeführt.",
      none: "Für diese Akte ist noch keine Labordatei gespeichert.",
      table: "Gespeicherte Labordateien",
      columns: {
        file: "Datei",
        uploaded: "Hochgeladen",
        reader: "Einleseprogramm",
        result: "Ergebnis",
      },
      storedNotRead: "Gespeichert, nicht eingelesen",
      readNow: "Einlesen",
      legend:
        "„Bereits vorhanden“: Der Wert liegt für diese Analyse und Abnahmezeit schon identisch vor und wurde nicht doppelt übernommen. „Nicht übernommen“: Ergebnis ohne Zahlenwert oder ohne Abnahmedatum (zum Beispiel Textbefund, noch ausstehend). Die Zahlen zeigen den Stand beim Einlesen.",
      errors: {
        invalidReference: "Ungültige Referenz.",
        chooseFile: "Bitte eine Datei wählen.",
        tooLarge5: "Die Datei ist zu groß (höchstens 5 MB).",
        nameTooLong: "Der Dateiname ist zu lang (höchstens 200 Zeichen).",
        uploadFailed: "Upload fehlgeschlagen. Bitte erneut versuchen.",
        tooManyUploads: "Zu viele Uploads in kurzer Zeit. Bitte kurz warten.",
        otherPatient:
          "Diese Datei ist bereits bei einer anderen Akte dieser Klinik gespeichert und wird hier nicht noch einmal angenommen.",
        empty: "Die Datei ist leer.",
        tooLarge: "Die Datei ist zu groß.",
        notText: "Die Datei ist keine lesbare Textdatei (UTF-8 erwartet).",
        wrongType:
          "Dieser Dateityp wird nicht angenommen (CSV, LDT oder Text).",
        importNotAllowed: "Das Einlesen ist Ihrer Rolle nicht erlaubt.",
        tooManyImports: "Zu viele Importe in kurzer Zeit. Bitte kurz warten.",
        importFailed: "Einlesen fehlgeschlagen. Bitte erneut versuchen.",
        line: " (Zeile {line})",
        nothingTaken: "{reason}{where} Es wurde nichts übernommen.",
        unreadableCode:
          "Die Datei konnte nicht eingelesen werden (Grund: {code}){where}. Es wurde nichts übernommen.",
        unreadable:
          "Die Datei konnte nicht eingelesen werden. Es wurde nichts übernommen.",
      },
      // Why a file was not read — keyed by the API's code.
      refusals: {
        unsupported_format:
          "Für dieses Dateiformat gibt es kein Einleseprogramm (unterstützt: CSV im HADP-Layout, LDT 2, LDT 3).",
        multiple_patients:
          "Die Datei enthält Befunde für mehr als eine Person. Eine Datei muss genau eine Person betreffen.",
        unidentified_patient:
          "Die Datei nennt nicht genau eine Person. Eine Datei muss genau eine Person betreffen.",
        patient_mismatch:
          "Die Datei nennt ein anderes Geburtsdatum als diese Akte.",
        checksum_mismatch:
          "Die Prüfsumme der LDT-Datei stimmt nicht — die Datei ist beschädigt oder unvollständig.",
        malformed_record:
          "Die LDT-Datei ist unvollständig oder nicht formatgerecht.",
        malformed_object:
          "Die LDT-Datei ist unvollständig oder nicht formatgerecht.",
        unsupported_ldt_version: "Diese LDT-Version wird nicht gelesen.",
        unsupported_record_type:
          "Die LDT-Datei enthält eine Satzart, die nicht gelesen wird (nur Laborbefunde).",
        unsupported_report_kind:
          "Die LDT-Datei enthält eine Satzart, die nicht gelesen wird (nur Laborbefunde).",
        unsupported_layout:
          "Der Tabellenkopf enthält nicht die erwarteten Spalten (Analyt, Wert, Abnahmedatum).",
        ambiguous_header: "Der Tabellenkopf nennt eine Spalte doppelt.",
        malformed_table:
          "Eine Zeile hat nicht so viele Felder wie der Tabellenkopf (häufig: Dezimalkomma in einer kommagetrennten Datei).",
        missing_field: "In einer Zeile fehlt Analyt, Wert oder Datum.",
        unsupported_date:
          "Ein Datum ist nicht eindeutig lesbar (erwartet: TT.MM.JJJJ oder JJJJ-MM-TT).",
        implausible_date: "Ein Datum liegt außerhalb der plausiblen Spanne.",
        unsupported_time: "Eine Uhrzeit ist nicht lesbar (erwartet: HH:MM).",
        empty_document: "Die Datei enthält keine Laborwerte.",
        too_many_values:
          "Die Datei enthält mehr Werte, als ein einzelner Befund hat.",
        document_unavailable:
          "Die gespeicherte Originaldatei ist nicht lesbar. Bitte erneut hochladen.",
      },
    },
    dataExport: {
      title: "Datenauskunft",
      noteBefore:
        "Eine Datei mit den zu dieser Person gespeicherten Daten, für eine Auskunft (Art. 15 DSGVO) oder eine Datenübertragung (Art. 20 DSGVO): Stammdaten, Einwilligungsvermerke, alle Werte, die in diese Akte eingelesenen Originaldateien und die freigegebenen Berichtsfassungen.",
      notIncluded: "Nicht enthalten",
      noteAfter:
        "sind unter anderem nicht freigegebene Berichtsfassungen, die Arbeitsdokumentation zur Interpretation, Prüfentscheidungen, das Audit-Protokoll, Angaben zum Personal und gespeicherte Dateien, die nie in diese Akte eingelesen wurden — die vollständige Liste steht in der Datei selbst. Ob diese Teile zu einer vollständigen Auskunft gehören, ist rechtlich noch zu klären.",
      create: "Datenauskunft erstellen",
      done: "Datei erstellt und heruntergeladen.",
      none: "Für diese Akte wurde noch keine Datenauskunft erstellt.",
      history: "Bisher erstellt (aus dem Audit-Protokoll)",
      // German as it was: a count of one is not given a singular of its own here.
      values: { one: "{n} Werte", other: "{n} Werte" },
      files: { one: "{n} Originaldateien", other: "{n} Originaldateien" },
      filesChanged: " ({n} nicht mehr unverändert im Speicher)",
      filesNeverRead: " ({n} nie eingelesen, nicht enthalten)",
      versions: {
        one: "{n} Berichtsfassungen",
        other: "{n} Berichtsfassungen",
      },
      confirmTitle: "Datenauskunft erstellen?",
      confirmNote:
        "Die Datei enthält personenbezogene Gesundheitsdaten dieser Person und wird auf dieses Gerät heruntergeladen. Bewahren Sie sie geschützt auf und geben Sie sie nur an die betroffene Person weiter. Die Erstellung wird Ihnen zugeordnet und auditiert; in der Plattform wird keine Kopie der Datei gespeichert.",
      confirm: "Erstellen und herunterladen",
      creating: "Wird erstellt …",
      errors: {
        patient_erased:
          "Diese Akte wurde gelöscht; es gibt nichts zu exportieren.",
        export_too_large:
          "Die gespeicherten Originaldateien sind zu groß für eine einzelne Datei.",
        storage_unavailable:
          "Eine gespeicherte Originaldatei konnte gerade nicht gelesen werden. Es wurde keine Datei erstellt — bitte später erneut versuchen.",
        cross_origin: "Die Anfrage wurde abgelehnt. Bitte die Seite neu laden.",
        tooMany:
          "Zu viele Datenauskünfte in kurzer Zeit. Bitte später erneut versuchen.",
        failed:
          "Die Datenauskunft konnte nicht erstellt werden. Bitte erneut versuchen.",
      },
    },
  },
  reviewQueue: {
    title: "Review-Queue",
    lead: "Offene Prüfaufgaben aus dem Import — kein Wert wird ohne menschliche Entscheidung veröffentlicht. Angezeigt wird die Quellrepräsentation (Originalname, -wert, -einheit).",
    readOnly:
      " Die Entscheidung ist der klinischen Rolle vorbehalten (Nur-Lese-Ansicht).",
    empty: "Keine offenen Prüfaufgaben.",
    tableAria: "Offene Prüfaufgaben",
    columns: {
      patient: "Patientin/Patient",
      value: "Wert (Quelle)",
      reason: "Grund",
      observed: "Beobachtet",
      decision: "Entscheidung",
    },
    publish: "Veröffentlichen",
    reject: "Ablehnen",
    cancel: "Abbrechen",
    clinicalRoleRequired: "Klinische Rolle erforderlich",
    reference: {
      upper: "obere Grenze {high}",
      lower: "untere Grenze {low}",
      line: "Referenz der Quelle: {bounds}",
      lineConverted: "Referenz der Quelle (umgerechnet): {bounds}",
    },
    // Where a value the patient already holds stands.
    heldStatus: {
      published: "veröffentlicht",
      pending: "in Prüfung",
      rejected: "abgelehnt",
      superseded: "ersetzt",
    },
    replacesOnPublish: "Ersetzt bei Veröffentlichung: {held}",
    citedIn: {
      one: " — in {n} Bericht zitiert",
      other: " — in {n} Berichten zitiert",
    },
    alreadyHeld: "Bereits vorhanden: {held}",
    dialog: {
      publishTitle: "Wert veröffentlichen?",
      rejectTitle: "Wert ablehnen?",
      publishBody:
        "Der Wert wird veröffentlicht und erscheint in der klinischen Zeitleiste. Bleibt eine weitere offene Prüfaufgabe zu diesem Wert bestehen, bleibt er bis zu deren Entscheidung zurückgehalten.",
      rejectBody:
        "Der Wert wird abgelehnt und nie veröffentlicht. Die Entscheidung wird Ihnen zugeordnet und auditiert.",
      replacesPublish:
        "Mit der Veröffentlichung ersetzt dieser Wert den früheren Wert {held}. Der frühere Wert bleibt unverändert erhalten und wird als ersetzt gekennzeichnet.",
      replacesReject: "Der frühere Wert {held} bleibt bestehen.",
      citedInReports: {
        one: " Er ist in {n} Bericht zitiert: Dieser kann erst mit einem neuen Entwurf genehmigt oder freigegeben werden; ein bereits freigegebener Bericht bleibt für die Patientin sichtbar, bis auf der Berichtsseite ein neuer Entwurf erstellt wird.",
        other:
          " Er ist in {n} Berichten zitiert: Diese können erst mit einem neuen Entwurf genehmigt oder freigegeben werden; ein bereits freigegebener Bericht bleibt für die Patientin sichtbar, bis auf der Berichtsseite ein neuer Entwurf erstellt wird.",
      },
    },
    // What the decision's server action answers.
    errors: {
      invalidReference: "Ungültige Referenz.",
      invalidPath: "Ungültiger Pfad.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      supersessionConflict:
        "Der Wert, den diese Korrektur ersetzen soll, wurde bereits durch eine andere Korrektur ersetzt. Dieser Wert kann nur abgelehnt werden.",
      conflict:
        "Bereits entschieden oder nicht mehr offen — Ansicht wird aktualisiert.",
      failed: "Aktion fehlgeschlagen. Bitte erneut versuchen.",
    },
  },
  interpretation: {
    crumb: "Interpretation erfassen · {patient}",
    titleNew: "Interpretation erfassen",
    titleCorrection: "Interpretation erfassen · Korrektur nach Lauf {run}",
    lead: "Sechs Domänen-Achsen · CIS und Actionability als zwei getrennte, geschlossene Angaben je Achse · drei bewertungsfreie Tri-State-Zellen als Belegkontext. Das System validiert und protokolliert Ihre Angaben; es leitet nichts ab. Eine Interpretation wird vollständig erfasst; eine Korrektur wird als neuer Lauf festgehalten, nichts wird überschrieben.",
    reason: "Grund (Pflicht)",
    reasonPlaceholderNew: "z. B. Baseline-Interpretation",
    reasonPlaceholderCorrection: "z. B. Korrektur nach neuen Laborwerten",
    // The names of the fields; what is chosen in them stays German (ADR-0007).
    cis: "CIS",
    actionability: "Actionability",
    followup: "Follow-up-Adäquanz",
    rationale: "Begründung (optional)",
    choose: "Bitte wählen",
    verdictFree: "(bewertungsfrei)",
    state: "Zustand",
    endpoint: "Endpunkt-Adäquanz",
    evidence: "Belege ({n} gewählt)",
    evidenceRequired: " — Pflicht",
    noEvidence: "Keine veröffentlichten Beobachtungen vorhanden.",
    cancel: "Abbrechen",
    submit: "Interpretation erfassen",
    submitting: "Wird erfasst …",
    invalid: {
      reason: "Bitte einen Grund angeben.",
      domain:
        "{axis}: CIS, Actionability und Follow-up-Adäquanz sind Pflichtangaben.",
      cell: "{axis} / {cell}: Zustand und Endpunkt-Adäquanz sind Pflichtangaben.",
      evidence:
        "{axis} / {cell}: eine bestimmte Zelle braucht mindestens einen Beleg.",
    },
    // What the server action answers.
    errors: {
      invalidPatient: "Ungültige Patientenreferenz.",
      invalidPath: "Ungültiger Pfad.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      vocabulary:
        "Eingaben unvollständig oder außerhalb der geschlossenen Vokabulare.",
      evidenceReplaced:
        "Ein gewählter Beleg wurde inzwischen vom Labor korrigiert. Bitte die Seite neu laden und die Belege erneut wählen.",
      evidenceUnresolved:
        "Belege nicht auflösbar: jeder Beleg muss eine veröffentlichte Beobachtung dieser Patientin sein.",
      shape: "Run-Struktur unvollständig (6 Domänen × 3 Zellen).",
      failed: "Erfassen fehlgeschlagen. Bitte erneut versuchen.",
    },
  },
  // One version of a report: its statements, their evidence, and the steps of its release.
  // What the page shares with the patient page (the report status, the age, the steps, how a
  // value relates to the source) is worded there, in patientPage.
  reportPage: {
    crumb: "Bericht",
    lead: "Jede Aussage bleibt auf die zugrunde liegenden Beobachtungen zurückführbar.",
    // Where this version stands, said above its text. Only a version that still awaits a
    // decision is called a draft.
    stage: {
      title: {
        report: "Quellengebundener Bericht",
        draft: "Quellengebundener Entwurf",
        rejected: "Zurückgewiesene Fassung",
      },
      badge: {
        draft: "Nicht freigegeben",
        approved: "Genehmigt",
        released: "Freigegeben",
        rejected: "Zurückgewiesen",
      },
      headline: {
        draftSystem: "Systementwurf – nicht freigegeben.",
        draftEdited: "Überarbeiteter Entwurf – nicht freigegeben.",
        approved: "Klinisch genehmigt – noch nicht freigegeben.",
        released: "Ärztlich freigegeben.",
        rejected: "Zurückgewiesen – nicht freigegeben.",
      },
      detail: {
        draft:
          "Aussagen müssen anhand der Quellen geprüft und vom klinischen Team signiert werden.",
        approved:
          "Die Freigabe an die Patientin ist der ärztlichen Leitung vorbehalten.",
        // What a released status proves — and no more: whether the patient can open the
        // report also depends on a valid link and standing consent.
        released:
          "Für die Patientin ist nur diese Version einsehbar – solange ihr Zugriffslink gültig ist und die Einwilligung besteht.",
        rejected:
          "Eine Überarbeitung erstellt eine neue Version; diese Fassung bleibt erhalten.",
        citesReplaced:
          "Ein zitierter Wert wurde vom Labor korrigiert – siehe Hinweis unten.",
      },
    },
    kicker: {
      edited: "Klinisch überarbeitete Fassung",
      deterministic: "Deterministische Zusammenfassung",
    },
    noStatements: "Für diesen Bericht liegen keine Aussagen vor.",
    // The reason itself is a closed vocabulary and stays German (ADR-0007).
    rejected: {
      title: "Zurückgewiesen.",
      reason: "Grund:",
      noReason: "Für diese Zurückweisung wurde kein Grund erfasst.",
      reworked: "Überarbeitung nach einer Zurückweisung. Damaliger Grund:",
    },
    citesReplaced: {
      note: "Ein zitierter Wert wurde vom Labor korrigiert. Diese Fassung kann nicht genehmigt oder freigegeben werden.",
      released:
        " Der Zugriff der Patientin auf diese Fassung wird erst mit einem neuen Entwurf zurückgezogen.",
      clinician: " Erstellen Sie einen neuen Entwurf aus den aktuellen Werten.",
      otherRole: " Ein neuer Entwurf ist der klinischen Rolle vorbehalten.",
    },
    statement: {
      label: "Aussage {n}",
      removing: " · wird entfernt",
      remove: "Aussage entfernen",
      restore: "Aussage wiederherstellen",
    },
    // A cited observation, as the source wrote it.
    chip: {
      unresolved: "Beleg nicht auflösbar",
      observation: "Beobachtung",
      corrected: " · vom Labor korrigiert",
    },
    rework: {
      note: "Die Belege bleiben an die jeweilige Aussage gebunden. Beim Speichern entsteht Version v{next} als Entwurf; die zurückgewiesene Version v{version} bleibt erhalten. Die neue Version muss erneut genehmigt und freigegeben werden.",
      save: "Als neue Version speichern",
    },
    domains: {
      title: "Domänen-Interpretation",
      note: "Sechs Domänen-Achsen · Actionability-Verdict je Achse. Kein Score.",
      run: "Lauf {n}",
      noRun: "Für diese Patientin liegt noch keine Interpretation vor.",
      reviewed: "✓ reviewt",
      draft: "Entwurf",
      // The name of the fact; its value is a closed vocabulary and stays German.
      adequacy: "Follow-up-Adäquanz:",
      citesReplaced:
        "Stützt sich auf einen vom Labor korrigierten Wert — Interpretation prüfen.",
      shown: "✓ Biomarker im Beobachtungsnachweis",
      show: "Biomarker ansehen ({n})",
    },
    evidence: {
      title: "Beobachtungsnachweis",
      noteAll:
        "Gemessene Werte, Einheiten, Referenzintervalle und Provenienz — mit Lage zum Referenzintervall.",
      // Followed by the name of the domain, which stays German.
      noteDomain: "Eigene Beobachtungen der Domäne:",
      showAll: "Alle anzeigen",
      filtersAria: "Nach Lage zum Referenzintervall filtern",
      filters: {
        all: "Alle",
        outside: "Außerhalb Referenz",
        no_ref: "Ohne Referenz",
      },
      caption: "Gemessene Beobachtungen dieses Assessments",
      columns: {
        marker: "Marker",
        primaryDomain: "Primärdomäne",
        current: "Aktuell",
        position: "Lage zum Referenzintervall",
        change: "Veränderung",
        reference: "Referenz",
        codeStatus: "Code / Status",
      },
      empty: {
        outside: "Keine Marker außerhalb des Referenzintervalls.",
        no_ref: "Keine Marker ohne hinterlegte Referenz.",
        domain: "Keine Beobachtungen für diese Domäne.",
        all: "Keine Beobachtungen vorhanden.",
      },
      notPublished: "keine Lage: Der Wert ist nicht veröffentlicht",
      referenceInterval: "Referenzintervall",
      noInterval: "kein Referenzintervall hinterlegt",
      reference: "Referenz {range}",
      noScale: "keine Skala",
    },
    // Around the name of the domain, which stays German.
    secondary: {
      title: "Sekundär relevant",
      noteBefore: "Auch für",
      noteAfter:
        " relevant. Zur Übersicht angezeigt – geführt und bewertet wird jeder Wert in seiner Primärdomäne; hieraus wird keine Domänen-Bewertung abgeleitet.",
      label: "Sekundär relevante Beobachtungen für",
    },
    audit: {
      title: "Audit-Status",
      note: "Fortschritt von Datenerfassung bis Patientenfreigabe (Live-Status).",
    },
    bar: {
      status: "Bericht v{version} · Status: {status}",
      // What this role can do here, and why not — the server enforces it; this explains it.
      hint: {
        releasedReplaced:
          "Freigegeben — ein zitierter Wert wurde vom Labor korrigiert; der Zugriff der Patientin wird erst mit einem neuen Entwurf zurückgezogen.",
        replaced:
          "Ein zitierter Wert wurde vom Labor korrigiert — diese Fassung kann nicht genehmigt oder freigegeben werden.",
        released:
          "Freigegeben — Für die Patientin ist nur diese Version einsehbar – solange ihr Zugriffslink gültig ist und die Einwilligung besteht.",
        rejectedClinician:
          "Zurückgewiesen — „Überarbeiten“ erstellt eine neue Version; die zurückgewiesene bleibt erhalten.",
        rejected:
          "Zurückgewiesen — eine Überarbeitung erstellt eine neue Version.",
        approvedDirector:
          "Bereit zur Freigabe an die Patientin — einwilligungsgebunden, zugeordnet und auditiert.",
        approved: "Genehmigt — wartet auf die ärztliche Freigabe.",
        draftClinician:
          "Genehmigung wird serverseitig geschrieben, ist Ihnen zugeordnet und wird auditiert.",
        draftDirector: "Wartet auf die klinische Genehmigung.",
        readOnly: "Nur-Lese-Ansicht für Ihre Rolle.",
      },
      rework: "Überarbeiten",
      redraft: "Neuen Entwurf erstellen",
      reject: "Zurückweisen",
      approve: "Bericht genehmigen",
      release: "An Patientin freigeben",
    },
    dialog: {
      close: "Dialog schließen",
      title: {
        approve: "Bericht genehmigen?",
        reject: "Bericht zurückweisen?",
        redraft: "Neuen Entwurf erstellen?",
        release: "An Patientin freigeben?",
        released: "Freigegeben — Zugriffslink",
      },
      body: {
        approve:
          "Sie bestätigen, dass Sie die sichtbaren Beobachtungen, Referenzintervalle und Quellen geprüft haben. Die Genehmigung wird serverseitig geschrieben, ist Ihnen zugeordnet und wird auditiert.",
        reject:
          "Die aktuelle Version wird als zurückgewiesen festgehalten (zugeordnet und auditiert), zusammen mit dem gewählten Grund. Wer den Bericht überarbeitet, sieht diesen Grund; eine Überarbeitung erstellt eine neue Version.",
        redraft:
          "Aus den aktuell gültigen Werten wird eine neue Entwurfsversion erstellt. Die bisherige Version bleibt gespeichert, wird hier aber nicht mehr angezeigt; manuell überarbeitete Formulierungen werden nicht übernommen.",
        redraftReleased:
          "Der Zugriff der Patientin auf den freigegebenen Bericht wird damit zurückgezogen, bis die neue Version genehmigt und erneut freigegeben ist.",
        redraftOther: "Die neue Version muss genehmigt und freigegeben werden.",
        release:
          "Die Freigabe ist einwilligungsgebunden (report_release), wird Ihnen zugeordnet und auditiert. Die Patientin sieht ausschließlich die freigegebene Version.",
        released:
          "Der Bericht ist freigegeben. Synthetische Demo: Den Link manuell und sicher übermitteln — kein automatischer Versand.",
      },
      reason: "Grund der Zurückweisung",
      confirm:
        "Ich habe die offenen Hinweise geprüft und bestätige die klinische Dokumentation.",
      link: "Zugriffslink (einmalig angezeigt)",
      copyLink: "Link kopieren",
      done: "Schließen",
      cancel: "Abbrechen",
      submit: {
        approve: "Genehmigen",
        reject: "Zurückweisen",
        redraft: "Neuen Entwurf erstellen",
        release: "Freigeben",
      },
    },
    toast: {
      saved: "Überarbeitung als neue Version gespeichert.",
      approved: "Bericht genehmigt.",
      redrafted: "Neuer Entwurf aus den aktuellen Werten erstellt.",
      rejected: "Bericht zurückgewiesen.",
      copied: "Link kopiert.",
    },
    // What the report actions answer — the draft action on the patient page among them.
    errors: {
      invalidReport: "Ungültige Berichtsreferenz.",
      invalidPatient: "Ungültige Patientenreferenz.",
      invalidPath: "Ungültiger Pfad.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      tooMany:
        "Zu viele Anfragen in kurzer Zeit. Bitte kurz warten und erneut versuchen.",
      noConsent:
        "Keine aktive Einwilligung (report_release) für diese Patientin hinterlegt.",
      notApproved: "Der Bericht ist noch nicht genehmigt.",
      alreadyRejected: "Der Bericht wurde bereits zurückgewiesen.",
      citesReplaced:
        "Nicht möglich: Ein zitierter Wert wurde vom Labor korrigiert. Bitte einen neuen Entwurf aus den aktuellen Werten erstellen.",
      evidenceHidden:
        "Genehmigung nicht möglich: nicht jeder Beleg ist einsehbar.",
      wrongStatus: "Aktion im aktuellen Berichtsstatus nicht möglich.",
      failed: "Aktion fehlgeschlagen. Bitte erneut versuchen.",
      noPublished:
        "Kein Entwurf möglich: Es liegen keine veröffentlichten Beobachtungen vor.",
      unsupported:
        "Kein Entwurf möglich: Nicht jede Aussage ließ sich mit einer Quelle belegen.",
      statementShape:
        "Jede Aussage braucht einen Text und mindestens einen Beleg.",
      // {terms}: the words the API refused, as it names them.
      restricted:
        "Nicht gespeichert: Der Text enthält für Berichte nicht zulässige Begriffe ({terms}).",
      editReplaced:
        "Nicht gespeichert: Ein zitierter Wert wurde vom Labor korrigiert. Bitte die betroffene Aussage entfernen oder einen neuen Entwurf erstellen.",
      editEvidence:
        "Nicht gespeichert: Nicht jeder Beleg ist einsehbar. Bitte die betroffene Aussage entfernen.",
      chooseReason: "Bitte einen Grund wählen.",
    },
  },
  // Settings → members (owners only). The names of the roles are `roles` above.
  membersPage: {
    ownersOnly: "Die Mitgliederverwaltung ist nur für Inhaber verfügbar.",
    eyebrow: "Einstellungen · Praxis",
    lead: "Wer in dieser Praxis arbeitet und was die Rolle erlaubt. Eingeladene richten ihren Zugang selbst über einen einmaligen Link ein; die Rolle legen Sie fest.",
    team: "Mitglieder",
    you: " · Sie",
    roleOf: "Rolle von {name}",
    roleCount: "{role} {n}",
    columns: {
      person: "Person",
      role: "Rolle",
      lastActive: "Zuletzt aktiv",
      actions: "Aktionen",
    },
    never: "noch nie",
    more: "Weitere Aktionen für {name}",
    showInTrail: "Im Protokoll anzeigen",
    remove: "Aus dem Team entfernen …",
    removeConfirm:
      "{name} aus dem Team entfernen? Die Person verliert sofort den Zugang zu dieser Praxis. Der Vorgang wird protokolliert.",
    roleConfirm:
      "Rolle von {name} von {from} zu {to} ändern? Der Vorgang wird protokolliert.",
    note: "Eine Rolle ändern oder ein Mitglied entfernen wird protokolliert und fragt vorher nach. Inhaber und Ärztliche Leitung sind getrennte Rollen: Wer freigibt, verwaltet nicht, und umgekehrt.",
    invite: {
      open: "Kolleg:in einladen",
      title: "Kolleg:in einladen",
      note: "Der Link wird genau einmal angezeigt und läuft nach 7 Tagen ab. Die Rolle legen Sie hier fest; die eingeladene Person kann sie nicht ändern.",
      label: "Für wen (optional)",
      labelHelp:
        "Zum Beispiel die E-Mail-Adresse. Nur zur Beschriftung in Ihrer Liste; der Link wird nicht versendet.",
      role: "Rolle",
      cancel: "Abbrechen",
      create: "Einladungslink erstellen",
      // Around the name of the role, then around "shown only once" (both bold).
      createdBefore: "Einladung für",
      createdAfter:
        "erstellt. Geben Sie diesen Link an die eingeladene Person weiter — er wird",
      once: "nur einmal angezeigt",
      link: "Einmaliger Einladungslink",
      done: "Fertig",
    },
    pending: {
      title: "Offene Einladungen",
      none: "Keine offenen Einladungen.",
      created: "Link erstellt am {day} von {name}",
      createdNoName: "Link erstellt am {day}",
      expires: "Läuft ab am {day} · noch nicht eingelöst",
      revoke: "Widerrufen",
      revokeOf: "Einladung {what} widerrufen",
      revokeConfirm:
        "Einladung widerrufen? Der Link funktioniert danach nicht mehr.",
    },
    matrix: {
      title: "Was eine Rolle darf",
      note: "Aus der Rechtematrix der Plattform; jede Aktion wird zusätzlich auf dem Server geprüft.",
      caption: "Was jede Rolle darf",
      capability: "Darf",
      yes: "ja",
      no: "nein",
      unavailable: "Die Rechtematrix ist derzeit nicht abrufbar.",
      capabilities: {
        readRecords: "Akten, Werte, eigene Vorgänge und das Praxisprofil lesen",
        createRecords:
          "Akten anlegen, Einwilligungen dokumentieren, Patientinnen und Patienten einladen",
        importValues: "Laborwerte hochladen und einlesen",
        draftReports: "Berichte entwerfen und überarbeiten",
        decideValues: "Werte der Review-Queue entscheiden",
        interpret: "Interpretation erfassen",
        approve: "Berichte genehmigen",
        redraft: "Neuen Entwurf nach einer Laborkorrektur öffnen",
        reject: "Berichte zurückweisen",
        release: "Berichte freigeben",
        team: "Team verwalten und Kolleg:innen einladen",
        clinicProfile: "Praxisprofil ändern",
        auditTrail: "Audit-Protokoll der Praxis lesen",
        metric: "Vorbereitungszeit erfassen und einsehen",
        export: "Datenauskunft erstellen",
        requestDeletion: "Löschung einer Akte beantragen",
        listDeletion: "Löschanträge einsehen",
        decideDeletion: "Löschanträge entscheiden",
        executeDeletion: "Genehmigte Löschungen ausführen",
      },
    },
    // What the server actions answer.
    errors: {
      invalidRole: "Ungültige Rolle.",
      invalidInvitation: "Ungültige Einladung.",
      invalidInput: "Ungültige Eingabe.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      ownMembership: "Die eigene Mitgliedschaft kann nicht geändert werden.",
      lastOwner: "Die Klinik benötigt mindestens einen Inhaber.",
      notPending: "Diese Einladung ist nicht mehr ausstehend.",
      tooMany: "Zu viele Anfragen. Bitte später erneut versuchen.",
      failed:
        "Die Aktion konnte nicht ausgeführt werden. Bitte erneut versuchen.",
    },
  },
  // Settings → deletion requests (owners and the medical director). The reasons of a request
  // are worded on the patient page (patientPage.deletion.reasons).
  deletionRequestsPage: {
    reserved:
      "Die Verwaltung von Löschanträgen ist Inhabern und der Ärztlichen Leitung vorbehalten.",
    lead: "Anträge auf Löschung von Patientendaten. Ein Antrag wird von der Inhaberin oder dem Inhaber gestellt und von der Ärztlichen Leitung geprüft (Vier-Augen-Prinzip). Die eigentliche, unwiderrufliche Löschung anonymisiert den Datensatz und wird gesondert ausgeführt.",
    none: "Keine Löschanträge vorhanden.",
    erased: "Gelöschter Datensatz",
    requested: "beantragt {day}",
    // Where a request stands — a workflow state.
    status: {
      pending: "Offen",
      approved: "Freigegeben",
      rejected: "Abgelehnt",
      cancelled: "Zurückgezogen",
      executed: "Ausgeführt",
    },
    execute: "Endgültig löschen",
    executeConfirm:
      'Daten von „{name}" jetzt endgültig und unwiderruflich löschen? Der Datensatz wird anonymisiert; abgeleitete Daten, Dokumente und Berichte werden gelöscht. Dies kann nicht rückgängig gemacht werden.',
    executionPending: "Ausführung ausstehend",
    approve: "Freigeben",
    approveConfirm:
      'Löschung für „{name}" freigeben? Die Ausführung erfolgt gesondert und ist unwiderruflich.',
    reject: "Ablehnen",
    cancel: "Zurückziehen",
    // What the server actions answer.
    errors: {
      failedShort: "Aktion fehlgeschlagen.",
      invalid: "Ungültige Anfrage.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      notFound: "Die Anfrage wurde nicht gefunden.",
      notOpen: "Die Anfrage ist nicht mehr offen.",
      requesterOnly: "Nur die anfragende Person kann zurückziehen.",
      wrongStatus: "Die Anfrage kann in diesem Status nicht bearbeitet werden.",
      failed:
        "Die Aktion konnte nicht ausgeführt werden. Bitte erneut versuchen.",
    },
  },
  // Settings → audit trail (owners only). The labels of the events, their families and the
  // kinds of record are in lib/auditCopy.ts, in both languages.
  auditPage: {
    ownersOnly: "Das Audit-Protokoll ist nur für Inhaber verfügbar.",
    tooMany:
      "Das Protokoll wurde in kurzer Zeit sehr oft abgerufen. Bitte versuchen Sie es in einer Minute erneut.",
    unavailable:
      "Das Protokoll ist vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut.",
    lead: "Die protokollierten Vorgänge dieser Praxis: wer, wann, welcher Vorgang, an welchem Datensatz. Ein Eintrag enthält Kennungen, Codes, Zähler und Zeitpunkte – keine Messwerte und keine Namen von Patientinnen und Patienten. Wer gehandelt hat, ist mit dem Namen und der E-Mail-Adresse des Kontos angegeben. Die Anwendung fügt Einträge nur an; sie ändert und löscht keine. Zeiten in der Zeitzone {zone}.",
    // What the trail does not show. `notRecorded` is held against the API's reads that write
    // no event (apps/api/tests/test_audit_read.py).
    notShown: {
      title: "Was dieses Protokoll nicht zeigt",
      tenantless:
        "Vorgänge, die ohne Praxis protokolliert werden: Anmeldung und Abmeldung, fehlgeschlagene Anmeldungen, gedrosselte und aus Sicherheitsgründen abgewiesene Anfragen sowie Zugriffsversuche ohne ausgewählte Praxis oder nach dem Ende einer Mitgliedschaft. Der Eintritt in die Praxis ist protokolliert.",
      notRecorded:
        "Derzeit nicht protokolliert: das Lesen eines Berichts durch Mitarbeitende und das Lesen der Verwaltungslisten (Mitglieder, Teameinladungen, Löschanträge, Verlauf der Datenauskünfte).",
      refusals:
        "Abgewiesene Vorgänge sind nur zum Teil protokolliert: Rollenverweigerungen, abgelehnte Einlesevorgänge und Datenauskünfte, abgewiesene Einladungs- und Zugriffslinks. Andere Ablehnungen – etwa eine Freigabe ohne Einwilligung oder der Aufruf einer unbekannten Kennung – hinterlassen keinen Eintrag.",
      linkRefusals:
        "Abgewiesene Einladungs- und Zugriffslinks stehen einzeln im Protokoll, bis je Vorgangsart 30 in einer Minute erreicht sind. Ein Eintrag hält dann fest, dass weitere Abweisungen bis zum Ablauf dieser Minute nicht mehr einzeln protokolliert werden – wie viele es waren, steht nicht im Protokoll.",
      byRecord:
        "Ein Eintrag steht unter dem Datensatz, an dem er protokolliert ist. Unter einer Akte stehen das Anlegen und Öffnen der Akte, das Lesen von Werten, Interpretation, Einwilligungen und Dateiliste, die in der Praxis dokumentierten Einwilligungen und Widerrufe und die Datenauskunft. Berichte, Dateien, Einlesevorgänge, erfasste Interpretationen, Review-Einträge, Einladungen und Löschanträge stehen unter ihrer eigenen Kennung und erscheinen bei der Auswahl einer Akte nicht; eine über eine Einladung erteilte Einwilligung steht unter der Einladung.",
      lists:
        "Listenansichten (Aktenliste, Übersicht, Review-Queue) sind als Lesezugriff protokolliert, ohne die einzelnen Akten zu nennen. Das Öffnen einer Akte lädt auch die Übersicht und hinterlässt dafür einen eigenen Eintrag.",
      erased:
        "Einträge zu einer gelöschten Akte bleiben mit der Kennung der Akte erhalten.",
      sameTime:
        "Einträge, die in derselben Anfrage entstehen, tragen denselben Zeitpunkt; ihre Reihenfolge untereinander ist nicht festgelegt.",
      paging:
        "Beim Blättern zu älteren Einträgen kann ein Eintrag fehlen, der erst während des Lesens gespeichert wurde. Ein erneutes Lesen von der ersten Seite an zeigt ihn.",
    },
    filter: {
      category: "Bereich",
      allCategories: "Alle Bereiche",
      from: "Von",
      to: "Bis einschließlich",
      hideReads: "Lesezugriffe ausblenden",
      apply: "Anwenden",
      reset: "Filter zurücksetzen",
    },
    // Around the record's identifier (shown as it is).
    targetBefore: "Nur Einträge, die unter dem Datensatz",
    targetAfter: " protokolliert sind.",
    allTargets: "Alle Datensätze anzeigen",
    actorOnly: "Nur Einträge von {name}.",
    allActors: "Alle Personen anzeigen",
    readsHidden: "Lesezugriffe sind ausgeblendet.",
    showReads: "Lesezugriffe einblenden",
    stalePosition:
      "Die aufgerufene Position ist nicht gültig. Angezeigt werden die neuesten Einträge.",
    entries: "Einträge",
    emptyFiltered: "Zu dieser Auswahl gibt es keine Einträge.",
    empty: "Noch keine Einträge.",
    tableAria: "Audit-Protokoll, neueste Einträge zuerst",
    columns: {
      time: "Zeit",
      who: "Wer",
      action: "Vorgang",
      target: "Datensatz",
      details: "Details",
    },
    noActor: "ohne angemeldete Person",
    onlyThisTarget: "Nur Einträge zu diesem Datensatz anzeigen",
    openRecord: "Akte öffnen",
    yes: "ja",
    no: "nein",
    older: "Ältere Einträge",
    newest: "Zu den neuesten Einträgen",
  },
  // Settings → preparation time (owners only): what the clinic states, and what the platform
  // measures — two quantities the page never sets against each other.
  preparationPage: {
    ownersOnly: "Die Vorbereitungszeit ist nur für Inhaber verfügbar.",
    tooMany:
      "Die Seite wurde in kurzer Zeit sehr oft abgerufen. Bitte versuchen Sie es in einer Minute erneut.",
    unavailable:
      "Die Kennzahl ist vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut.",
    lead: "Wie lange die Vorbereitung eines Termins dauert. Diese Seite hält zwei Dinge auseinander: was die Praxis selbst angibt, und was die Plattform aus dem Ablauf der Berichte misst. Sie enthält keine Daten von Patientinnen und Patienten. Zeiten in der Zeitzone {zone}.",
    saved: "Die Angabe wurde gespeichert.",
    // Keyed by the outcome code the form's action puts in the URL.
    failures: {
      eingabe:
        "Die Angabe wurde nicht gespeichert: Die Eingabe war unvollständig.",
      minuten:
        "Die Angabe wurde nicht gespeichert: Der Median ist eine ganze Zahl von 1 bis 600 Minuten.",
      stichprobe:
        "Die Angabe wurde nicht gespeichert: Zu einer Zeitmessung gehört die Anzahl der gemessenen Termine (1 bis 100000).",
      schaetzung:
        "Die Angabe wurde nicht gespeichert: Eine Schätzung hat keine Anzahl gemessener Termine. Bitte das Feld leer lassen oder „Zeitmessung“ wählen.",
      rolle:
        "Die Angabe wurde nicht gespeichert: Das ist nur Inhabern erlaubt.",
      zuviele:
        "Die Angabe wurde nicht gespeichert: zu viele Angaben in kurzer Zeit. Bitte warten Sie eine Minute.",
      // The API may have recorded it although its answer did not arrive: say what is known.
      allgemein:
        "Ob die Angabe gespeichert wurde, konnte nicht bestätigt werden. Bitte prüfen Sie den Verlauf, bevor Sie sie erneut eingeben.",
    },
    kind: { baseline: "Ausgangswert", follow_up: "Folgeangabe" },
    basis: { estimate: "Schätzung", timed_sample: "Zeitmessung" },
    timedOver: {
      one: "Zeitmessung über {n} Termin",
      other: "Zeitmessung über {n} Termine",
    },
    minutes: "{n} Min.",
    // An elapsed time in the two largest units that say something; nothing finer than a minute.
    elapsed: {
      underOne: "unter 1 Min.",
      minutes: "{m} Min.",
      hours: "{h} Std.",
      hoursMinutes: "{h} Std. {m} Min.",
      days: { one: "{n} Tag", other: "{n} Tage" },
      daysHours: { one: "{n} Tag {h} Std.", other: "{n} Tage {h} Std." },
    },
    stated: {
      title: "Angaben der Praxis",
      note: "Der Median der Vorbereitungszeit je Termin, in Minuten, wie die Praxis ihn angibt: der Ausgangswert vor dem Einsatz der Plattform und spätere Folgeangaben. Die Plattform übernimmt diese Zahlen und prüft sie nicht.",
      latestFollowUp: "Letzte Folgeangabe",
      noBaseline: "Noch kein Ausgangswert erfasst.",
      noFollowUp: "Noch keine Folgeangabe erfasst.",
      perAppointment: "Median je Termin · {basis}",
      // Before the time it was recorded, then who recorded it.
      recordedAt: "erfasst am",
      recordedBy: " von {name}",
      same: "Die letzte Folgeangabe entspricht dem Ausgangswert.",
      below: "Die letzte Folgeangabe liegt {n} Min. unter dem Ausgangswert.",
      above: "Die letzte Folgeangabe liegt {n} Min. über dem Ausgangswert.",
      bothStated: "Beide Zahlen sind Angaben der Praxis",
      // The pilot's figure (docs/notes/0025): the two statements set against each other.
      change: {
        title: "Veränderung gegenüber dem Ausgangswert",
        note: "{from} → {to} Minuten je Termin, beide Angaben der Praxis. Die Plattform rechnet nur die Differenz.",
        targetMet:
          "Das Pilotkriterium von mindestens −{target} % ist nach diesen Angaben erreicht.",
        targetOpen:
          "Pilotkriterium: mindestens −{target} % gegenüber dem Ausgangswert.",
      },
      differentBasis:
        " – auf unterschiedlicher Grundlage ({first} und {second}).",
    },
    form: {
      kind: "Art der Angabe",
      median: "Median je Termin (Minuten)",
      basis: "Grundlage",
      sample: "Anzahl gemessener Termine (nur bei Zeitmessung)",
      save: "Angabe speichern",
      note: "Eine gespeicherte Angabe wird nicht geändert oder gelöscht. Eine Korrektur ist eine neue Angabe; die frühere bleibt im Verlauf stehen.",
    },
    history: {
      shown: "Der Verlauf zeigt die neuesten {shown} von {total} Angaben.",
      caption: "Verlauf der Angaben der Praxis, neueste zuerst",
      columns: {
        recordedAt: "Erfasst am",
        kind: "Art",
        median: "Median je Termin",
        basis: "Grundlage",
        recordedBy: "Erfasst von",
      },
    },
    measured: {
      title: "Gemessen aus dem Ablauf der Berichte",
      note: "Die Zeit vom ersten Entwurf eines Berichts bis zu seiner ersten klinischen Genehmigung, die Bestand hatte – aus den Zeitpunkten, die die Plattform dabei ohnehin festhält. Das ist Durchlaufzeit, keine Arbeitszeit, und noch nicht die Vorbereitungszeit selbst.",
      last30: "Letzte 30 Tage",
      allTime: "Alle genehmigten Berichte der Praxis",
      median:
        "Median vom ersten Entwurf bis zur ersten Genehmigung, die Bestand hatte · {n} Berichte",
      middleHalf: "Mittlere Hälfte der Berichte: {q1} bis {q3}",
      none: "Noch kein genehmigter Bericht in diesem Zeitraum.",
      tooFew:
        "Genehmigte Berichte in diesem Zeitraum: {n}. Ein Median wird ab {minimum} Berichten angegeben.",
    },
    limits: {
      title: "Was diese Zahlen sind – und was nicht",
      waiting:
        "Die gemessene Zeit enthält jede Wartezeit zwischen Entwurf und Genehmigung – auch Nächte und Wochenenden. Was vor dem Entwurf geschieht (Werte sichten, Review-Einträge entscheiden, Interpretation erfassen), ist nicht enthalten.",
      notOffset:
        "Sie wird deshalb nicht mit den Minuten-Angaben der Praxis verrechnet: Es sind zwei verschiedene Größen. Eine Messung, die sich mit dem Ausgangswert vergleichen lässt, gibt es noch nicht – die Plattform hält bisher keinen Beginn der Vorbereitung fest.",
      countsOnce:
        "Ein Bericht zählt einmal: mit seiner ersten Genehmigung, die nicht wieder zurückgewiesen wurde. Eine Genehmigung, die bei der ärztlichen Freigabe abgelehnt oder zurückgezogen wurde, beendet die Messung nicht. Berichte ohne Genehmigung zählen nicht.",
      minimum:
        "Unter {minimum} Berichten wird kein Median angegeben: Bei so wenigen Berichten entspricht jede Zahl nahezu der Zeit eines einzelnen Berichts. Das ist eine Vorsicht bei kleinen Zahlen, kein Schutz einzelner Personen: Genehmigen in der Praxis nur wenige, so beschreibt die Zahl auch bei vielen Berichten deren Arbeit.",
      computed:
        "Die Kennzahl wird bei jedem Aufruf aus den vorhandenen Berichten gebildet. Wird eine Akte gelöscht, entfallen ihre Berichte auch hier – eine früher abgelesene Zahl lässt sich dann nicht mehr nachrechnen.",
      audited:
        "Das Lesen dieser Seite und jede erfasste Angabe stehen im Audit-Protokoll. Stand der Messvorschrift: {definition}.",
    },
  },
  notFound: {
    title: "Seite nicht gefunden",
    note: "Die angeforderte Seite existiert nicht oder ist nicht verfügbar.",
    back: "Zur Übersicht",
  },
  settings: {
    title: "Einstellungen",
    eyebrow: "Verwaltung",
    intro:
      "Persönliches, die Praxis und die Governance, getrennt. Was Ihre Rolle nicht öffnen darf, ist gesperrt, nicht versteckt.",
    nav: {
      label: "Bereiche der Einstellungen",
      groups: {
        personal: "Persönlich",
        clinic: "Praxis",
        governance: "Governance",
      },
      locked: "Nur für {roles}",
      and: " und ",
    },
    all: {
      title: "Alle Bereiche",
      note: "Jede Karte sagt, was darin gerade steht.",
    },
    appearance: {
      title: "Sprache & Darstellung",
      desc: "Die Sprache der Oberfläche und das Erscheinungsbild auf diesem Gerät.",
    },
    profile: {
      title: "Profil",
      desc: "Name und E-Mail-Adresse, wie Kolleginnen und Kollegen sie im Protokoll sehen, und Ihre Praxen.",
    },
    security: {
      title: "Sicherheit & Sitzungen",
      desc: "Wie Sie sich anmelden, Ihre Sitzungen, und alle anderen beenden.",
    },
    clinicProfile: {
      title: "Praxisprofil",
      desc: "Name und Anschrift der Praxis, wie Team und Patientinnen sie sehen, und die Zeitzone des Labors.",
    },
    dataSources: {
      title: "Datenquellen & Import",
      desc: "Welche Leser Labordateien lesen, wann zuletzt, und was nach dem Einlesen mit einem Wert geschieht.",
    },
    consentTexts: {
      title: "Einwilligungstexte",
      desc: "Die Fassungen, auf die sich jede Einwilligung bezieht. Eine neue Fassung ist eine neue Version, nie ein Überschreiben.",
    },
    retention: {
      title: "Aufbewahrung & Export",
      desc: "Aufbewahrungsfristen, Datenauskunft (Art. 15/20), Löschung und Wiederherstellung.",
    },
    members: {
      title: "Team & Rollen",
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
    // What each card says is in the section right now.
    state: {
      members: { one: "{n} Mitglied", other: "{n} Mitglieder" },
      invitations: {
        one: "{n} offene Einladung",
        other: "{n} offene Einladungen",
      },
      noInvitations: "keine offene Einladung",
      baselineSet: "Ausgangswert erfasst",
      baselineMissing: "Ausgangswert fehlt",
      median: "Median {value}",
      noMedian: "noch kein Median",
      deletions: { one: "{n} Antrag offen", other: "{n} Anträge offen" },
      noDeletions: "Kein Antrag offen",
      denials: {
        one: "{n} abgewiesener Zugriff in 7 Tagen",
        other: "{n} abgewiesene Zugriffe in 7 Tagen",
      },
      unavailable: "Stand derzeit nicht abrufbar",
      sessions: {
        one: "{n} aktive Sitzung",
        other: "{n} aktive Sitzungen",
      },
      signIn: {
        dev: "Entwicklungsanmeldung",
        oidc: "Anmeldestelle der Praxis",
      },
      clinicProfile: "{name} · {zone}",
      dataSources: "{readers} · Wearables nicht verbunden",
      consentTexts: "Fassung {version} · {n} Zwecke",
      retention: "Aufbewahrungsrichtlinie noch nicht hinterlegt",
    },
  },
  clinicPage: {
    lead: "Wie die Praxis heißt und wo sie ist – im Kopf jeder Seite und unter dem Bericht, den eine Patientin über ihren Zugriffslink liest.",
    profile: "Angaben",
    name: "Name der Praxis",
    address: "Anschrift",
    addressHelp:
      "Erscheint unter dem freigegebenen Bericht. Höchstens 300 Zeichen.",
    noAddress: "Keine Anschrift hinterlegt",
    zone: "Zeitzone des Labors",
    zoneHelp:
      "Laborzeiten ohne eigene Zeitzone werden in dieser Zone gelesen. Sie gilt für die ganze Pilotumgebung und wird nicht hier geändert.",
    logo: "Logo",
    logoNote: "Noch nicht möglich: Diese Pilotumgebung nimmt keine Bilder an.",
    save: "Speichern",
    saved: "Gespeichert.",
    ownerOnly: "Ändern kann der Inhaber der Praxis.",
    errors: {
      invalid:
        "Bitte einen Namen angeben; die Anschrift hat höchstens 300 Zeichen.",
      forbidden: "Diese Aktion ist Ihrer Rolle nicht erlaubt.",
      failed: "Nicht gespeichert. Bitte erneut versuchen.",
    },
    unavailable: "Das Praxisprofil ist derzeit nicht abrufbar.",
  },
  sourcesPage: {
    lead: "Wie Werte in die Akten kommen. Welche Quelle eine Praxis nutzt, ist eine Frage des Labors – eine strukturierte Datei ist einer PDF immer vorzuziehen.",
    readers: "Leser für Labordateien",
    readersNote:
      "Welche Art Datei es ist, entscheidet der Inhalt, nie der Dateiname.",
    what: {
      csv: "Tabelle im HADP-Layout: eine Zeile je Wert, mit Einheit und Referenzintervall des Labors.",
      ldt2: "Labordatenträger, Version 2 (Satzart 8201).",
      ldt3: "Labordatenträger, Version 3 (Satzart 8205), mit Prüfsumme.",
      other: "Von Hand eingetragen oder über die Schnittstelle gesendet.",
    },
    never: "Noch nichts eingelesen",
    last: "Zuletzt {when}",
    jobs: { one: "{n} Vorgang", other: "{n} Vorgänge" },
    rows: { one: "{n} Zeile", other: "{n} Zeilen" },
    after: "Was nach dem Einlesen geschieht",
    steps: {
      stored: "Die Datei wird unverändert gespeichert, bevor sie gelesen wird.",
      published:
        "Ein Wert, dessen Kennzahl, Einheit und Zahl eindeutig sind, wird veröffentlicht.",
      review:
        "Jeder andere Wert wartet in der Review-Queue, bis eine Ärztin oder ein Arzt entscheidet – unbekannte Einheit, unklare Kennzahl, unmögliche Zahl, mögliche Doppelung oder Korrektur.",
      original:
        "Originalwert, Einheit und Referenzintervall des Labors bleiben unverändert erhalten.",
    },
    pdf: "PDF-Befunde werden noch nicht gelesen.",
    wearables: "Wearables",
    wearablesNote: "Keine Anbindung in Pilotphase 1.",
    unavailable: "Die Quellen sind derzeit nicht abrufbar.",
  },
  consentTextsPage: {
    lead: "Die Einwilligungen, die die Praxis dokumentiert, und die Fassung des Textes, auf die sich jede bezieht.",
    current: "Aktuelle Fassung",
    currentNote:
      "Jede neu dokumentierte Einwilligung bezieht sich auf diese Fassung. Eine geänderte Formulierung bekommt eine neue Versionsnummer; erfasste Einwilligungen behalten ihre.",
    placeholder:
      "Die Formulierungen sind Platzhalter der Pilotphase. Die endgültigen Texte erstellt die Datenschutzberatung der Praxis; sie werden mit einer neuen Version eingespielt, nicht hier bearbeitet.",
    purposes: "Zwecke",
    counts: "Erfasst in dieser Praxis",
    caption: "Einwilligungen je Zweck und Fassung",
    columns: {
      purpose: "Zweck",
      version: "Fassung",
      granted: "Erteilt",
      withdrawn: "Widerrufen",
    },
    none: "Noch keine Einwilligung dokumentiert.",
    unavailable: "Die Zahlen sind derzeit nicht abrufbar.",
  },
  retentionPage: {
    lead: "Wie lange die Praxis Daten aufbewahrt, wie eine Patientin ihre Daten erhält, und wie gelöscht wird.",
    policy: "Aufbewahrungsfristen",
    policyNote:
      "Noch keine Richtlinie hinterlegt. Die Fristen legt die Praxis als Verantwortliche mit ihrer Datenschutzberatung fest. Bis dahin löscht die Plattform nichts von sich aus.",
    export: "Datenauskunft (Art. 15 und 20 DSGVO)",
    exportNote:
      "Der Inhaber erstellt sie auf der Seite der Patientin oder des Patienten: eine Datei mit allem, was die Akte enthält. Jede Auskunft steht im Audit-Protokoll.",
    deletion: "Löschung (Art. 17 DSGVO)",
    deletionNote:
      "Nach dem Vier-Augen-Prinzip: Der Inhaber beantragt, die Ärztliche Leitung entscheidet, dann wird ausgeführt.",
    deletionState: "{open} offen · {executed} ausgeführt",
    deletionLink: "Zu den Löschanträgen",
    backup: "Sicherung und Wiederherstellung",
    backupNote:
      "In dieser Pilotumgebung nicht eingerichtet. Verschlüsselte Sicherungen in der EU mit geprüfter Wiederherstellung sind eine Bedingung vor echten Patientendaten.",
    unavailable: "Derzeit nicht abrufbar.",
  },
  // Settings → profile and security (everyone, about themselves).
  profilePage: {
    lead: "So stehen Sie in dieser Praxis und im Audit-Protokoll.",
    account: "Konto",
    name: "Name",
    email: "E-Mail-Adresse",
    role: "Rolle in dieser Praxis",
    clinic: "Praxis",
    clinics: "Ihre Praxen",
    clinicsNote:
      "Gehören Sie zu mehreren Praxen, wählen Sie die Praxis nach der Anmeldung.",
    current: "aktuell",
    source:
      "Name und E-Mail-Adresse kommen aus der Anmeldung und werden nicht hier geändert: In der Pilotumgebung sind es synthetische Konten; mit der Anmeldestelle der Praxis (OIDC) ändern Sie sie dort.",
  },
  securityPage: {
    lead: "Wie Sie sich anmelden, und wo Sie gerade angemeldet sind.",
    signIn: {
      title: "Anmeldung",
      method: "Verfahren",
      mfa: "Zweiter Faktor",
      dev: "Entwicklungsanmeldung: ohne Passwort und ohne zweiten Faktor. Es gibt sie nur in der Pilotumgebung mit synthetischen Daten; im Betrieb ist sie abgeschaltet.",
      oidc: "Die Anmeldestelle Ihrer Praxis (OIDC).",
      mfaDev: "Nicht vorhanden in der Entwicklungsanmeldung.",
      mfaOidc:
        "Richtet die Anmeldestelle Ihrer Praxis ein und fragt ihn ab; diese Plattform sieht ihn nicht.",
    },
    sessions: {
      title: "Ihre Sitzungen",
      note: "Die letzten zehn. Gespeichert werden Beginn, Ablauf und die zuletzt gewählte Praxis – kein Gerät und keine Adresse.",
      caption: "Ihre Sitzungen, neueste zuerst",
      columns: {
        started: "Begonnen",
        state: "Stand",
        until: "Bis",
        clinic: "Praxis",
      },
      states: {
        active: "aktiv",
        ended: "beendet",
        expired: "abgelaufen",
      },
      current: "diese Sitzung",
      endOthers: "Alle anderen Sitzungen beenden",
      endConfirm:
        "Alle anderen Sitzungen beenden? Wer dort angemeldet ist, muss sich neu anmelden. Diese Sitzung bleibt.",
      ended: {
        one: "{n} Sitzung beendet.",
        other: "{n} Sitzungen beendet.",
      },
      none: "Keine andere Sitzung ist aktiv.",
      failed:
        "Die Sitzungen konnten nicht beendet werden. Bitte erneut versuchen.",
      unavailable: "Die Sitzungen sind derzeit nicht abrufbar.",
    },
  },
  // Language and appearance, under Einstellungen.
  appearance: {
    title: "Sprache & Darstellung",
    note: "Gilt für Sie auf diesem Gerät. Klinische Bezeichnungen, Laborangaben und Namen bleiben in der Sprache, in der sie erfasst wurden.",
    language: {
      label: "Sprache der Oberfläche",
      help: "Deutsch ist die Standardsprache der Pilotphase.",
    },
    theme: {
      label: "Erscheinungsbild",
      help: "Hell, dunkel oder wie das System dieses Geräts eingestellt ist.",
      light: "Hell",
      dark: "Dunkel",
      system: "System",
    },
    formats: {
      label: "Zahlen und Daten",
      help: "Die Schreibweise folgt der Sprache; Datum und Uhrzeit stehen auf der Uhr der Praxis.",
    },
    progress: {
      label: "Stand der Übersetzung",
      summary: "Was auf Englisch verfügbar ist",
    },
  },
  language: {
    title: "Sprache",
    note: "Die Sprache der Oberfläche auf diesem Gerät. Inhalte wie Berichte, Bezeichnungen aus dem Labor und Namen bleiben in der Sprache, in der sie erfasst wurden.",
    // Says exactly what is done. To be widened with every part, and removed with the last page.
    progress:
      "Alle Seiten des Praxisteams sind auf Englisch umgestellt. Die Seiten für Patientinnen und Patienten, die Einladungsseiten und die Fehlerseite erscheinen vorerst auf Deutsch. Der Wortlaut der Einwilligungszwecke, die klinischen Bezeichnungen (Domänen, CIS, Actionability, Follow-up- und Endpunkt-Adäquanz, Tri-State-Achsen und ihre Zustände, Lage zum Referenzintervall, Vergleichbarkeit), die Gründe der Prüfaufgaben und die Gründe einer Zurückweisung bleiben Deutsch.",
    selected: "ausgewählt",
    choose: "Sprache der Oberfläche",
  },
};

// The same shape with any wording in it.
type Wording<T> = {
  [K in keyof T]: T[K] extends string ? string : Wording<T[K]>;
};
export type Messages = Wording<typeof de>;
