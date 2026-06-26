// SYNTHETIC demo data for the VitaBahn dashboard (ADR-0005).
//
// Ported verbatim from the Claude Design comp's in-component dataset. This is
// SYNTHETIC, illustrative data for the governance/clinician-review demo — no real
// patient data, no identifiers. It feeds the new /overview, /patients and
// /patients/[id] screens only; it is never written to the interpretation model,
// a report, or a patient release.
//
// NOTE (ADR-0005): the per-domain A–E "grade" from the comp was removed by founder
// direction and is intentionally absent here. The data-quality percentages (`q`),
// the patient `risk` indicator, and the observation `stat` (normal/borderline/
// abnormal) are the three founder-approved surfaces recorded in the ADR + register.

export type AttnLevel = "hoch" | "mittel" | "niedrig";
export type WorkStatus = "pruefung" | "entwurf" | "genehmigt" | "freigegeben";
export type PatientStatus = "aktiv" | "onboarding" | "pausiert" | "archiviert";
export type ObsStat = "normal" | "borderline" | "abnormal";
export type Trend = "up" | "down" | "flat";

export interface WorkRow {
  id: string;
  name: string;
  assess: string;
  attn: AttnLevel;
  q: number;
  status: WorkStatus;
  upd: string;
}

export interface PatientRow {
  id: string;
  name: string;
  age: string;
  sex: string;
  program: string;
  risk: AttnLevel;
  q: number;
  last: string;
  when: string;
  status: PatientStatus;
}

export interface Observation {
  marker: string;
  value: string;
  cat: string;
  ref: string;
  stat: ObsStat;
  trend: Trend;
}

export interface Domain {
  key: string;
  name: string;
  followUp: string;
  count: number;
}

export interface BadgeMeta {
  label: string;
  fg: string;
  bg: string;
  bd: string;
}
export interface AttnMeta {
  label: string;
  c: string;
}

// Review throughput — drafts created vs. reviews signed, last 30 days.
export const SIG30 = [
  4, 6, 5, 7, 5, 8, 6, 5, 7, 9, 6, 8, 7, 5, 8, 6, 9, 7, 6, 8, 10, 7, 9, 6, 8, 7,
  9, 8, 7, 9,
];
export const ERS30 = [
  6, 7, 7, 9, 6, 9, 8, 7, 8, 11, 8, 9, 9, 7, 10, 8, 11, 9, 8, 10, 11, 9, 10, 8,
  10, 9, 11, 10, 9, 11,
];

export const WORK_ROWS: WorkRow[] = [
  {
    id: "MLX-0428",
    name: "K. Brandt",
    assess: "Kardiometabolisches Risiko",
    attn: "hoch",
    q: 88,
    status: "pruefung",
    upd: "vor 12 Min.",
  },
  {
    id: "MLX-0506",
    name: "A. Reuter",
    assess: "Glukoseregulation · CGM",
    attn: "hoch",
    q: 71,
    status: "pruefung",
    upd: "vor 2 Std.",
  },
  {
    id: "MLX-0188",
    name: "J. Lindqvist",
    assess: "Entzündungsmarker · hsCRP",
    attn: "hoch",
    q: 64,
    status: "pruefung",
    upd: "gestern",
  },
  {
    id: "MLX-0391",
    name: "T. Sørensen",
    assess: "VO₂max-Verlauf",
    attn: "mittel",
    q: 95,
    status: "entwurf",
    upd: "vor 1 Std.",
  },
  {
    id: "MLX-0463",
    name: "L. Vásquez",
    assess: "Lipid-Panel · Trend",
    attn: "mittel",
    q: 90,
    status: "entwurf",
    upd: "vor 5 Std.",
  },
  {
    id: "MLX-0277",
    name: "M. Okafor",
    assess: "Schlaf- & HRV-Profil",
    attn: "niedrig",
    q: 97,
    status: "genehmigt",
    upd: "vor 3 Std.",
  },
  {
    id: "MLX-0334",
    name: "S. Petrova",
    assess: "Kognitives Screening",
    attn: "mittel",
    q: 93,
    status: "genehmigt",
    upd: "vor 2 T.",
  },
  {
    id: "MLX-0521",
    name: "R. Haddad",
    assess: "Knochendichte · DXA",
    attn: "niedrig",
    q: 99,
    status: "freigegeben",
    upd: "gestern",
  },
];

