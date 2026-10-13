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
  // The patient page (app/patients/[id]): its header and actions, the data coverage, the three
  // cards (consent, laboratory files, data export), its dialogs, and what its server actions
  // answer. NOT here, and German on the page whatever the interface says: the closed
  // vocabularies the page shows — the names of the six domain axes, follow-up adequacy, the
  // position against the reference interval, the comparability notes (ADR-0007: their English
  // needs the medical director) — and the wording of the consent purposes (versioned text).
  patientPage: {
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
    domains: {
      noRun:
        "Noch kein Interpretationslauf — die sechs Domänen-Achsen werden als Entwurf angezeigt.",
      select: "Domäne {axis} auswählen",
      // The name of the fact; its value is a closed vocabulary and stays German.
      adequacy: "Follow-up-Adäquanz:",
      citesReplaced:
        "Stützt sich auf einen vom Labor korrigierten Wert — Interpretation prüfen.",
      shown: "Biomarker im Beobachtungsnachweis",
      show: "Biomarker ansehen ({n})",
      notInterpreted: "Noch nicht interpretiert",
    },
    evidence: {
      title: "Beobachtungsnachweis",
      note: "Quellengebundene Beobachtungen · Lage relativ zum Quellreferenzintervall · keine automatische Diagnose oder Therapieempfehlung.",
      columns: {
        marker: "Marker",
        category: "Kategorie",
        value: "Wert",
        change: "Δ",
        position: "Lage z. Referenz",
        bar: "Referenzlage",
      },
      open: "Marker {name} öffnen",
      superseded: "durch Laborkorrektur ersetzt",
      inputReplaced: "Eingangswert durch Laborkorrektur ersetzt",
      empty: "Keine Beobachtungen in dieser Domäne.",
      noScale: "keine Skala",
      reference: "Ref {range}",
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
      "Englisch wird Seite für Seite ergänzt: die Navigation, die Anmeldung, die Übersicht, die Patientenliste, die Patientenseite und diese Übersicht der Einstellungen sind umgestellt; alle übrigen Seiten erscheinen vorerst auf Deutsch. Der Wortlaut der Einwilligungszwecke und die klinischen Bezeichnungen (Domänen, Follow-up-Adäquanz, Lage zum Referenzintervall, Vergleichbarkeit) bleiben Deutsch.",
    selected: "ausgewählt",
    choose: "Sprache der Oberfläche",
  },
};

// The same shape with any wording in it.
type Wording<T> = {
  [K in keyof T]: T[K] extends string ? string : Wording<T[K]>;
};
export type Messages = Wording<typeof de>;
