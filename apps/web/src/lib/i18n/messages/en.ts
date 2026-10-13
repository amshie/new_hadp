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
    waiting: { one: "{n} review", other: "{n} reviews" },
    waitingRest: {
      one: "is waiting for your review. Source-grounded drafts must be reviewed before every release. Synthetic sample data.",
      other:
        "are waiting for your review. Source-grounded drafts must be reviewed before every release. Synthetic sample data.",
    },
    kpis: {
      openReviews: { label: "Open reviews", help: "Clinical review pending" },
      approved: {
        label: "Approved",
        help: "Waiting for release by a physician",
      },
      released: { label: "Released", help: "Released to the patient" },
      patients: {
        label: "Patients",
        help: "Scoped to the clinic · protected by row-level security",
      },
    },
    worklist: {
      title: "Clinical work list",
      note: "By report status · not a diagnosis or treatment advice.",
      tabs: {
        open: "Open reviews",
        approved: "Approved",
        released: "Released",
        all: "All",
      },
      search: "Search patient or ID",
      columns: {
        patient: "Patient",
        assessment: "Assessment",
        status: "Status",
        updated: "Updated",
      },
      openRow: "Open patient {name}, {ref}",
      emptyTitle: "No matching items",
      emptyNote: "Change the filter or the search term.",
    },
    snapshot: {
      title: "Report status",
      note: {
        one: "Current state · snapshot · {n} patient",
        other: "Current state · snapshot · {n} patients",
      },
    },
    coverage: {
      title: "Data coverage",
      note: {
        one: "Coverage across {n} real observation · not a quality rating",
        other: "Coverage across {n} real observations · not a quality rating",
      },
      ring: "PUBLISHED",
      published: "Published",
      withReference: "With reference interval",
      latest: "Latest observation",
    },
    gated: {
      throughput: {
        title: "Review throughput",
        reason:
          "The throughput series cannot be loaded at present. A backend slice of its own (report_versions by status).",
      },
      coverage: {
        title: "Data coverage",
        reason:
          "Coverage across the observations cannot be loaded at present. The patient page shows the real coverage per patient.",
      },
      activity: {
        title: "Recent activity",
        reason:
          "An activity feed needs a clinic-scoped read endpoint over the append-only events. A backend slice of its own.",
      },
      imports: {
        title: "Imports & sources",
        reason:
          "Import status needs a read endpoint over import_jobs. A backend slice of its own.",
      },
    },
    throughput: {
      title: "Review throughput",
      note: "Drafts created vs. reviews signed · real timestamps",
      days14: "14 d",
      days30: "30 d",
      signed: "Signed",
      created: "Created",
      totalSigned: "Signed in total",
      totalCreated: "Created in total",
      avgSigned: "Avg. signed / day",
      showTable: "Show data table",
      day: "Day",
      summary:
        "Review throughput over {days} days: {signed} signed, {created} created, an average of {avg} signed per day.",
    },
  },
  patients: {
    kicker: "Clinic · {clinic}",
    title: "Patients",
    count: { one: "{n} patient", other: "{n} patients" },
    lead: "· scoped to the clinic, protected by row-level security · pseudonymised, synthetic sample data.",
    chips: {
      total: {
        label: "Total",
        help: "In the clinic · protected by row-level security",
      },
      withReport: { label: "With a report", help: "At least one report draft" },
      open: { label: "Open assessments", help: "Clinical review pending" },
      quality: {
        label: "Avg. data quality",
        help: "No data-quality model (Gate G1)",
      },
    },
    notAvailable: "n/a",
    gatedTitle: "No approved real-data indicator (ADR-0006)",
    directory: {
      title: "Patient directory",
      note: "Pseudonymised · not a diagnosis or treatment advice. The risk and data-quality columns are switched off in the real-data view (no approved source or model value — ADR-0006).",
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
      risk: "Risk",
      quality: "Data quality",
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
    domains: {
      noRun:
        "No interpretation run yet — the six domain axes are shown as a draft.",
      select: "Select domain {axis}",
      reviewed: "Reviewed",
      draft: "Draft",
      none: "No run",
      adequacy: "Follow-up adequacy:",
      citesReplaced:
        "Relies on a value the laboratory has corrected — check the interpretation.",
      shown: "Biomarkers in the observation evidence",
      show: "View biomarkers ({n})",
      notInterpreted: "Not interpreted yet",
    },
    evidence: {
      title: "Observation evidence",
      note: "Source-grounded observations · position relative to the source reference interval · not a diagnosis or treatment advice.",
      columns: {
        marker: "Marker",
        category: "Category",
        value: "Value",
        change: "Δ",
        position: "Position vs. reference",
        bar: "Reference position",
      },
      open: "Open marker {name}",
      superseded: "replaced by a laboratory correction",
      inputReplaced: "input value replaced by a laboratory correction",
      empty: "No observations in this domain.",
      noScale: "no scale",
      reference: "Ref {range}",
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
    titleCorrection: "Record correction run (after run #{run})",
    lead: "Six domain axes · CIS and Actionability as two separate, closed entries per axis · three verdict-free tri-state cells as evidence context. The system validates and records your entries; it derives nothing. A run is recorded as a whole; corrections create a new run (append-only).",
    reason: "Reason for the run (required)",
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
    submit: "Record run (append-only)",
    submitting: "Recording …",
    invalid: {
      reason: "Please give a reason for the run.",
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
      run: "Run #{n}",
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
    lead: "Invite a colleague to your clinic team. The person invited sets up their own access through a single-use link. You set the role here.",
    team: "Team",
    you: " · you",
    roleOf: "Role of {name}",
    remove: "Remove",
    removeConfirm: "Remove {name} from the team?",
    invite: {
      title: "Invite a colleague",
      role: "Role",
      create: "Create invitation",
      createdBefore: "Invitation for",
      createdAfter: "created. Pass this link on to the person invited — it is",
      once: "shown only once",
      link: "Single-use invitation link",
    },
    pending: {
      title: "Pending invitations",
      none: "No pending invitations.",
      validUntil: "valid until {day}",
      revoke: "Revoke",
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
    intro:
      "Administration of the clinic. The sections available depend on your role.",
    noSections: "No further sections are available for your role.",
    members: {
      title: "Members",
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