export const STATUS_META: Record<WorkStatus, BadgeMeta> = {
  pruefung: {
    label: "In Prüfung",
    fg: "var(--amber-500)",
    bg: "rgba(201,136,28,0.12)",
    bd: "rgba(201,136,28,0.30)",
  },
  entwurf: {
    label: "Entwurf",
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
  },
  genehmigt: {
    // Brand tokens (not raw --teal-NN scale) so the pill adapts in dark mode
    // like the other status badges (the raw scale is not remapped for dark).
    label: "Genehmigt",
    fg: "var(--brand)",
    bg: "var(--brand-soft)",
    bd: "var(--brand-border)",
  },
  freigegeben: {
    label: "Freigegeben",
    fg: "var(--vital-500)",
    bg: "rgba(20,169,130,0.12)",
    bd: "rgba(20,169,130,0.32)",
  },
};

export const ATTN_META: Record<AttnLevel, AttnMeta> = {
  hoch: { label: "Hoch", c: "var(--rose-500)" },
  mittel: { label: "Mittel", c: "var(--amber-500)" },
  niedrig: { label: "Niedrig", c: "var(--slate-400)" },
};

export const PATIENTS: PatientRow[] = [
  {
    id: "MLX-0428",
    name: "K. Brandt",
    age: "58",
    sex: "w",
    program: "Kardiometabolik",
    risk: "hoch",
    q: 88,
    last: "Kardiometab. Risiko",
    when: "vor 12 Min.",
    status: "aktiv",
  },
  {
    id: "MLX-0391",
    name: "T. Sørensen",
    age: "44",
    sex: "m",
    program: "Performance",
    risk: "mittel",
    q: 95,
    last: "VO₂max-Verlauf",
    when: "vor 1 Std.",
    status: "aktiv",
  },
  {
    id: "MLX-0506",
    name: "A. Reuter",
    age: "61",
    sex: "m",
    program: "Kardiometabolik",
    risk: "hoch",
    q: 71,
    last: "Glukoseregulation",
    when: "vor 2 Std.",
    status: "aktiv",
  },
  {
    id: "MLX-0277",
    name: "M. Okafor",
    age: "39",
    sex: "w",
    program: "Longevity Core",
    risk: "niedrig",
    q: 97,
    last: "Schlaf- & HRV-Profil",
    when: "vor 3 Std.",
    status: "aktiv",
  },
  {
    id: "MLX-0463",
    name: "L. Vásquez",
    age: "52",
    sex: "w",
    program: "Hormon & Stoffwechsel",
    risk: "mittel",
    q: 90,
    last: "Lipid-Panel Trend",
    when: "vor 5 Std.",
    status: "aktiv",
  },
  {
    id: "MLX-0188",
    name: "J. Lindqvist",
    age: "66",
    sex: "m",
    program: "Kardiometabolik",
    risk: "hoch",
    q: 64,
    last: "Entzündungsmarker",
    when: "gestern",
    status: "aktiv",
  },
  {
    id: "MLX-0334",
    name: "S. Petrova",
    age: "47",
    sex: "w",
    program: "Kognition",
    risk: "mittel",
    q: 93,
    last: "Kognitives Screening",
    when: "vor 2 T.",
    status: "aktiv",
  },
  {
    id: "MLX-0521",
    name: "R. Haddad",
    age: "55",
    sex: "m",
    program: "Longevity Core",
    risk: "niedrig",
    q: 99,
    last: "Knochendichte · DXA",
    when: "gestern",
    status: "aktiv",
  },
  {
    id: "MLX-0612",
    name: "N. Yamamoto",
    age: "41",
    sex: "w",
    program: "Longevity Core",
    risk: "niedrig",
    q: 86,
    last: "Onboarding-Panel",
    when: "vor 1 T.",
    status: "onboarding",
  },
  {
    id: "MLX-0609",
    name: "D. Fischer",
    age: "49",
    sex: "m",
    program: "Performance",
    risk: "mittel",
    q: 78,
    last: "Baseline-Assessment",
    when: "vor 2 T.",
    status: "onboarding",
  },
  {
    id: "MLX-0244",
    name: "C. Mbeki",
    age: "63",
    sex: "w",
    program: "Hormon & Stoffwechsel",
    risk: "mittel",
    q: 91,
    last: "Hormon-Panel",
    when: "vor 6 T.",
    status: "pausiert",
  },
  {
    id: "MLX-0102",
    name: "E. Kowalski",
    age: "70",
    sex: "m",
    program: "Kardiometabolik",
    risk: "hoch",
    q: 82,
    last: "Lipid-Panel Trend",
    when: "vor 14 T.",
    status: "archiviert",
  },
];

