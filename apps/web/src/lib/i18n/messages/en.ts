import type { Messages } from "./de";

// English wording of the interface. Typed against the German source: a key that is missing
// here, or one that exists only here, does not compile. The same intended-use rules hold as
// for the German (apps/api/tests/test_web_copy_language.py scans this file too): the wording
// names observations, reviews and records — nothing the product does not do.
export const en: Messages = {
  shell: {
    navAria: "Main navigation",
    workspace: "Workspace",
    overview: "Overview",
    patients: "Patients",
    reviewQueue: "Review queue",
    administration: "Administration",
    settings: "Settings",
    pilot: "Pilot environment",
    pilotNote: "Synthetic sample data · no real patient care.",
    signOut: "Sign out",
    clinic: "Clinic: ",
    toggleTheme: "Switch theme",
    skipLink: "Skip to main content",
    brandAria: "HADP overview",
    menu: "Menu",
    closeMenu: "Close menu",
  },
  roles: {
    owner: "Owner",
    clinician: "Clinician",
    assistant: "Assistant",
    medical_director: "Medical director",
  },
  meta: {
    description:
      "Clinical, source-grounded workspace — human review before every release.",
  },
  login: {
    homeAria: "HADP home",
    kicker: "Clinical workspace",
    title: "Understand health data. Document decisions traceably.",
    lead: "A calm, source-grounded workspace for longevity and preventive-care clinics – with human review before every release.",
    trustAria: "About this environment",
    sessionsLimited: "Sessions are time-limited",
    audited: "Access and changes are recorded for the audit trail",
    pilot:
      "Pilot environment with synthetic sample data – no real patient care",
    sectionAria: "Sign-in",
    eyebrow: "Clinical access",
    heading: "Sign in",
    devNote:
      "Pilot environment with synthetic sample data. Signing in here needs no password – only the e-mail address of an account that has been set up.",
    noneHeading: "Sign-in is not set up",
    noneNote:
      "No sign-in method is set up for this environment. Signing in is not possible at present.",
    unreachableHeading: "Sign-in is not possible at the moment",
    unreachableNote:
      "The sign-in service cannot be reached. Please try again in a few minutes.",
    retry: "Try again",
    emailLabel: "E-mail address",
    submit: "Sign in",
    pending: "Signing in …",
    purposeNote:
      "Access to patient data is bound to its purpose and is recorded.",
    errorNoClinic: "No clinic is available for this account.",
    errorFailed: "Sign-in failed. Please try again.",
  },
  dashboard: {
    status: {
      review: "In review",
      approved: "Approved",
      released: "Released",
      rejected: "Rejected",
      none: "No draft",
    },
    reportVersion: "Report · v{version}",
    time: {
      now: "just now",
      minutes: "{n} min ago",
      hours: "{n} h ago",
      yesterday: "yesterday",
      days: "{n} d ago",
    },
  },
  overview: {
    kicker: "Clinical workspace",
    title: "Overview",
    lead: {
      none: "Nothing is waiting for you right now.",
      one: "{n} item is waiting for you.",
      other: "{n} items are waiting for you.",
    },
    leadRole: {
      clinician: "Source-grounded drafts are reviewed before any release.",
      medical_director:
        "Only what was clinically reviewed and approved is released.",
      assistant:
        "Reviewing, approving and releasing stay with the clinical roles.",
      owner:
        "For the clinic: the team, deletion requests and preparation time.",
    },
    synthetic: "Synthetic demo data.",
    statband: {
      label: "Key figures",
      openReviews: {
        label: "Open reviews",
        help: "Clinical review pending",
      },
      toRelease: {
        label: "To release",
        help: "Waiting for medical release",
      },
      valuesInReview: {
        label: "Values in review",
        help: "Review queue, not yet published",
      },
      released: {
        label: "Released · {days} d",
        help: "Per day, oldest on the left",
        unavailable: "Not available at present",
      },
      patients: {
        label: "Patients",
        help: "{withReport} with a report · {without} without a draft",
      },
    },
    today: {
      title: "Today",
      note: "Ordered by where the work stands and how long it has waited, not by clinical urgency. The order is workflow, not a judgement.",
      asOf: "As of {time}",
      tiers: {
        now: { title: "Now", tag: "waiting for you" },
        soon: { title: "Next", tag: "new values" },
        fyi: { title: "For information", tag: "no action needed" },
      },
      count: { one: "{n} entry", other: "{n} entries" },
      empty: {
        now: "Nothing is waiting for your role.",
        soon: "No new values and no record without a draft.",
        fyi: "Nothing new in the last 7 days.",
      },
      waited: "waiting since {since}",
      kinds: {
        review_draft: {
          what: "Report v{version}: clinical review open",
          action: "Review",
        },
        rework_rejected: {
          what: "Report v{version} rejected: rework open",
          action: "Rework",
        },
        decide_values: {
          what: {
            one: "{n} value is waiting for a decision",
            other: "{n} values are waiting for a decision",
          },
          action: "Decide",
        },
        release: {
          what: "Report v{version} approved: release open",
          action: "Open",
        },
        decide_deletion: {
          what: "Deletion request: decision open",
          action: "Decide",
        },
        execute_deletion: {
          what: "Deletion approved, not yet carried out",
          action: "Show",
        },
        upload_values: {
          what: "No values in the record yet",
          action: "Open record",
        },
        invitation_open: {
          title: "Invitation · {role}",
          what: "Not yet redeemed · expires on {until}",
          action: "Show",
        },
        prep_baseline: {
          title: "Preparation time",
          what: "The clinic's baseline has not been recorded yet",
          action: "Record",
        },
        prep_follow_up: {
          title: "Preparation time",
          what: "No new statement for more than {days} days",
          action: "Record",
        },
        values_since_run: {
          what: {
            one: "{n} value received after the latest interpretation",
            other: "{n} values received after the latest interpretation",
          },
          detail: "Latest interpretation: run {run}",
          action: "Open record",
        },
        no_draft: {
          what: {
            one: "{n} published value, no draft yet",
            other: "{n} published values, no draft yet",
          },
          action: "Open record",
        },
        approved_waiting: {
          what: "Report v{version} approved: waiting for medical release",
          action: "Show",
        },
        deletion_waiting: {
          what: "Deletion request: waiting for the medical director",
          action: "Show",
        },
        released_recently: {
          title: {
            one: "{n} report released",
            other: "{n} reports released",
          },
          ref: "last 7 days",
          action: "Work list",
        },
      },
    },
    worklist: {
      title: "Work list",
      note: "By report status · not a diagnosis or treatment advice.",
      tabs: {
        open: "Open reviews",
        approved: "To release",
        released: "Released",
        rejected: "Rejected",
        none: "No draft",
        all: "All",
      },
      search: "Search patient or ID",
      columns: {
        patient: "Patient",
        state: "State",
        next: "Next step",
        values: "Values",
        updated: "Updated",
      },
      next: {
        clinical_review: { title: "Clinical review", who: "by the {role}" },
        release: { title: "Release", who: "by the {role}" },
        rework: { title: "Rework", who: "a new version after the rejection" },
        none: { title: "Nothing open", who: "released {since}" },
        draft: { title: "Create a draft", who: "from the published values" },
        import: { title: "Read in values", who: "no values in the record yet" },
      },
      inReview: "{n} in review",
      openRow: "Open patient {name}, {ref}",
      emptyTitle: "No matching items",
      emptyNote: "Change the filter or the search term.",
    },
    practice: {
      title: "Clinic · {days} days",
      note: "Drafts created and reviews signed, per calendar week · real timestamps.",
      range: "{from} – {to}",
      week: "W {week}",
      created: "Created",
      signed: "Signed",
      released: "Released",
      chartLabel:
        "Drafts created and reviews signed, per calendar week. Every number is also in the table.",
      showTable: "Show as a table",
      columns: {
        week: "Calendar week",
        days: "Days in the period",
      },
      median: "Median from first draft to approval · 30 d",
      medianNote: "Turnaround, not working time",
      tooFew: "From {minimum} reports · {n} so far",
      baseline: "The clinic's baseline",
      baselineNote: "Self-reported, median per appointment",
      baselineValue: "{n} min",
      noBaseline: "Not recorded yet",
      foot: "Two different measures; they are not set against each other. More under Settings › Preparation time.",
      unavailable: "The clinic's figures are not available at present.",
    },
    duration: {
      minutes: "{n} min",
      hours: "{n} h",
      days: "{n} d",
    },
    data: {
      title: "Data coverage",
      note: {
        one: "Count over {n} observation · no quality rating.",
        other: "Count over {n} observations · no quality rating.",
      },
      published: "Published",
      withReference: "With a source reference interval",
      withKpi: "Linked to a catalog marker",
      latest: "Newest observation",
      unavailable: "The data coverage is not available at present.",
    },
    sources: {
      title: "Sources",
      names: {
        csv: "CSV (HADP layout)",
        ldt2: "LDT 2",
        ldt3: "LDT 3",
        other: "By hand or through the interface",
        wearables: "Wearables",
      },
      last: {
        one: "Last {when} · {n} row",
        other: "Last {when} · {n} rows",
      },
      neverFile: "No file read yet",
      neverOther: "Nothing entered yet",
      wearablesNote: "Not connected in pilot phase 1",
      state: {
        used: "in use",
        ready: "ready",
        none: "not connected",
      },
      unavailable: "The sources are not available at present.",
    },
    activity: {
      title: "Recent activity",
      noteClinic:
        "From the clinic's audit trail, without reads and sign-ins · the same wording as under Settings › Audit trail.",
      noteOwn:
        "Your own actions, without reads and sign-ins. The owner reads the full trail.",
      open: "Open the trail",
      empty: "No actions yet.",
      unavailable: "The activity is not available at present.",
    },
  },
  patients: {
    kicker: "Clinic · {clinic}",
    title: "Patients",
    count: { one: "{n} patient", other: "{n} patients" },
    lead: "· pseudonymised, synthetic sample data.",
    chips: {
      total: { label: "Total", help: "In this clinic" },
      withReport: { label: "With a report", help: "At least one report draft" },
      open: { label: "Open assessments", help: "Clinical review pending" },
    },
    directory: {
      title: "Patient directory",
      note: "Pseudonymised · not a diagnosis or treatment advice.",
    },
    tabs: {
      all: "All",
      open: "Open reviews",
      released: "Released",
      none: "No report",
    },
    search: "Search patient or ID",
    emptyTitle: "No patient records yet",
    emptyNote:
      "Create the first record — guided in three steps, with a duplicate check and a documented consent.",
    firstRecord: "Create the first record",
    columns: {
      patient: "Patient",
      age: "Age",
      lastAssessment: "Last assessment",
      status: "Status",
    },
    openRow: "Open patient {name}, {ref}",
    noneTitle: "No patients in this view",
    noneNote: "Choose another filter or change the search.",
    showing: "Showing {shown} of {total}",
    loading: "Loading the patient directory …",
  },
  addPatient: {
    open: "Add patient",
    subtitle: "Synthetic demo data · no real patient.",
    steps: "Steps",
    stepNames: {
      identity: "Identity",
      consent: "Consent",
      review: "Review",
    },
    stepLabel: "{n}. {label}",
    stepDone: "{n}. {label} – completed",
    optional: "(optional)",
    cancel: "Cancel",
    back: "Back",
    next: "Next",
    close: "Close",
    openRecord: "Open record",
    discard: {
      title: "Discard what you entered?",
      note: "What you have entered so far will not be saved.",
      keep: "Keep editing",
      confirm: "Discard",
    },
    identity: {
      title: "Identity & basic details",
      name: "Name",
      namePlaceholder: "e.g. Maria Example",
      dob: "Date of birth",
      ref: "External ID",
      refPlaceholder: "e.g. SYN-0042",
      refHint: "Reference in your practice system.",
      duplicateNote:
        "Before the record is created, the clinic is checked for possible duplicates.",
    },
    consent: {
      title: "Consents",
      note: "Consents given in person are documented with a timestamp, the purpose and the person who recorded them (unchangeable log). Alternatively, the person can give them themselves later through the invitation link.",
      channel:
        "Recorded: in person · the pilot environment's catalogue of purposes (synthetic data).",
    },
    review: {
      title: "Review & confirm",
      name: "Name",
      dob: "Date of birth",
      age: { one: "· {n} year", other: "· {n} years" },
      ref: "External ID",
      consents: "Consents",
      noConsents: "None documented",
      create: "Create patient",
      creating: "Creating …",
    },
    duplicates: {
      running: "Checking for duplicates …",
      unavailable: "The duplicate check is not available at present.",
      retry: "Check again",
      strong: "Possibly on record already",
      similar: "Similar entry in the clinic",
      match: {
        external_ref: "Same external ID",
        name_dob: "Name + date of birth",
        name: "Same name",
      },
      createAnyway: "Create anyway — this is a different person.",
      none: "No matches found in the clinic.",
    },
    done: {
      title: "Patient created",
      summary: "· synthetic demo record · {consents}.",
      consents: {
        one: "{n} consent documented",
        other: "{n} consents documented",
      },
      noConsents: "no consents documented",
      inviteTitle: "Invitation for the person to give consent themselves",
      inviteNote:
        "The person can also give consents themselves through a single-use invitation link.",
      inviteLink: "Invitation link",
      copy: "Copy",
      copied: "Copied",
      validUntil:
        "Valid until {when} · shown only once — please pass it on safely and in person.",
      createLink: "Create invitation link",
      creatingLink: "Creating …",
      another: "Add another person",
    },
    errors: {
      nameRequired: "Please enter a name.",
      nameTooLong: "The name may have 200 characters at most.",
      dobInvalid: "Please enter a valid date of birth.",
      dobFuture: "The date of birth must not lie in the future.",
      dobTooEarly: "Please enter a date of birth from {year} on.",
      refTooLong: "The external ID may have 120 characters at most.",
      signInAgain: "Not authorised. Please sign in again.",
      duplicate: "The clinic already has an entry with these details.",
      checkInput: "The record was not created. Please check what you entered.",
      failed: "The record was not created. Please try again.",
    },
    invitationErrors: {
      invalidPatient: "Invalid patient reference.",
      notAllowed: "Your role does not allow this action.",
      tooMany: "Too many invitations. Please try again later.",
      failed: "The invitation was not created. Please try again.",
    },
  },
  patientPage: {
    back: "Back to patients",
    cancel: "Cancel",
    close: "Close",
    notAllowed: "Your role does not allow this action.",
    invalidPatient: "Invalid patient reference.",
    recordUnavailable: "This record is not available.",
    erased: {
      title: "This record has been deleted",
      note: "This person's data has been anonymised and irrevocably removed (observations, documents and reports). The entry remains only as evidence in the audit trail.",
    },
    reportStatus: {
      draft: "Clinical review open",
      approved: "Passed on for release by a physician",
      released: "Released",
      rejected: "Rejected",
      none: "No draft",
    },
    age: { one: "{n} year", other: "{n} years" },
    ageUnknown: "Age unknown",
    noReport: "No report",
    reportVersion: "Report · v{version}",
    actions: {
      openReport: "Open report",
      createDraft: "Create report draft",
      creatingDraft: "Creating the draft …",
      recordInterpretation: "Record interpretation",
      invite: "Invite patient",
      requestDeletion: "Request deletion",
    },
    coverage: {
      title: "Data coverage",
      note: "Deterministic, from the observations · not a clinical quality rating.",
      observations: "Observations",
      published: "published",
      withReference: "with reference",
      latest: "latest measurement",
      today: "today",
      days: "{n} d",
    },
    // Before a visit: counts of recorded values, each a filter of the domain lists.
    prep: {
      title: "Before the visit",
      note: "Counted from the recorded values. Each count filters the domain lists below; none is a rating.",
      lastRun: "Last interpretation: run {n} · {date}",
      noRun: "No interpretation recorded yet",
      facts: {
        since_run: {
          label: {
            one: "value since the last interpretation",
            other: "values since the last interpretation",
          },
          note: "Received after {date}",
          noRun: "Without an interpretation there is no “since”",
        },
        outside: {
          label: {
            one: "marker outside the source reference interval",
            other: "markers outside the source reference interval",
          },
          note: "By the latest published value",
        },
        pending: {
          label: {
            one: "value awaiting review",
            other: "values awaiting review",
          },
          note: "Not published, used in no change",
        },
        missing: {
          label: {
            one: "core marker without a published value",
            other: "core markers without a published value",
          },
          note: "Of the catalog's {n} core markers",
        },
      },
      filtered: {
        since_run:
          "Showing only markers with a value received after the last interpretation.",
        outside:
          "Showing only markers whose latest published value lies outside the source reference interval.",
        pending: "Showing only markers with a value awaiting review.",
        missing: "Showing only core markers without a published value.",
      },
      showAll: "Show all markers",
    },
    domains: {
      title: "Domains",
      note: "The six domains of the interpretation model. Values belong to a domain through the KPI catalog – also before any interpretation is recorded.",
      go: "{axis}: go to the marker list",
      coreMarkers: { one: "{n} core marker", other: "{n} core markers" },
      coverage: "{x} of {n} with a published value",
      noCore: "No core markers in the catalog",
      noValue: "No published value yet",
      outside: {
        one: "{n} marker outside the source reference interval",
        other: "{n} markers outside the source reference interval",
      },
      outsideNone: "No latest value outside the source reference interval",
      pending: {
        one: "{n} value awaiting review",
        other: "{n} values awaiting review",
      },
      pendingNone: "Nothing awaiting review",
      latest: "Latest published value from {date}",
      interpretation: "Clinician's interpretation",
      reviewed: "Reviewed",
      draft: "Draft",
      none: "No run",
      run: "Run {n} · recorded on {date}",
      adequacy: "Follow-up adequacy:",
      sinceRun: {
        one: "{n} value received after this interpretation",
        other: "{n} values received after this interpretation",
      },
      citesReplaced:
        "Relies on a value the laboratory has corrected — check the interpretation.",
      notInterpreted: "Not interpreted yet",
    },
    evidence: {
      eyebrow: "Domain",
      note: "Source-grounded observations · position relative to the source reference interval · not a diagnosis or treatment advice.",
      counts: "{x} of {n} core markers with a published value",
      filteredCount: {
        one: "{n} row in the filter",
        other: "{n} rows in the filter",
      },
      columns: {
        marker: "Marker",
        value: "Latest value",
        change: "Change",
        position: "Position vs. reference",
        bar: "Reference position",
        measured: "Measured",
      },
      open: "Open marker {name}",
      catalogName: "Name in the catalog",
      measurementClass: {
        laboratory: "Laboratory",
        vital_sign: "Vital sign",
        anthropometric: "Anthropometry",
        body_composition: "Body composition",
        functional_test: "Functional test",
        wearable: "Wearable",
        imaging: "Imaging",
        derived: "Derived",
        omics: "Omics",
      },
      missing: "No value recorded",
      pending: {
        one: "{n} value awaiting review",
        other: "{n} values awaiting review",
      },
      corrected: "corrected by the laboratory",
      noChange: "—",
      ago: {
        today: "today",
        days: { one: "{n} day ago", other: "{n} days ago" },
        months: { one: "{n} month ago", other: "{n} months ago" },
      },
      alsoRelevant: "Also relevant here",
      alsoRelevantNote:
        "Kept and counted in their own domain; shown here for an overview.",
      superseded: "replaced by a laboratory correction",
      inputReplaced: "input value replaced by a laboratory correction",
      empty: "No observations in this domain.",
      emptyFilter: "No marker of this domain matches the filter.",
      noScale: "no scale",
      reference: "Ref {range}",
    },
    // A marker's history: its sparkline in the domain list and its chart in the dialog.
    history: {
      column: "History",
      title: "History",
      chartLabel:
        "History of {name}. Every value is also in the table beneath.",
      summary: {
        none: "{name}: no published value yet.",
        one: "{name}: one published value, from {to}: {value}.",
        other:
          "{name}: {n} published values between {from} and {to}; the latest is {value}.",
      },
      pending: {
        one: "{n} value is awaiting review.",
        other: "{n} values are awaiting review.",
      },
      replaced: {
        one: "{n} value was replaced by a laboratory correction.",
        other: "{n} values were replaced by a laboratory correction.",
      },
      notDrawn: {
        one: "{n} value is not drawn (rejected or not a number) and is listed only in the table.",
        other:
          "{n} values are not drawn (rejected or not a number) and are listed only in the table.",
      },
      legend: {
        value: "Published value",
        joined: "Line: change calculated",
        interval: "Source reference interval, per value",
        outside: "Outside the source reference interval",
        pending: "Awaiting review",
        replaced: "Replaced by a laboratory correction",
      },
      today: "today",
      foot: "Recorded values only: no trend line, no smoothing, no forecast. A line joins two values only where the platform calculated a change between them.",
    },
    unassigned: {
      title: "Not assigned to a catalog marker",
      note: "Values the import could not link to a marker. They stay visible here and are decided in the review queue; until then they belong to no domain.",
      openQueue: "Open the review queue",
    },
    valueStatus: {
      published: "published",
      pending: "in review – not published",
      rejected: "rejected in review",
    },
    sourceNote: {
      text: {
        short: "As written by the source",
        full: "The platform reads no number from what the source wrote here – for instance a text result, an addition to the value, or a way of writing a number that it cannot read unambiguously. What the source wrote is shown as written.",
      },
      converted: {
        short: "converted from {source}",
        full: "The source states {source}; the value – and the reference interval, where one is shown – was converted to {unit}.",
        unitOfMetric: "the unit of the metric",
      },
      source_unit: {
        short: "Unit of the source",
        full: "The value stands as the source states it, in the source's unit – and so does a reference interval that is shown. The value is not normalised; a change from the previous value is therefore not calculated.",
      },
    },
    marker: {
      kicker: "Marker detail ·",
      reference: "Reference",
      change: "Change",
      source: "Source / code",
      status: "Review status",
      noPosition:
        "No position relative to the reference interval is stated for a value that is not published.",
      positionNote:
        "Position relative to the source reference interval · not a diagnosis or treatment advice.",
      values: "All values of this marker",
      valueColumns: {
        measured: "Measured",
        value: "Value",
        asReported: "As reported",
        reference: "Source interval",
        status: "Status",
        change: "Change",
      },
    },
    audit: {
      title: "Audit status",
      note: "Progress from data capture to release to the patient (derived from the report status).",
      none: "No report draft yet — the audit lifecycle begins when a draft is created.",
      steps: {
        capture: { label: "Data capture", done: "Values published" },
        draft: { label: "Draft created", done: "Source-grounded" },
        clinical: {
          label: "Clinical review",
          done: "Signed",
          active: "In progress",
          pending: "Pending",
          rejected: "Version rejected",
        },
        release: {
          label: "Release by a physician",
          done: "Completed",
          active: "In review",
          pending: "Pending",
          rejected: "Did not take place",
        },
        patient: {
          label: "Release to the patient",
          done: "Released",
          pending: "Not possible",
          rejected: "Rejected — rework needed",
        },
      },
    },
    invite: {
      title: "Invite patient?",
      note: "Creates a single-use, time-limited invitation link through which the consent (report release) is recorded. The link is shown exactly once. Synthetic demo: no real patient.",
      doneTitle: "Invitation created — single-use link",
      doneNote:
        "Share the link by hand and safely outside the system — nothing is sent automatically. It can be used once, is time-limited and is shown only now. Synthetic demo: no real patient.",
      link: "Invitation link (shown once)",
      copy: "Copy link",
      copied: "Link copied",
      create: "Create invitation",
    },
    deletion: {
      title: "Request deletion",
      noteBefore: "This files a request for the final deletion of the data of",
      noteAfter:
        ". Nothing is deleted at once — the medical director has to approve the request (two-person approval); it is carried out separately and cannot be undone.",
      reason: "Reason",
      reasons: {
        patient_request: "Data subject request (Art. 17)",
        withdrawn_consent: "Consent withdrawn",
        data_minimization: "Data minimisation",
      },
      submit: "Request deletion",
      submitting: "Filing the request …",
      doneTitle: "Deletion request filed",
      doneNote:
        "The medical director reviews the request (two-person approval). Until it is approved and carried out separately, the record stays unchanged. You find the request under Settings → Deletion requests.",
      errors: {
        invalidReason: "Invalid reason.",
        alreadyOpen:
          "There is already an open deletion request for this patient.",
        failed: "The deletion request was not filed. Please try again.",
      },
    },
    consent: {
      title: "Consents",
      note: "State per purpose. Every entry is a new, attributed and audited record — earlier entries are never changed.",
      readOnly:
        " Documenting is reserved for the practice team (read-only view).",
      active: "Active",
      inactive: "Not active",
      notDocumented: "Not documented",
      granted: "Given on {day} ({how}) · text version {version}",
      withdrawn: "Withdrawn on {day} ({how}) · text version {version}",
      channels: { in_person: "declared in person" },
      recordGrant: "Document consent",
      recordWithdrawal: "Document withdrawal",
      footnoteBefore:
        "Synthetic demo: the purposes and the consent text are placeholders. At present only the purpose",
      footnoteAfter:
        "is enforced technically (no release without an active consent; a withdrawal revokes existing access links). The other purposes are documented, but not yet enforced technically.",
      grantTitle: "Document consent?",
      withdrawTitle: "Document withdrawal?",
      grantNote:
        "You document that the person agreed to this purpose in person. The record is attributed to you and audited; it cannot be changed, only added to by a withdrawal.",
      withdrawNote:
        "You document that the person withdrew their consent in person. The record is attributed to you and audited; the earlier consent stays as an entry.",
      withdrawReleaseNote:
        " The person's existing access links become invalid at once; a new release is possible only after a new consent.",
      confirmGrant: "Document",
      errors: {
        unknownPurpose: "Unknown consent purpose.",
        unknownAction: "Unknown action.",
        notSaved: "Not saved. Please try again.",
      },
    },
    lab: {
      title: "Laboratory data",
      note: "A structured laboratory file (CSV in the HADP layout, LDT 2 or LDT 3) for exactly this record. The original file is stored and then read; the values are taken over unchanged. Values that are not unambiguous go to the review queue — they are published only after a clinical decision.",
      choose: "Choose laboratory file",
      upload: "Upload and read",
      uploading: "Reading …",
      readOnly:
        "Uploading and reading is reserved for the practice team (read-only view).",
      read: "Read ({parser} v{version}): ",
      readBefore:
        "This file has been read before — result of the first reading: ",
      counts: {
        published: "{n} published",
        review: "{n} for review",
        duplicate: "{n} already on record",
        notImported: "{n} not taken over",
      },
      toQueue: "To the review queue",
      stored: " The original file is stored and listed below.",
      none: "No laboratory file is stored for this record yet.",
      table: "Stored laboratory files",
      columns: {
        file: "File",
        uploaded: "Uploaded",
        reader: "Reader",
        result: "Result",
      },
      storedNotRead: "Stored, not read",
      readNow: "Read",
      legend:
        "“Already on record”: the value is already held, identical, for this analysis and collection time and was not taken over twice. “Not taken over”: a result without a numeric value or without a collection date (for example a text finding, or still pending). The figures show the state at the time of reading.",
      errors: {
        invalidReference: "Invalid reference.",
        chooseFile: "Please choose a file.",
        tooLarge5: "The file is too large (5 MB at most).",
        nameTooLong: "The file name is too long (200 characters at most).",
        uploadFailed: "The upload failed. Please try again.",
        tooManyUploads:
          "Too many uploads in a short time. Please wait a moment.",
        otherPatient:
          "This file is already stored with another record of this clinic and is not accepted here a second time.",
        empty: "The file is empty.",
        tooLarge: "The file is too large.",
        notText: "The file is not a readable text file (UTF-8 expected).",
        wrongType: "This file type is not accepted (CSV, LDT or text).",
        importNotAllowed: "Your role does not allow reading a file.",
        tooManyImports:
          "Too many imports in a short time. Please wait a moment.",
        importFailed: "Reading failed. Please try again.",
        line: " (line {line})",
        nothingTaken: "{reason}{where} Nothing was taken over.",
        unreadableCode:
          "The file could not be read (reason: {code}){where}. Nothing was taken over.",
        unreadable: "The file could not be read. Nothing was taken over.",
      },
      refusals: {
        unsupported_format:
          "There is no reader for this file format (supported: CSV in the HADP layout, LDT 2, LDT 3).",
        multiple_patients:
          "The file holds findings for more than one person. A file must concern exactly one person.",
        unidentified_patient:
          "The file does not name exactly one person. A file must concern exactly one person.",
        patient_mismatch:
          "The file states a date of birth other than this record's.",
        checksum_mismatch:
          "The checksum of the LDT file does not match — the file is damaged or incomplete.",
        malformed_record:
          "The LDT file is incomplete or does not follow the format.",
        malformed_object:
          "The LDT file is incomplete or does not follow the format.",
        unsupported_ldt_version: "This LDT version is not read.",
        unsupported_record_type:
          "The LDT file holds a record type that is not read (laboratory findings only).",
        unsupported_report_kind:
          "The LDT file holds a record type that is not read (laboratory findings only).",
        unsupported_layout:
          "The table header does not hold the expected columns (analyte, value, date).",
        ambiguous_header: "The table header names a column twice.",
        malformed_table:
          "A row does not have as many fields as the table header (often: a decimal comma in a comma-separated file).",
        missing_field: "A row lacks the analyte, the value or the date.",
        unsupported_date:
          "A date cannot be read unambiguously (expected: DD.MM.YYYY or YYYY-MM-DD).",
        implausible_date: "A date lies outside the plausible span.",
        unsupported_time: "A time cannot be read (expected: HH:MM).",
        empty_document: "The file holds no laboratory values.",
        too_many_values:
          "The file holds more values than a single set of laboratory findings has.",
        document_unavailable:
          "The stored original file cannot be read. Please upload it again.",
      },
    },
    dataExport: {
      title: "Data export",
      noteBefore:
        "A file with the data stored about this person, for an access request (Art. 15 GDPR) or data portability (Art. 20 GDPR): master data, consent records, all values, the original files read into this record and the released report versions.",
      notIncluded: "Not included",
      noteAfter:
        "are, among other things, report versions that were not released, the working documentation of the interpretation, review decisions, the audit trail, details about staff and stored files that were never read into this record — the complete list is in the file itself. Whether these parts belong to a complete response to an access request is still to be settled legally.",
      create: "Create data export",
      done: "File created and downloaded.",
      none: "No data export has been created for this record yet.",
      history: "Created so far (from the audit trail)",
      values: { one: "{n} value", other: "{n} values" },
      files: { one: "{n} original file", other: "{n} original files" },
      filesChanged: " ({n} no longer unchanged in storage)",
      filesNeverRead: " ({n} never read, not included)",
      versions: { one: "{n} report version", other: "{n} report versions" },
      confirmTitle: "Create data export?",
      confirmNote:
        "The file holds personal health data of this person and is downloaded to this device. Keep it protected and hand it only to the person concerned. Creating it is attributed to you and audited; the platform keeps no copy of the file.",
      confirm: "Create and download",
      creating: "Creating …",
      errors: {
        patient_erased:
          "This record has been deleted; there is nothing to export.",
        export_too_large:
          "The stored original files are too large for a single file.",
        storage_unavailable:
          "A stored original file could not be read just now. No file was created — please try again later.",
        cross_origin: "The request was refused. Please reload the page.",
        tooMany:
          "Too many data exports in a short time. Please try again later.",
        failed: "The data export could not be created. Please try again.",
      },
    },
  },
  reviewQueue: {
    title: "Review queue",
    lead: "Open review tasks from the import — no value is published without a human decision. Shown is the source representation (original name, value, unit).",
    readOnly:
      " The decision is reserved for the clinical role (read-only view).",
    empty: "No open review tasks.",
    tableAria: "Open review tasks",
    columns: {
      patient: "Patient",
      value: "Value (source)",
      reason: "Reason",
      observed: "Observed",
      decision: "Decision",
    },
    publish: "Publish",
    reject: "Reject",
    cancel: "Cancel",
    clinicalRoleRequired: "Clinical role required",
    reference: {
      upper: "upper limit {high}",
      lower: "lower limit {low}",
      line: "Source reference: {bounds}",
      lineConverted: "Source reference (converted): {bounds}",
    },
    heldStatus: {
      published: "published",
      pending: "in review",
      rejected: "rejected",
      superseded: "replaced",
    },
    replacesOnPublish: "Replaced on publication: {held}",
    citedIn: {
      one: " — cited in {n} report",
      other: " — cited in {n} reports",
    },
    alreadyHeld: "Already present: {held}",
    dialog: {
      publishTitle: "Publish the value?",
      rejectTitle: "Reject the value?",
      publishBody:
        "The value is published and appears in the clinical timeline. If another open review task remains for this value, it stays held until that task is decided.",
      rejectBody:
        "The value is rejected and never published. The decision is attributed to you and audited.",
      replacesPublish:
        "On publication this value replaces the earlier value {held}. The earlier value is kept unchanged and marked as replaced.",
      replacesReject: "The earlier value {held} remains.",
      citedInReports: {
        one: " It is cited in {n} report: that report can only be approved or released with a new draft; a report already released stays visible to the patient until a new draft is created on the report page.",
        other:
          " It is cited in {n} reports: these can only be approved or released with a new draft; a report already released stays visible to the patient until a new draft is created on the report page.",
      },
    },
    errors: {
      invalidReference: "Invalid reference.",
      invalidPath: "Invalid path.",
      forbidden: "Your role does not allow this action.",
      supersessionConflict:
        "The value this correction is meant to replace has already been replaced by another correction. This value can only be rejected.",
      conflict:
        "Already decided or no longer open — the view is being refreshed.",
      failed: "The action failed. Please try again.",
    },
  },
  interpretation: {
    crumb: "Record interpretation · {patient}",
    titleNew: "Record interpretation",
    titleCorrection: "Record interpretation · correction after run {run}",
    lead: "Six domain axes · CIS and Actionability as two separate, closed entries per axis · three verdict-free tri-state cells as evidence context. The system validates and records your entries; it derives nothing. An interpretation is recorded as a whole; a correction is kept as a new run, nothing is overwritten.",
    reason: "Reason (required)",
    reasonPlaceholderNew: "e.g. baseline interpretation",
    reasonPlaceholderCorrection: "e.g. correction after new laboratory values",
    cis: "CIS",
    actionability: "Actionability",
    followup: "Follow-up adequacy",
    rationale: "Rationale (optional)",
    choose: "Please choose",
    verdictFree: "(verdict-free)",
    state: "State",
    endpoint: "Endpoint adequacy",
    evidence: "Evidence ({n} chosen)",
    evidenceRequired: " — required",
    noEvidence: "No published observations available.",
    cancel: "Cancel",
    submit: "Record interpretation",
    submitting: "Recording …",
    invalid: {
      reason: "Please give a reason.",
      domain: "{axis}: CIS, Actionability and follow-up adequacy are required.",
      cell: "{axis} / {cell}: state and endpoint adequacy are required.",
      evidence:
        "{axis} / {cell}: a determinate cell needs at least one piece of evidence.",
    },
    errors: {
      invalidPatient: "Invalid patient reference.",
      invalidPath: "Invalid path.",
      forbidden: "Your role does not allow this action.",
      vocabulary: "Entries incomplete or outside the closed vocabularies.",
      evidenceReplaced:
        "A chosen piece of evidence has since been corrected by the laboratory. Please reload the page and choose the evidence again.",
      evidenceUnresolved:
        "Evidence cannot be resolved: every piece of evidence must be a published observation of this patient.",
      shape: "Run structure incomplete (6 domains × 3 cells).",
      failed: "Recording failed. Please try again.",
    },
  },
  reportPage: {
    crumb: "Report",
    lead: "Every statement remains traceable to the observations it rests on.",
    stage: {
      title: {
        report: "Source-grounded report",
        draft: "Source-grounded draft",
        rejected: "Rejected version",
      },
      badge: {
        draft: "Not released",
        approved: "Approved",
        released: "Released",
        rejected: "Rejected",
      },
      headline: {
        draftSystem: "System draft – not released.",
        draftEdited: "Reworked draft – not released.",
        approved: "Clinically approved – not released yet.",
        released: "Released by a physician.",
        rejected: "Rejected – not released.",
      },
      detail: {
        draft:
          "Statements must be checked against their sources and signed by the clinical team.",
        approved:
          "Release to the patient is reserved for the medical director.",
        released:
          "Only this version can be viewed by the patient – as long as their access link is valid and their consent stands.",
        rejected: "A rework creates a new version; this version is kept.",
        citesReplaced:
          "A cited value has been corrected by the laboratory – see the note below.",
      },
    },
    kicker: {
      edited: "Clinically reworked version",
      deterministic: "Deterministic summary",
    },
    noStatements: "This report has no statements.",
    rejected: {
      title: "Rejected.",
      reason: "Reason:",
      noReason: "No reason was recorded for this rejection.",
      reworked: "Rework after a rejection. Reason given then:",
    },
    citesReplaced: {
      note: "A cited value has been corrected by the laboratory. This version cannot be approved or released.",
      released:
        " The patient's access to this version is withdrawn only when a new draft is created.",
      clinician: " Create a new draft from the current values.",
      otherRole: " A new draft is reserved for the clinical role.",
    },
    statement: {
      label: "Statement {n}",
      removing: " · will be removed",
      remove: "Remove statement",
      restore: "Restore statement",
    },
    chip: {
      unresolved: "Evidence cannot be resolved",
      observation: "Observation",
      corrected: " · corrected by the laboratory",
    },
    rework: {
      note: "The evidence stays bound to its statement. Saving creates version v{next} as a draft; the rejected version v{version} is kept. The new version has to be approved and released again.",
      save: "Save as a new version",
    },
    domains: {
      title: "Domain interpretation",
      note: "Six domain axes · an Actionability verdict per axis. No score.",
      run: "Run {n}",
      noRun: "There is no interpretation run for this patient yet.",
      reviewed: "✓ reviewed",
      draft: "Draft",
      adequacy: "Follow-up adequacy:",
      citesReplaced:
        "Relies on a value the laboratory has corrected — check the interpretation.",
      shown: "✓ Biomarkers in the observation evidence",
      show: "View biomarkers ({n})",
    },
    evidence: {
      title: "Observation evidence",
      noteAll:
        "Measured values, units, reference intervals and provenance — with the position relative to the reference interval.",
      noteDomain: "The domain's own observations:",
      showAll: "Show all",
      filtersAria: "Filter by position relative to the reference interval",
      filters: {
        all: "All",
        outside: "Outside reference",
        no_ref: "Without reference",
      },
      caption: "Measured observations of this assessment",
      columns: {
        marker: "Marker",
        primaryDomain: "Primary domain",
        current: "Current",
        position: "Position vs. reference interval",
        change: "Change",
        reference: "Reference",
        codeStatus: "Code / status",
      },
      empty: {
        outside: "No markers outside the reference interval.",
        no_ref: "No markers without a reference on file.",
        domain: "No observations for this domain.",
        all: "No observations available.",
      },
      notPublished: "no position: the value is not published",
      referenceInterval: "reference interval",
      noInterval: "no reference interval on file",
      reference: "Reference {range}",
      noScale: "no scale",
    },
    secondary: {
      title: "Secondarily relevant",
      noteBefore: "Also relevant to",
      noteAfter:
        ". Shown for an overview – each value is kept and assessed in its primary domain; no domain assessment is derived from this.",
      label: "Secondarily relevant observations for",
    },
    audit: {
      title: "Audit status",
      note: "Progress from data capture to release to the patient (live status).",
    },
    bar: {
      status: "Report v{version} · Status: {status}",
      hint: {
        releasedReplaced:
          "Released — a cited value has been corrected by the laboratory; the patient's access is withdrawn only when a new draft is created.",
        replaced:
          "A cited value has been corrected by the laboratory — this version cannot be approved or released.",
        released:
          "Released — Only this version can be viewed by the patient – as long as their access link is valid and their consent stands.",
        rejectedClinician:
          "Rejected — “Rework” creates a new version; the rejected one is kept.",
        rejected: "Rejected — a rework creates a new version.",
        approvedDirector:
          "Ready for release to the patient — bound to consent, attributed and audited.",
        approved: "Approved — waiting for release by a physician.",
        draftClinician:
          "The approval is written on the server, attributed to you and audited.",
        draftDirector: "Waiting for the clinical approval.",
        readOnly: "Read-only view for your role.",
      },
      rework: "Rework",
      redraft: "Create a new draft",
      reject: "Reject",
      approve: "Approve report",
      release: "Release to patient",
    },
    dialog: {
      close: "Close dialog",
      title: {
        approve: "Approve the report?",
        reject: "Reject the report?",
        redraft: "Create a new draft?",
        release: "Release to the patient?",
        released: "Released — access link",
      },
      body: {
        approve:
          "You confirm that you have checked the visible observations, reference intervals and sources. The approval is written on the server, attributed to you and audited.",
        reject:
          "The current version is recorded as rejected (attributed and audited), together with the reason you choose. Whoever reworks the report sees this reason; a rework creates a new version.",
        redraft:
          "A new draft version is created from the values that currently stand. The previous version stays stored but is no longer shown here; wording that was reworked by hand is not carried over.",
        redraftReleased:
          "This withdraws the patient's access to the released report until the new version is approved and released again.",
        redraftOther: "The new version has to be approved and released.",
        release:
          "The release is bound to consent (report_release), attributed to you and audited. The patient sees only the released version.",
        released:
          "The report is released. Synthetic demo: pass the link on by hand and safely — nothing is sent automatically.",
      },
      reason: "Reason for the rejection",
      confirm:
        "I have checked the open notes and confirm the clinical documentation.",
      link: "Access link (shown once)",
      copyLink: "Copy link",
      done: "Close",
      cancel: "Cancel",
      submit: {
        approve: "Approve",
        reject: "Reject",
        redraft: "Create a new draft",
        release: "Release",
      },
    },
    toast: {
      saved: "Rework saved as a new version.",
      approved: "Report approved.",
      redrafted: "New draft created from the current values.",
      rejected: "Report rejected.",
      copied: "Link copied.",
    },
    errors: {
      invalidReport: "Invalid report reference.",
      invalidPatient: "Invalid patient reference.",
      invalidPath: "Invalid path.",
      forbidden: "Your role does not allow this action.",
      tooMany:
        "Too many requests in a short time. Please wait a moment and try again.",
      noConsent:
        "There is no active consent (report_release) on file for this patient.",
      notApproved: "The report has not been approved yet.",
      alreadyRejected: "The report has already been rejected.",
      citesReplaced:
        "Not possible: a cited value has been corrected by the laboratory. Please create a new draft from the current values.",
      evidenceHidden:
        "Approval not possible: not every piece of evidence can be viewed.",
      wrongStatus:
        "This action is not possible in the report's current status.",
      failed: "The action failed. Please try again.",
      noPublished: "No draft possible: there are no published observations.",
      unsupported:
        "No draft possible: not every statement could be backed by a source.",
      statementShape:
        "Every statement needs a text and at least one piece of evidence.",
      restricted:
        "Not saved: the text contains terms that are not permitted in reports ({terms}).",
      editReplaced:
        "Not saved: a cited value has been corrected by the laboratory. Please remove the statement concerned or create a new draft.",
      editEvidence:
        "Not saved: not every piece of evidence can be viewed. Please remove the statement concerned.",
      chooseReason: "Please choose a reason.",
    },
  },
  membersPage: {
    ownersOnly: "Member management is available to owners only.",
    eyebrow: "Settings · Clinic",
    lead: "Who works in this clinic and what their role allows. People invited set up their own access through a single-use link; you set the role.",
    team: "Members",
    you: " · you",
    roleOf: "Role of {name}",
    roleCount: "{role} {n}",
    columns: {
      person: "Person",
      role: "Role",
      lastActive: "Last active",
      actions: "Actions",
    },
    never: "never",
    more: "More actions for {name}",
    showInTrail: "Show in the audit trail",
    remove: "Remove from the team …",
    removeConfirm:
      "Remove {name} from the team? They lose access to this clinic at once. This is recorded.",
    roleConfirm:
      "Change the role of {name} from {from} to {to}? This is recorded.",
    note: "Changing a role or removing a member is recorded and asks first. Owner and medical director are separate roles: whoever releases does not administer, and the other way round.",
    invite: {
      open: "Invite a colleague",
      title: "Invite a colleague",
      note: "The link is shown exactly once and expires after 7 days. You set the role here; the person invited cannot change it.",
      label: "Who it is for (optional)",
      labelHelp:
        "For example the e-mail address. Only a label in your list; the link is not sent anywhere.",
      role: "Role",
      cancel: "Cancel",
      create: "Create invitation link",
      createdBefore: "Invitation for",
      createdAfter: "created. Pass this link on to the person invited — it is",
      once: "shown only once",
      link: "Single-use invitation link",
      done: "Done",
    },
    pending: {
      title: "Open invitations",
      none: "No open invitations.",
      created: "Link created on {day} by {name}",
      createdNoName: "Link created on {day}",
      expires: "Expires on {day} · not yet redeemed",
      revoke: "Revoke",
      revokeOf: "Revoke the invitation {what}",
      revokeConfirm: "Revoke the invitation? The link stops working.",
    },
    matrix: {
      title: "What a role may do",
      note: "From the platform's authorization matrix; every action is checked on the server as well.",
      caption: "What each role may do",
      capability: "May",
      yes: "yes",
      no: "no",
      unavailable: "The authorization matrix is not available at present.",
      capabilities: {
        readRecords:
          "Read records, values, their own actions and the clinic profile",
        createRecords: "Create records, document consent, invite patients",
        importValues: "Upload and read in laboratory values",
        draftReports: "Draft and rework reports",
        decideValues: "Decide values in the review queue",
        interpret: "Record the interpretation",
        approve: "Approve reports",
        redraft: "Open a new draft after a laboratory correction",
        reject: "Reject reports",
        release: "Release reports",
        team: "Manage the team and invite colleagues",
        clinicProfile: "Change the clinic profile",
        auditTrail: "Read the clinic's audit trail",
        metric: "Record and view the preparation time",
        export: "Create a data export",
        requestDeletion: "Request the deletion of a record",
        listDeletion: "View deletion requests",
        decideDeletion: "Decide deletion requests",
        executeDeletion: "Carry out approved deletions",
      },
    },
    errors: {
      invalidRole: "Invalid role.",
      invalidInvitation: "Invalid invitation.",
      invalidInput: "Invalid input.",
      forbidden: "Your role does not allow this action.",
      ownMembership: "You cannot change your own membership.",
      lastOwner: "The clinic needs at least one owner.",
      notPending: "This invitation is no longer pending.",
      tooMany: "Too many requests. Please try again later.",
      failed: "The action could not be carried out. Please try again.",
    },
  },
  deletionRequestsPage: {
    reserved:
      "Managing deletion requests is reserved for owners and the medical director.",
    lead: "Requests to delete patient data. A request is made by the owner and reviewed by the medical director (two-person approval). The actual, irreversible deletion anonymises the record and is carried out separately.",
    none: "No deletion requests.",
    erased: "Deleted record",
    requested: "requested {day}",
    status: {
      pending: "Open",
      approved: "Approved",
      rejected: "Rejected",
      cancelled: "Withdrawn",
      executed: "Carried out",
    },
    execute: "Delete permanently",
    executeConfirm:
      "Delete the data of “{name}” now, permanently and irreversibly? The record is anonymised; derived data, documents and reports are deleted. This cannot be undone.",
    executionPending: "Execution pending",
    approve: "Approve",
    approveConfirm:
      "Approve the deletion for “{name}”? It is carried out separately and cannot be undone.",
    reject: "Reject",
    cancel: "Withdraw",
    errors: {
      failedShort: "The action failed.",
      invalid: "Invalid request.",
      forbidden: "Your role does not allow this action.",
      notFound: "The request was not found.",
      notOpen: "The request is no longer open.",
      requesterOnly: "Only the person who made the request can withdraw it.",
      wrongStatus: "The request cannot be handled in this status.",
      failed: "The action could not be carried out. Please try again.",
    },
  },
  auditPage: {
    ownersOnly: "The audit trail is available to owners only.",
    tooMany:
      "The trail was requested very often in a short time. Please try again in a minute.",
    unavailable:
      "The trail is temporarily unavailable. Please try again later.",
    lead: "The recorded events of this clinic: who, when, which event, on which record. An entry holds identifiers, codes, counts and times – no measured values and no names of patients. Who acted is given by the name and e-mail address of the account. The application only appends entries; it changes and deletes none. Times in the time zone {zone}.",
    notShown: {
      title: "What this trail does not show",
      tenantless:
        "Events recorded without a clinic: signing in and out, failed sign-ins, throttled requests and requests refused for security reasons, and access attempts without a selected clinic or after a membership has ended. Entering the clinic is recorded.",
      notRecorded:
        "Not recorded at present: a report read by staff and the reading of the administrative lists (members, team invitations, deletion requests, history of data exports).",
      refusals:
        "Refused events are recorded only in part: role denials, refused imports and data exports, refused invitation and access links. Other refusals – such as a release without consent or a request for an unknown identifier – leave no entry.",
      linkRefusals:
        "Refused invitation and access links are recorded one by one until 30 in a minute are reached for each kind of event. An entry then records that further refusals are no longer recorded one by one until that minute is over – how many there were is not in the trail.",
      byRecord:
        "An entry is filed under the record it is recorded on. Under a patient record are creating and opening the record, reading values, interpretation, consents and the file list, the consents and withdrawals documented in the clinic, and the data export. Reports, files, imports, recorded interpretations, review items, invitations and deletion requests are filed under their own identifier and do not appear when a patient record is chosen; a consent given through an invitation is filed under the invitation.",
      lists:
        "List views (record list, overview, review queue) are recorded as a read access, without naming the individual records. Opening a record also loads the overview and leaves an entry of its own for that.",
      erased:
        "Entries about a deleted record are kept with the record's identifier.",
      sameTime:
        "Entries that arise in the same request carry the same time; their order among each other is not fixed.",
      paging:
        "When paging to older entries, an entry that was stored only while reading may be missing. Reading again from the first page shows it.",
    },
    filter: {
      category: "Area",
      allCategories: "All areas",
      from: "From",
      to: "Up to and including",
      hideReads: "Hide read accesses",
      apply: "Apply",
      reset: "Reset filters",
    },
    targetBefore: "Only entries recorded under the record",
    targetAfter: ".",
    allTargets: "Show all records",
    actorOnly: "Only the entries of {name}.",
    allActors: "Show everyone",
    readsHidden: "Read accesses are hidden.",
    showReads: "Show read accesses",
    stalePosition:
      "The requested position is not valid. The newest entries are shown.",
    entries: "Entries",
    emptyFiltered: "There are no entries for this selection.",
    empty: "No entries yet.",
    tableAria: "Audit trail, newest entries first",
    columns: {
      time: "Time",
      who: "Who",
      action: "Event",
      target: "Record",
      details: "Details",
    },
    noActor: "no signed-in person",
    onlyThisTarget: "Show only entries for this record",
    openRecord: "Open record",
    yes: "yes",
    no: "no",
    older: "Older entries",
    newest: "To the newest entries",
  },
  preparationPage: {
    ownersOnly: "Preparation time is available to owners only.",
    tooMany:
      "The page was requested very often in a short time. Please try again in a minute.",
    unavailable:
      "The metric is temporarily unavailable. Please try again later.",
    lead: "How long preparing an appointment takes. This page keeps two things apart: what the clinic states itself, and what the platform measures from the course of the reports. It holds no data of patients. Times in the time zone {zone}.",
    saved: "The figure was saved.",
    failures: {
      eingabe: "The figure was not saved: the input was incomplete.",
      minuten:
        "The figure was not saved: the median is a whole number from 1 to 600 minutes.",
      stichprobe:
        "The figure was not saved: a timed sample needs the number of appointments timed (1 to 100000).",
      schaetzung:
        "The figure was not saved: an estimate has no number of timed appointments. Please leave the field empty or choose “Timed sample”.",
      rolle: "The figure was not saved: only owners may do this.",
      zuviele:
        "The figure was not saved: too many figures in a short time. Please wait a minute.",
      allgemein:
        "Whether the figure was saved could not be confirmed. Please check the history before entering it again.",
    },
    kind: { baseline: "Baseline", follow_up: "Follow-up figure" },
    basis: { estimate: "Estimate", timed_sample: "Timed sample" },
    timedOver: {
      one: "Timed sample over {n} appointment",
      other: "Timed sample over {n} appointments",
    },
    minutes: "{n} min",
    elapsed: {
      underOne: "under 1 min",
      minutes: "{m} min",
      hours: "{h} h",
      hoursMinutes: "{h} h {m} min",
      days: { one: "{n} day", other: "{n} days" },
      daysHours: { one: "{n} day {h} h", other: "{n} days {h} h" },
    },
    stated: {
      title: "Stated by the clinic",
      note: "The median preparation time per appointment, in minutes, as the clinic states it: the baseline before the platform was used, and later follow-up figures. The platform takes these figures over and does not check them.",
      latestFollowUp: "Latest follow-up figure",
      noBaseline: "No baseline recorded yet.",
      noFollowUp: "No follow-up figure recorded yet.",
      perAppointment: "Median per appointment · {basis}",
      recordedAt: "recorded on",
      recordedBy: " by {name}",
      same: "The latest follow-up figure equals the baseline.",
      below: "The latest follow-up figure is {n} min below the baseline.",
      above: "The latest follow-up figure is {n} min above the baseline.",
      bothStated: "Both figures are stated by the clinic",
      differentBasis: " – on different bases ({first} and {second}).",
    },
    form: {
      kind: "Kind of figure",
      median: "Median per appointment (minutes)",
      basis: "Basis",
      sample: "Number of appointments timed (timed sample only)",
      save: "Save figure",
      note: "A saved figure is not changed or deleted. A correction is a new figure; the earlier one stays in the history.",
    },
    history: {
      shown: "The history shows the newest {shown} of {total} figures.",
      caption: "History of the clinic's figures, newest first",
      columns: {
        recordedAt: "Recorded on",
        kind: "Kind",
        median: "Median per appointment",
        basis: "Basis",
        recordedBy: "Recorded by",
      },
    },
    measured: {
      title: "Measured from the course of the reports",
      note: "The time from a report's first draft to its first clinical approval that stood – from the times the platform records along the way anyway. This is turnaround time, not working time, and not yet the preparation time itself.",
      last30: "Last 30 days",
      allTime: "All of the clinic's approved reports",
      median:
        "Median from the first draft to the first approval that stood · {n} reports",
      middleHalf: "Middle half of the reports: {q1} to {q3}",
      none: "No approved report in this period yet.",
      tooFew:
        "Approved reports in this period: {n}. A median is given from {minimum} reports on.",
    },
    limits: {
      title: "What these figures are – and what they are not",
      waiting:
        "The measured time includes every wait between draft and approval – nights and weekends too. What happens before the draft (looking through values, deciding review items, recording the interpretation) is not included.",
      notOffset:
        "It is therefore not set off against the clinic's stated minutes: they are two different quantities. A measurement that can be compared with the baseline does not exist yet – the platform does not yet record when preparation begins.",
      countsOnce:
        "A report counts once: with its first approval that was not rejected again. An approval that was refused or withdrawn at the release by a physician does not end the measurement. Reports without an approval do not count.",
      minimum:
        "Below {minimum} reports no median is given: with so few reports, any figure is close to the time of a single report. This is caution with small numbers, not protection of individual people: if only a few people in the clinic approve, the figure describes their work even with many reports.",
      computed:
        "The metric is computed from the existing reports each time the page is opened. If a record is deleted, its reports drop out here too – a figure read earlier can then no longer be recomputed.",
      audited:
        "Reading this page and every recorded figure are in the audit trail. Version of the measurement rule: {definition}.",
    },
  },
  notFound: {
    title: "Page not found",
    note: "The page you asked for does not exist or is not available.",
    back: "To the overview",
  },
  settings: {
    title: "Settings",
    eyebrow: "Administration",
    intro:
      "Personal, clinic and governance settings, kept apart. What your role may not open is locked, not hidden.",
    nav: {
      label: "Settings sections",
      groups: {
        personal: "Personal",
        clinic: "Clinic",
        governance: "Governance",
      },
      locked: "Only for {roles}",
      and: " and ",
    },
    all: {
      title: "All sections",
      note: "Each card says what it holds right now.",
    },
    appearance: {
      title: "Language & appearance",
      desc: "The interface language and the appearance on this device.",
    },
    profile: {
      title: "Profile",
      desc: "Your name and e-mail address as colleagues see them in the trail, and your clinics.",
    },
    security: {
      title: "Security & sessions",
      desc: "How you sign in, your sessions, and ending all the others.",
    },
    clinicProfile: {
      title: "Clinic profile",
      desc: "The clinic's name and address as the team and patients see them, and the laboratory's time zone.",
    },
    dataSources: {
      title: "Data sources & import",
      desc: "Which readers read laboratory files, when last, and what happens to a value after it is read in.",
    },
    consentTexts: {
      title: "Consent texts",
      desc: "The versions every consent refers to. A new wording is a new version, never an overwrite.",
    },
    retention: {
      title: "Retention & export",
      desc: "Retention periods, data export (Art. 15/20), deletion and restore.",
    },
    members: {
      title: "Team & roles",
      desc: "Manage the team, change roles and invite colleagues.",
    },
    deletionRequests: {
      title: "Deletion requests",
      desc: "Review and carry out requests to delete a patient record (two-person approval).",
    },
    auditTrail: {
      title: "Audit trail",
      desc: "View the clinic's recorded events: who, when, which event, on which record.",
    },
    preparationTime: {
      title: "Preparation time",
      desc: "Record the clinic's baseline and its later figures, and view the measured turnaround time of reports.",
    },
    state: {
      members: { one: "{n} member", other: "{n} members" },
      invitations: {
        one: "{n} open invitation",
        other: "{n} open invitations",
      },
      noInvitations: "no open invitation",
      baselineSet: "Baseline recorded",
      baselineMissing: "Baseline missing",
      median: "Median {value}",
      noMedian: "no median yet",
      deletions: { one: "{n} request open", other: "{n} requests open" },
      noDeletions: "No request open",
      denials: {
        one: "{n} denied access in 7 days",
        other: "{n} denied accesses in 7 days",
      },
      unavailable: "State not available at present",
      sessions: {
        one: "{n} active session",
        other: "{n} active sessions",
      },
      signIn: {
        dev: "Development sign-in",
        oidc: "The clinic's sign-in service",
      },
      clinicProfile: "{name} · {zone}",
      dataSources: "{readers} · wearables not connected",
      consentTexts: "Version {version} · {n} purposes",
      retention: "Retention policy not yet set",
    },
  },
  clinicPage: {
    lead: "What the clinic is called and where it is — at the top of every page and beneath the report a patient reads through their access link.",
    profile: "Details",
    name: "Name of the clinic",
    address: "Address",
    addressHelp: "Shown beneath the released report. At most 300 characters.",
    noAddress: "No address given",
    zone: "Laboratory time zone",
    zoneHelp:
      "Laboratory times without a zone of their own are read in this zone. It applies to the whole pilot and is not changed here.",
    logo: "Logo",
    logoNote: "Not possible yet: this pilot accepts no images.",
    save: "Save",
    saved: "Saved.",
    ownerOnly: "The clinic's owner can change this.",
    errors: {
      invalid: "Please give a name; the address has at most 300 characters.",
      forbidden: "Your role does not allow this action.",
      failed: "Not saved. Please try again.",
    },
    unavailable: "The clinic profile is not available at present.",
  },
  sourcesPage: {
    lead: "How values get into the records. Which source a clinic uses depends on its laboratory — a structured file is always preferable to a PDF.",
    readers: "Readers for laboratory files",
    readersNote:
      "What kind of file it is is decided by its content, never by its name.",
    what: {
      csv: "A table in the HADP layout: one row per value, with the laboratory's unit and reference interval.",
      ldt2: "Laboratory data transfer, version 2 (record 8201).",
      ldt3: "Laboratory data transfer, version 3 (record 8205), with a checksum.",
      other: "Entered by hand or sent through the interface.",
    },
    never: "Nothing read in yet",
    last: "Last {when}",
    jobs: { one: "{n} import", other: "{n} imports" },
    rows: { one: "{n} row", other: "{n} rows" },
    after: "What happens after a file is read in",
    steps: {
      stored: "The file is stored unchanged before it is read.",
      published:
        "A value whose marker, unit and number are unambiguous is published.",
      review:
        "Every other value waits in the review queue until a clinician decides — an unknown unit, an unclear marker, an impossible number, a possible duplicate or correction.",
      original:
        "The laboratory's original value, unit and reference interval are kept unchanged.",
    },
    pdf: "PDF reports are not read yet.",
    wearables: "Wearables",
    wearablesNote: "Not connected in pilot phase 1.",
    unavailable: "The sources are not available at present.",
  },
  consentTextsPage: {
    lead: "The consents the clinic documents, and the version of the text each one refers to.",
    current: "Current version",
    currentNote:
      "Every newly documented consent refers to this version. A changed wording gets a new version number; recorded consents keep theirs.",
    placeholder:
      "The wordings are placeholders of the pilot. The final texts are written by the clinic's data protection advisers; they arrive as a new version, not edited here.",
    purposes: "Purposes",
    counts: "Recorded in this clinic",
    caption: "Consents per purpose and version",
    columns: {
      purpose: "Purpose",
      version: "Version",
      granted: "Given",
      withdrawn: "Withdrawn",
    },
    none: "No consent documented yet.",
    unavailable: "The figures are not available at present.",
  },
  retentionPage: {
    lead: "How long the clinic keeps data, how a patient receives their data, and how data is deleted.",
    policy: "Retention periods",
    policyNote:
      "No policy set yet. The clinic, as the controller, sets the periods with its data protection advisers. Until then the platform deletes nothing on its own.",
    export: "Data export (GDPR Art. 15 and 20)",
    exportNote:
      "The owner creates it on the patient's page: one file with everything the record holds. Every export is in the audit trail.",
    deletion: "Deletion (GDPR Art. 17)",
    deletionNote:
      "Two-person approval: the owner requests, the medical director decides, then it is carried out.",
    deletionState: "{open} open · {executed} carried out",
    deletionLink: "To the deletion requests",
    backup: "Backup and restore",
    backupNote:
      "Not set up in this pilot. Encrypted backups in the EU with a tested restore are a condition before real patient data.",
    unavailable: "Not available at present.",
  },
  profilePage: {
    lead: "How you appear in this clinic and in the audit trail.",
    account: "Account",
    name: "Name",
    email: "E-mail address",
    role: "Role in this clinic",
    clinic: "Clinic",
    clinics: "Your clinics",
    clinicsNote:
      "If you belong to several clinics, you choose the clinic after signing in.",
    current: "current",
    source:
      "Your name and e-mail address come from the sign-in and are not changed here: in the pilot they are synthetic accounts; with the clinic's sign-in service (OIDC) you change them there.",
  },
  securityPage: {
    lead: "How you sign in, and where you are signed in right now.",
    signIn: {
      title: "Sign-in",
      method: "Method",
      mfa: "Second factor",
      dev: "Development sign-in: no password and no second factor. It exists only in the pilot with synthetic data; in operation it is switched off.",
      oidc: "Your clinic's sign-in service (OIDC).",
      mfaDev: "Not available with the development sign-in.",
      mfaOidc:
        "Set up and asked for by your clinic's sign-in service; this platform does not see it.",
    },
    sessions: {
      title: "Your sessions",
      note: "The latest ten. Kept are the start, the expiry and the clinic last chosen — no device and no address.",
      caption: "Your sessions, newest first",
      columns: {
        started: "Started",
        state: "State",
        until: "Until",
        clinic: "Clinic",
      },
      states: {
        active: "active",
        ended: "ended",
        expired: "expired",
      },
      current: "this session",
      endOthers: "End all other sessions",
      endConfirm:
        "End all other sessions? Whoever is signed in there has to sign in again. This session stays.",
      ended: {
        one: "{n} session ended.",
        other: "{n} sessions ended.",
      },
      none: "No other session is active.",
      failed: "The sessions could not be ended. Please try again.",
      unavailable: "The sessions are not available at present.",
    },
  },
  appearance: {
    title: "Language & appearance",
    note: "Applies to you on this device. Clinical labels, laboratory details and names stay in the language they were recorded in.",
    language: {
      label: "Interface language",
      help: "German is the default language of the pilot.",
    },
    theme: {
      label: "Appearance",
      help: "Light, dark, or as this device's system is set.",
      light: "Light",
      dark: "Dark",
      system: "System",
    },
    formats: {
      label: "Numbers and dates",
      help: "The notation follows the language; dates and times are on the clinic's clock.",
    },
    progress: {
      label: "State of the translation",
      summary: "What is available in English",
    },
  },
  language: {
    title: "Language",
    note: "The language of the interface on this device. Content such as reports, laboratory terms and names stays in the language it was recorded in.",
    progress:
      "All of the clinic team's pages are available in English. The pages for patients, the invitation pages and the error page are shown in German for now. The wording of the consent purposes, the clinical labels (domains, CIS, Actionability, follow-up and endpoint adequacy, the tri-state axes and their states, position relative to the reference interval, comparability), the reasons of the review tasks and the reasons for a rejection stay German.",
    selected: "selected",
    choose: "Interface language",
  },
};
