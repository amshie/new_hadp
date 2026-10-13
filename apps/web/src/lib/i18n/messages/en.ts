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
      "English is being added page by page: the navigation, sign-in, the overview, the patients list and this settings overview are done; all other pages are shown in German for now. The wording of the consent purposes stays German.",
    selected: "selected",
    choose: "Interface language",
  },
};