export const PATIENT_STATUS_META: Record<PatientStatus, BadgeMeta> = {
  aktiv: {
    label: "Aktiv",
    fg: "var(--vital-500)",
    bg: "rgba(20,169,130,0.12)",
    bd: "rgba(20,169,130,0.32)",
  },
  onboarding: {
    label: "Onboarding",
    fg: "var(--sky-400)",
    bg: "rgba(63,164,201,0.12)",
    bd: "rgba(63,164,201,0.32)",
  },
  pausiert: {
    label: "Pausiert",
    fg: "var(--amber-500)",
    bg: "rgba(201,136,28,0.12)",
    bd: "rgba(201,136,28,0.30)",
  },
  archiviert: {
    label: "Archiviert",
    fg: "var(--text-muted)",
    bg: "var(--surface-sunken)",
    bd: "var(--border-default)",
  },
};

// Cohort totals (synthetic) for the directory tab badges + pagination footer.
export const PATIENT_COHORT: Record<"alle" | PatientStatus, number> = {
  alle: 148,
  aktiv: 132,
  onboarding: 9,
  pausiert: 5,
  archiviert: 2,
};

export const DOMAINS: Domain[] = [
  { key: "metab", name: "Metabolisch", followUp: "adäquat", count: 2 },
  { key: "immun", name: "Immun / Entzündung", followUp: "inadäquat", count: 1 },
  { key: "kardio", name: "Kardiovaskulär", followUp: "adäquat", count: 2 },
  { key: "neuro", name: "Neurokognitiv", followUp: "adäquat", count: 1 },
  { key: "musku", name: "Muskuloskelettal", followUp: "inadäquat", count: 1 },
  {
    key: "regen",
    name: "Regenerationskapazität",
    followUp: "nicht bewertet",
    count: 2,
  },
];

