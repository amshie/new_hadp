"""KPI catalog seed data (ADR-0004, release kpi-cat-2.0.0) — the single source of truth.

120 KPI definitions across the six HADP domains; only the 43 Core rows are `default_enabled`.
Definitions only: no reference/optimal ranges, no scores, no CIS/Actionability. `comparison_policy`
and per-row `value_kind` are populated in a later slice (ADR-0004 §0); they stay None here except
`value_kind='panel'` where a row has no canonical unit.
"""

from __future__ import annotations

# ruff: noqa: E501  -- wide rows: this is a data table, kept one KPI per line for reviewability.

CATALOG_VERSION = "kpi-cat-2.0.0"

# Code prefix -> primary DomainAxis value (reuses the existing closed DomainAxis enum).
_PREFIX_DOMAIN = {
    "metabolic": "metabolic",
    "immune": "immune_inflammation",
    "cardio": "cardiovascular",
    "neuro": "neurocognitive",
    "regen": "regenerative_capacity",
    "msk": "musculoskeletal",
}

# Derived-KPI formula ids (ADR-0004 §10). is_derived <=> presence here / measurement_class 'derived'.
FORMULA_IDS: dict[str, str] = {
    "metabolic.bmi": "bmi.v1",
    "metabolic.cgm_glucose_cv": "cgm_glucose_cv.v1",
    "metabolic.fib4": "fib4.v1",
    "metabolic.waist_height_ratio": "waist_height_ratio.v1",
    "metabolic.homa_ir": "homa_ir.v1",
    "immune.nlr": "nlr.v1",
    "cardio.non_hdl_c": "non_hdl_c.v1",
    "cardio.mean_arterial_pressure": "map.v1",
    "cardio.pulse_pressure": "pulse_pressure.v1",
    "regen.egfr_creatinine": "egfr_creatinine.ckd_epi_2021.v1",
    "regen.egfr_creatinine_cystatin": "egfr_creatinine_cystatin.ckd_epi_2021.v1",
    "regen.heart_rate_recovery_1min": "heart_rate_recovery_1min.v1",
    "regen.sleep_efficiency": "sleep_efficiency.v1",
    "regen.sleep_regularity": "sleep_regularity.v1",
    "msk.almi": "almi.v1",
}

