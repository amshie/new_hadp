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
  },
  roles: {
    owner: "Owner",
    clinician: "Clinician",
    assistant: "Assistant",
    medical_director: "Medical director",
  },
  meta: {
    description:
      "Clinical, source-bound workspace — human review before every release.",
  },
  login: {
    homeAria: "HADP home",
    kicker: "Clinical workspace",
    title: "Understand health data. Document decisions traceably.",
    lead: "A calm, source-bound workspace for longevity and preventive-care clinics – with human review before every release.",
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
      desc: "Review and carry out requests to delete a patient record (four-eyes principle).",
    },
    auditTrail: {
      title: "Audit trail",
      desc: "View the clinic's recorded events: who, when, which event, on which record.",
    },
    preparationTime: {
      title: "Preparation time",
      desc: "Record the clinic's baseline and follow-up statements, and view the measured turnaround time of reports.",
    },
  },
  language: {
    title: "Language",
    note: "The language of the interface on this device. Content such as reports, laboratory values and names stays in the language it was recorded in.",
    progress:
      "English is being added page by page: navigation, sign-in and settings are done; the other pages are shown in German for now.",
    selected: "selected",
    choose: "Interface language",
  },
};