export const OBSERVATIONS: Record<string, Observation[]> = {
  metab: [
    {
      marker: "HbA1c",
      value: "5,4 %",
      cat: "Labor",
      ref: "< 5,7",
      stat: "normal",
      trend: "flat",
    },
    {
      marker: "Nüchternglukose",
      value: "5,3 mmol/L",
      cat: "Labor",
      ref: "3,9–5,6",
      stat: "normal",
      trend: "down",
    },
  ],
  immun: [
    {
      marker: "hs-CRP",
      value: "2,8 mg/L",
      cat: "Labor",
      ref: "< 1,0",
      stat: "abnormal",
      trend: "up",
    },
    {
      marker: "Leukozyten",
      value: "6,1 ×10⁹/L",
      cat: "Labor",
      ref: "4,0–10,0",
      stat: "normal",
      trend: "flat",
    },
  ],
  kardio: [
    {
      marker: "hsCRP",
      value: "2,8 mg/L",
      cat: "Labor",
      ref: "< 1,0",
      stat: "abnormal",
      trend: "up",
    },
    {
      marker: "LDL-Cholesterin",
      value: "134 mg/dL",
      cat: "Labor",
      ref: "< 100",
      stat: "borderline",
      trend: "up",
    },
    {
      marker: "Ruhepuls",
      value: "55 bpm",
      cat: "Wearable",
      ref: "< 80",
      stat: "borderline",
      trend: "flat",
    },
    {
      marker: "HRV (RMSSD)",
      value: "34 ms",
      cat: "Wearable",
      ref: "> 50",
      stat: "borderline",
      trend: "down",
    },
    {
      marker: "Blutdruck",
      value: "126/80 mmHg",
      cat: "Lebensstil",
      ref: "< 120/80",
      stat: "borderline",
      trend: "flat",
    },
    {
      marker: "Trainingsfrequenz",
      value: "4×/Wo",
      cat: "Lebensstil",
      ref: "5×/Wo",
      stat: "borderline",
      trend: "flat",
    },
    {
      marker: "Gesamtcholesterin",
      value: "188 mg/dL",
      cat: "Labor",
      ref: "< 200",
      stat: "normal",
      trend: "flat",
    },
    {
      marker: "Triglyzeride",
      value: "92 mg/dL",
      cat: "Labor",
      ref: "< 150",
      stat: "normal",
      trend: "down",
    },
    {
      marker: "HDL-Cholesterin",
      value: "58 mg/dL",
      cat: "Labor",
      ref: "> 40",
      stat: "normal",
      trend: "up",
    },
  ],
  neuro: [
    {
      marker: "Verarbeitungsgeschwindigkeit",
      value: "105",
      cat: "Wearable",
      ref: "—",
      stat: "normal",
      trend: "up",
    },
    {
      marker: "Reaktionszeit",
      value: "240 ms",
      cat: "Wearable",
      ref: "< 300",
      stat: "normal",
      trend: "down",
    },
  ],
  musku: [
    {
      marker: "Vitamin D (25-OH)",
      value: "62 nmol/L",
      cat: "Labor",
      ref: "50–125",
      stat: "normal",
      trend: "up",
    },
    {
      marker: "Griffkraft",
      value: "41 kg",
      cat: "Wearable",
      ref: "> 38",
      stat: "normal",
      trend: "flat",
    },
  ],
  regen: [
    {
      marker: "HRV (RMSSD)",
      value: "48 ms",
      cat: "Wearable",
      ref: "> 50",
      stat: "borderline",
      trend: "up",
    },
    {
      marker: "Schlaf-Effizienz",
      value: "88 %",
      cat: "Wearable",
      ref: "≥ 85",
      stat: "normal",
      trend: "up",
    },
  ],
};

export const DOMAIN_HEALTH: Record<string, string> = {
  metab: "Metabolische Gesundheit",
  immun: "Immun & Entzündung",
  kardio: "Kardiovaskuläre Gesundheit",
  neuro: "Neurokognitive Gesundheit",
  musku: "Muskuloskelettale Gesundheit",
  regen: "Regeneration & Schlaf",
};

// Source-grounded, non-prescriptive demo summaries. These DESCRIBE the synthetic
// observations and their position relative to the source reference interval and their
// trend — they carry NO recommendation/treatment/follow-up advice (ADR-0005 keeps the
// no-recommendation boundary; the comp's original prose was neutralized here).
export const DOMAIN_DESC: Record<string, string> = {
  kardio:
    "Gesamtcholesterin, Triglyzeride und HDL liegen innerhalb des Quellreferenzintervalls und sind im Verlauf stabil. hs-CRP und LDL liegen über der Referenz; mehrere kardiometabolische Marker liegen grenzwertig nahe der oberen Referenzgrenze. Die HRV liegt unter dem Referenzwert mit rückläufigem Verlauf. Für den kardialen Belastungstest liegt keine aktuelle Messung vor.",
  metab:
    "HbA1c und Nüchternglukose liegen innerhalb des Quellreferenzintervalls und sind über die letzten Messungen stabil. Keine Werte außerhalb der Referenz erfasst.",
  immun:
    "Der hs-CRP-Wert liegt über dem Quellreferenzintervall und zeigt im Verlauf einen steigenden Trend. Die Leukozyten liegen innerhalb der Referenz und sind stabil.",
  neuro:
    "Verarbeitungsgeschwindigkeit und Reaktionszeit liegen innerhalb des erfassten Referenzbereichs; beide zeigen einen stabilen bis leicht verbesserten Verlauf.",
  musku:
    "Vitamin D (25-OH) liegt innerhalb und die Griffkraft oberhalb des Quellreferenzintervalls. Beide Werte sind im Verlauf stabil.",
  regen:
    "Die Schlaf-Effizienz liegt innerhalb des Quellreferenzintervalls. Die HRV liegt knapp unter dem Referenzwert, mit leicht steigendem Verlauf.",
};

export function initials(name: string): string {
  return (name.match(/[A-ZÀ-Þ]/g) || [name[0]]).slice(0, 2).join("");
}