# (tier, code, display_name, measurement_class, canonical_unit_ucum | None, default_enabled)
_ROWS: list[tuple[str, str, str, str, str | None, bool]] = [
    # --- Metabolic (20) ---
    ("core", "metabolic.alt", "Alanine aminotransferase", "laboratory", "[IU]/L", True),
    ("core", "metabolic.ast", "Aspartate aminotransferase", "laboratory", "[IU]/L", True),
    ("core", "metabolic.bmi", "Body mass index", "derived", "kg/m2", True),
    ("core", "metabolic.body_weight", "Body weight", "anthropometric", "kg", True),
    (
        "core",
        "metabolic.fasting_plasma_glucose",
        "Fasting plasma glucose",
        "laboratory",
        "mmol/L",
        True,
    ),
    ("core", "metabolic.ggt", "Gamma-glutamyl transferase", "laboratory", "[IU]/L", True),
    ("core", "metabolic.hba1c", "HbA1c", "laboratory", "%", True),
    ("core", "metabolic.triglycerides", "Triglycerides", "laboratory", "mmol/L", True),
    ("core", "metabolic.waist_circumference", "Waist circumference", "anthropometric", "cm", True),
    (
        "extended",
        "metabolic.body_fat_percent",
        "Body fat percentage",
        "body_composition",
        "%",
        False,
    ),
    ("extended", "metabolic.c_peptide", "C-peptide", "laboratory", "nmol/L", False),
    (
        "extended",
        "metabolic.cgm_glucose_cv",
        "CGM glucose coefficient of variation",
        "derived",
        "%",
        False,
    ),
    ("extended", "metabolic.cgm_mean_glucose", "CGM mean glucose", "wearable", "mmol/L", False),
    ("extended", "metabolic.cgm_time_in_range", "CGM time in range", "wearable", "%", False),
    ("extended", "metabolic.fasting_insulin", "Fasting insulin", "laboratory", "m[IU]/L", False),
    ("extended", "metabolic.fib4", "FIB-4 index", "derived", "1", False),
    (
        "extended",
        "metabolic.ogtt_2h_glucose",
        "OGTT 2-hour plasma glucose",
        "laboratory",
        "mmol/L",
        False,
    ),
    ("extended", "metabolic.uric_acid", "Uric acid", "laboratory", "umol/L", False),
    ("extended", "metabolic.waist_height_ratio", "Waist-to-height ratio", "derived", "1", False),
    ("research", "metabolic.homa_ir", "HOMA-IR", "derived", "1", False),
    # --- Immune / Inflammation (17) ---
    ("core", "immune.lymphocytes_abs", "Absolute lymphocyte count", "laboratory", "10*9/L", True),
    ("core", "immune.neutrophils_abs", "Absolute neutrophil count", "laboratory", "10*9/L", True),
    ("core", "immune.albumin", "Albumin", "laboratory", "g/L", True),
    ("core", "immune.ferritin", "Ferritin", "laboratory", "ug/L", True),
    ("core", "immune.hs_crp", "High-sensitivity C-reactive protein", "laboratory", "mg/L", True),
    ("core", "immune.platelets", "Platelet count", "laboratory", "10*9/L", True),
    ("core", "immune.wbc", "White blood cell count", "laboratory", "10*9/L", True),
    (
        "extended",
        "immune.eosinophils_abs",
        "Absolute eosinophil count",
        "laboratory",
        "10*9/L",
        False,
    ),
    ("extended", "immune.monocytes_abs", "Absolute monocyte count", "laboratory", "10*9/L", False),
    ("extended", "immune.crp", "C-reactive protein", "laboratory", "mg/L", False),
    ("extended", "immune.esr", "Erythrocyte sedimentation rate", "laboratory", "mm/h", False),
    ("extended", "immune.fibrinogen", "Fibrinogen", "laboratory", "g/L", False),
    ("extended", "immune.nlr", "Neutrophil-to-lymphocyte ratio", "derived", "1", False),
    ("research", "immune.glyca", "GlycA", "omics", "umol/L", False),
    (
        "research",
        "immune.inflammation_proteomics_panel",
        "Inflammation proteomics panel",
        "omics",
        None,
        False,
    ),
    ("research", "immune.il6", "Interleukin-6", "laboratory", "pg/mL", False),
    ("research", "immune.tnf_alpha", "Tumor necrosis factor alpha", "laboratory", "pg/mL", False),
    # --- Cardiovascular (17) ---
    ("core", "cardio.apob", "Apolipoprotein B", "laboratory", "g/L", True),
    ("core", "cardio.diastolic_bp", "Diastolic blood pressure", "vital_sign", "mm[Hg]", True),
    ("core", "cardio.hdl_c", "HDL cholesterol", "laboratory", "mmol/L", True),
    ("core", "cardio.ldl_c", "LDL cholesterol", "laboratory", "mmol/L", True),
    ("core", "cardio.lpa", "Lipoprotein(a)", "laboratory", "nmol/L", True),
    ("core", "cardio.non_hdl_c", "Non-HDL cholesterol", "derived", "mmol/L", True),
    ("core", "cardio.resting_heart_rate", "Resting heart rate", "vital_sign", "/min", True),
    ("core", "cardio.systolic_bp", "Systolic blood pressure", "vital_sign", "mm[Hg]", True),
    ("core", "cardio.total_cholesterol", "Total cholesterol", "laboratory", "mmol/L", True),
    ("extended", "cardio.abi", "Ankle-brachial index", "functional_test", "1", False),
    ("extended", "cardio.apoa1", "Apolipoprotein A-I", "laboratory", "g/L", False),
    (
        "extended",
        "cardio.cf_pwv",
        "Carotid-femoral pulse wave velocity",
        "functional_test",
        "m/s",
        False,
    ),
    (
        "extended",
        "cardio.cac_score",
        "Coronary artery calcium score",
        "imaging",
        "{Agatston}",
        False,
    ),
    (
        "extended",
        "cardio.mean_arterial_pressure",
        "Mean arterial pressure",
        "derived",
        "mm[Hg]",
        False,
    ),
    ("extended", "cardio.pulse_pressure", "Pulse pressure", "derived", "mm[Hg]", False),
    (
        "specialist",
        "cardio.central_systolic_bp",
        "Central systolic blood pressure",
        "vital_sign",
        "mm[Hg]",
        False,
    ),
    (
        "research",
        "cardio.coronary_plaque_volume",
        "Coronary plaque volume",
        "imaging",
        "mm3",
        False,
    ),
    # --- Neurocognitive (21) ---
    (
        "core",
        "neuro.cognitive_composite_score",
        "Cognitive battery composite score",
        "functional_test",
        "{score}",
        True,
    ),
    (
        "core",
        "neuro.episodic_memory_score",
        "Episodic memory score",
        "functional_test",
        "{score}",
        True,
    ),
    (
        "core",
        "neuro.executive_function_score",
        "Executive function score",
        "functional_test",
        "{score}",
        True,
    ),
    (
        "core",
        "neuro.processing_speed_score",
        "Processing speed score",
        "functional_test",
        "{score}",
        True,
    ),
    ("extended", "neuro.attention_score", "Attention score", "functional_test", "{score}", False),
    ("extended", "neuro.folate", "Folate", "laboratory", "nmol/L", False),
    ("extended", "neuro.homocysteine", "Homocysteine", "laboratory", "umol/L", False),
    (
        "extended",
        "neuro.hearing_pure_tone_average",
        "Pure-tone hearing average",
        "functional_test",
        "dB[HL]",
        False,
    ),
    ("extended", "neuro.reaction_time", "Reaction time", "functional_test", "ms", False),
    ("extended", "neuro.tsh", "Thyroid-stimulating hormone", "laboratory", "m[IU]/L", False),
    ("extended", "neuro.verbal_fluency", "Verbal fluency", "functional_test", "{words}/min", False),
    (
        "extended",
        "neuro.visual_acuity_logmar",
        "Visual acuity",
        "functional_test",
        "{logMAR}",
        False,
    ),
    ("extended", "neuro.vitamin_b12", "Vitamin B12", "laboratory", "pmol/L", False),
    (
        "extended",
        "neuro.working_memory_score",
        "Working memory score",
        "functional_test",
        "{score}",
        False,
    ),
    (
        "specialist",
        "neuro.abeta42_40_ratio",
        "Plasma amyloid beta 42/40 ratio",
        "laboratory",
        "1",
        False,
    ),
    ("specialist", "neuro.ptau181", "Plasma phosphorylated tau 181", "laboratory", "pg/mL", False),
    ("specialist", "neuro.ptau217", "Plasma phosphorylated tau 217", "laboratory", "pg/mL", False),
    ("research", "neuro.gfap", "Glial fibrillary acidic protein", "laboratory", "pg/mL", False),
    ("research", "neuro.hippocampal_volume", "Hippocampal volume", "imaging", "mL", False),
    ("research", "neuro.nfl", "Neurofilament light chain", "laboratory", "pg/mL", False),
    ("research", "neuro.wmh_volume", "White matter hyperintensity volume", "imaging", "mL", False),
    # --- Regenerative Capacity (22) ---
    ("core", "regen.creatinine", "Creatinine", "laboratory", "umol/L", True),
    (
        "core",
        "regen.egfr_creatinine",
        "eGFR, creatinine-based",
        "derived",
        "mL/min/{1.73_m2}",
        True,
    ),
    ("core", "regen.hrv_rmssd", "Heart rate variability RMSSD", "wearable", "ms", True),
    ("core", "regen.hemoglobin", "Hemoglobin", "laboratory", "g/L", True),
    ("core", "regen.sleep_efficiency", "Sleep efficiency", "derived", "%", True),
    ("core", "regen.steps_per_day", "Steps per day", "wearable", "{steps}/d", True),
    ("core", "regen.sleep_duration", "Total sleep time", "wearable", "min", True),
    (
        "core",
        "regen.uacr",
        "Urine albumin-to-creatinine ratio",
        "laboratory",
        "mg/mmol{creat}",
        True,
    ),
    (
        "core",
        "regen.vo2peak_direct",
        "VO2peak, directly measured",
        "functional_test",
        "mL/(kg.min)",
        True,
    ),
    (
        "extended",
        "regen.reticulocytes_abs",
        "Absolute reticulocyte count",
        "laboratory",
        "10*9/L",
        False,
    ),
    ("extended", "regen.cystatin_c", "Cystatin C", "laboratory", "mg/L", False),
    (
        "extended",
        "regen.egfr_creatinine_cystatin",
        "eGFR, creatinine-cystatin C",
        "derived",
        "mL/min/{1.73_m2}",
        False,
    ),
    (
        "extended",
        "regen.heart_rate_recovery_1min",
        "Heart rate recovery at 1 minute",
        "derived",
        "/min",
        False,
    ),
    ("extended", "regen.hrv_sdnn", "Heart rate variability SDNN", "wearable", "ms", False),
    (
        "extended",
        "regen.nocturnal_spo2_mean",
        "Mean nocturnal oxygen saturation",
        "wearable",
        "%",
        False,
    ),
    (
        "extended",
        "regen.mvpa_minutes_per_day",
        "Moderate-to-vigorous activity",
        "wearable",
        "min/d",
        False,
    ),
    (
        "extended",
        "regen.nocturnal_respiratory_rate",
        "Nocturnal respiratory rate",
        "wearable",
        "/min",
        False,
    ),
    ("extended", "regen.sedentary_minutes_per_day", "Sedentary time", "wearable", "min/d", False),
    ("extended", "regen.sleep_onset_latency", "Sleep onset latency", "wearable", "min", False),
    ("extended", "regen.sleep_regularity", "Sleep regularity index", "derived", "%", False),
    ("extended", "regen.vo2max_estimated", "VO2max, estimated", "wearable", "mL/(kg.min)", False),
    ("extended", "regen.waso", "Wake after sleep onset", "wearable", "min", False),
    # --- Musculoskeletal (23) ---
    (
        "core",
        "msk.appendicular_lean_mass",
        "Appendicular lean mass",
        "body_composition",
        "kg",
        True,
    ),
    ("core", "msk.almi", "Appendicular lean mass index", "derived", "kg/m2", True),
    ("core", "msk.chair_stand_5_time", "Five-chair-stand time", "functional_test", "s", True),
    ("core", "msk.grip_strength", "Grip strength", "functional_test", "[kgf]", True),
    ("core", "msk.gait_speed", "Usual gait speed", "functional_test", "m/s", True),
    ("extended", "msk.vitamin_d_25oh", "25-hydroxyvitamin D", "laboratory", "nmol/L", False),
    ("extended", "msk.alp", "Alkaline phosphatase", "laboratory", "[IU]/L", False),
    ("extended", "msk.calcium", "Calcium", "laboratory", "mmol/L", False),
    (
        "extended",
        "msk.femoral_neck_bmd",
        "Femoral neck bone mineral density",
        "imaging",
        "g/cm2",
        False,
    ),
    ("extended", "msk.femoral_neck_t_score", "Femoral neck T-score", "imaging", "{T-score}", False),
    (
        "extended",
        "msk.lumbar_spine_bmd",
        "Lumbar spine bone mineral density",
        "imaging",
        "g/cm2",
        False,
    ),
    ("extended", "msk.lumbar_spine_t_score", "Lumbar spine T-score", "imaging", "{T-score}", False),
    ("extended", "msk.pth", "Parathyroid hormone", "laboratory", "pmol/L", False),
    ("extended", "msk.phosphate", "Phosphate", "laboratory", "mmol/L", False),
    (
        "extended",
        "msk.sppb_total",
        "Short Physical Performance Battery total score",
        "functional_test",
        "{score}",
        False,
    ),
    ("extended", "msk.single_leg_stance", "Single-leg stance time", "functional_test", "s", False),
    (
        "extended",
        "msk.six_min_walk_distance",
        "Six-minute walk distance",
        "functional_test",
        "m",
        False,
    ),
    ("extended", "msk.timed_up_and_go", "Timed Up and Go", "functional_test", "s", False),
    ("extended", "msk.total_hip_bmd", "Total hip bone mineral density", "imaging", "g/cm2", False),
    ("extended", "msk.total_hip_t_score", "Total hip T-score", "imaging", "{T-score}", False),
    ("extended", "msk.total_lean_mass", "Total lean mass", "body_composition", "kg", False),
    (
        "specialist",
        "msk.ctx",
        "C-terminal telopeptide of type I collagen",
        "laboratory",
        "ng/L",
        False,
    ),
    (
        "specialist",
        "msk.p1np",
        "Procollagen type I N-terminal propeptide",
        "laboratory",
        "ug/L",
        False,
    ),
]


def kpi_rows() -> list[dict[str, object]]:
    """Materialize the catalog rows with derived fields filled in."""
    out: list[dict[str, object]] = []
    for tier, code, name, mclass, unit, default_enabled in _ROWS:
        domain = _PREFIX_DOMAIN[code.split(".", 1)[0]]
        is_derived = mclass == "derived"
        out.append(
            {
                "code": code,
                "display_name": name,
                "primary_domain_axis": domain,
                "measurement_class": mclass,
                "value_kind": "panel" if unit is None else None,
                "canonical_unit_ucum": unit,
                "tier": tier,
                "default_enabled": default_enabled,
                "is_derived": is_derived,
                "formula_id": FORMULA_IDS.get(code),
                "clinician_visible": True,
                "patient_visible": False,
            }
        )
    return out


# Verified external code mappings (ADR-0004 §11). Only these are eligible for automatic mapping.
VERIFIED_EXTERNAL_CODES: list[tuple[str, str, str, str]] = [
    ("metabolic.hba1c", "LOINC", "4548-4", "HbA1c, NGSP-aligned reporting"),
    ("metabolic.hba1c", "LOINC", "59261-8", "HbA1c, IFCC protocol"),
    ("immune.hs_crp", "LOINC", "30522-7", "Serum/plasma, high-sensitivity method"),
    ("cardio.apob", "LOINC", "1884-6", "Serum/plasma mass concentration"),
    ("cardio.systolic_bp", "LOINC", "8480-6", "Systolic blood pressure"),
    ("cardio.diastolic_bp", "LOINC", "8462-4", "Diastolic blood pressure"),
    ("cardio.lpa", "LOINC", "43583-4", "Serum/plasma substance concentration"),
]

# Explicit global source-name aliases (lowercased) -> kpi_code, beyond the auto display-name alias.
# Covers the existing importer/seed source terms (normalize.py _TERMINOLOGY + seed markers).
EXTRA_ALIASES: list[tuple[str, str]] = [
    ("ldl", "cardio.ldl_c"),
    ("ldl cholesterol", "cardio.ldl_c"),
    ("hdl cholesterol", "cardio.hdl_c"),
    ("total cholesterol", "cardio.total_cholesterol"),
    ("glucose", "metabolic.fasting_plasma_glucose"),
    ("nüchternglukose", "metabolic.fasting_plasma_glucose"),
    ("hba1c", "metabolic.hba1c"),
    ("hs-crp", "immune.hs_crp"),
    ("apob", "cardio.apob"),
    ("verarbeitungsgeschwindigkeit", "neuro.processing_speed_score"),
    ("griffstärke", "msk.grip_strength"),
    ("vo2max", "regen.vo2peak_direct"),
    ("hrv", "regen.hrv_rmssd"),
]

# Secondary domain membership (ADR-0004 §4.2, §7 "Secondary domains" column; Slice 2).
#
# Each KPI has ONE primary domain (stored on kpi_catalog); these are the additional domains where
# the same single Observation is relevant. A secondary link is NAVIGATIONAL evidence-visibility
# ONLY: it never duplicates the Observation across domains (ADR-0004 §3/§15) and never feeds,
# weights or derives a domain's CIS or Actionability (ADR-0003 — verdicts stay per-axis; tri-state
# stays separate). 34 KPIs, 44 links, transcribed row-by-row from ADR-0004 §7.
SECONDARY_DOMAINS: dict[str, list[str]] = {
    # --- Metabolic ---
    "metabolic.alt": ["regenerative_capacity"],
    "metabolic.ast": ["regenerative_capacity"],
    "metabolic.bmi": ["musculoskeletal", "cardiovascular"],
    "metabolic.body_weight": ["musculoskeletal", "cardiovascular"],
    "metabolic.fasting_plasma_glucose": ["cardiovascular"],
    "metabolic.ggt": ["regenerative_capacity"],
    "metabolic.hba1c": ["cardiovascular", "neurocognitive"],
    "metabolic.triglycerides": ["cardiovascular"],
    "metabolic.waist_circumference": ["cardiovascular"],
    "metabolic.body_fat_percent": ["musculoskeletal"],
    "metabolic.fib4": ["regenerative_capacity"],
    "metabolic.uric_acid": ["cardiovascular"],
    "metabolic.waist_height_ratio": ["cardiovascular"],
    # --- Immune / Inflammation ---
    "immune.albumin": ["regenerative_capacity"],
    "immune.ferritin": ["regenerative_capacity", "musculoskeletal"],
    "immune.hs_crp": ["cardiovascular"],
    "immune.platelets": ["metabolic", "regenerative_capacity"],
    # --- Cardiovascular ---
    "cardio.resting_heart_rate": ["regenerative_capacity"],
    # --- Neurocognitive ---
    "neuro.homocysteine": ["cardiovascular"],
    # --- Regenerative Capacity ---
    "regen.creatinine": ["cardiovascular", "metabolic"],
    "regen.egfr_creatinine": ["cardiovascular", "metabolic"],
    "regen.sleep_efficiency": ["neurocognitive"],
    "regen.sleep_duration": ["neurocognitive"],
    "regen.uacr": ["cardiovascular", "metabolic"],
    "regen.vo2peak_direct": ["cardiovascular"],
    "regen.cystatin_c": ["cardiovascular"],
    "regen.egfr_creatinine_cystatin": ["cardiovascular"],
    "regen.heart_rate_recovery_1min": ["cardiovascular"],
    "regen.sleep_onset_latency": ["neurocognitive"],
    "regen.sleep_regularity": ["neurocognitive"],
    "regen.vo2max_estimated": ["cardiovascular"],
    "regen.waso": ["neurocognitive"],
    # --- Musculoskeletal ---
    "msk.gait_speed": ["neurocognitive", "regenerative_capacity"],
    "msk.six_min_walk_distance": ["cardiovascular", "regenerative_capacity"],
}


def kpi_secondary_domain_rows() -> list[tuple[str, str]]:
    """Materialize (kpi_code, secondary_domain_axis) pairs from SECONDARY_DOMAINS.

    Validates every code against the catalog and every axis against the closed domain set, and
    raises if a secondary domain equals the KPI's primary domain (ADR-0004 §13 step 7: secondary
    != primary) or is duplicated. A bad link is a seed failure, never a runtime guess.
    """
    primary = {str(r["code"]): str(r["primary_domain_axis"]) for r in kpi_rows()}
    valid_axes = set(_PREFIX_DOMAIN.values())
    out: list[tuple[str, str]] = []
    for code, secondaries in SECONDARY_DOMAINS.items():
        if code not in primary:
            raise ValueError(f"secondary-domain for unknown KPI code: {code}")
        seen: set[str] = set()
        for axis in secondaries:
            if axis not in valid_axes:
                raise ValueError(f"unknown secondary domain axis: {code} -> {axis}")
            if axis == primary[code]:
                raise ValueError(f"secondary domain equals primary: {code} -> {axis}")
            if axis in seen:
                raise ValueError(f"duplicate secondary domain: {code} -> {axis}")
            seen.add(axis)
            out.append((code, axis))
    return out
