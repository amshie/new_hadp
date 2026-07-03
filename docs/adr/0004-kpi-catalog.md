# ADR-0004: KPI catalog v2 — canonical reference data for the six HADP domains

- Status: **Accepted (2026-06-22)** — corrected per four-specialist review; **§0 (M1–M5) is
  authoritative over any conflicting statement in the sections below.** Slice 1 is build-ready.
- Date: **2026-06-22**
- Supersedes: the original ADR-0004 KPI-catalog shape (v1).
- Relates: ADR-0003 (HADP governance doctrine), ADR-0002 (wiring)
- Catalog release: `kpi-cat-2.0.0`
- Seed files: catalog data lives in `modules/kpi/catalog_data.py` (single source of truth; seeded
  via a versioned seed function, not inline migration SQL).

## 0. Review corrections (authoritative) + build framing

A four-specialist review (data · architecture · regulatory · CTO-strategy) approved this design
**with the corrections below. These override any conflicting statement in §1–§13.**

**Project framing.** We build the full product **step by step** — not an "alpha-minimal" scope. The
catalog is seeded in full (all definitions), with only **Core** `default_enabled=true`. The deferred
items below are **committed subsequent slices**, not "maybe later." The **synthetic-data-only** gate
and the human regulatory gates (MDR/SaMD · DPO/DPIA · counsel) **remain in force** — they govern real
patient data, independent of build scope.

- **M1 — read-only is enforced by REVOKE, not GRANT.** `alembic/versions/0002_security_rls.py:67-72`
  grants `hadp_app` full DML on all current **and future** tables. The catalog migration MUST
  `REVOKE INSERT, UPDATE, DELETE, TRUNCATE … FROM hadp_app` on each catalog table, then `GRANT SELECT`.
  The read-only test runs under the `hadp_app` role.
- **M2 — closed enums are CHECK-backed (`pg_enum`, `native_enum=False`), not native PG types.** All new
  vocabularies (`measurement_class`, `value_kind`, `tier`, `comparison_policy`, `status`, external-code
  `verification_status`, release `status`) go in `modules/enums.py` via the existing `pg_enum` helper.
  Domain columns **reuse the existing `DomainAxis` value set** (`metabolic · immune_inflammation ·
cardiovascular · neurocognitive · regenerative_capacity · musculoskeletal`) — no native `domain_axis`
  type; the catalog's display labels map onto these values.
- **M3 — `metric_code` stays the source/LOINC code; add `observations.kpi_code`.** Do not rewrite
  `observations.metric_code`. Add a nullable `observations.kpi_code` (FK → `kpi_catalog.code`), set by
  the normalizer and backfilled on seeded rows. Interpretation evidence and the dashboard keep reading
  what they read today; `kpi_code` is the new catalog linkage. Additive and reversible.
- **M4 — seed ↔ catalog reconciliation (before any import-behavior test).** Existing seed markers map
  to catalog codes/aliases: HbA1c→`metabolic.hba1c`, glucose `2345-7`→`metabolic.fasting_plasma_glucose`,
  hs-CRP→`immune.hs_crp` (verified LOINC `30522-7`; the seed's `1988-5` becomes an alias/external-code),
  ApoB→`cardio.apob`, LDL→`cardio.ldl_c`, `SYN-PROC`→`neuro.processing_speed_score`,
  `SYN-GRIP`→`msk.grip_strength`, `SYN-VO2`→`regen.vo2peak_direct`, `SYN-HRV`→`regen.hrv_rmssd`.
- **M5 — `source_category` + derived-provenance live on the Observation and are NOT built here.**
  `observations` has none of `source_category`, `source_system`, `derived_from`, `formula_version`
  today; these are **separate prerequisite additive migrations** (Slices 3/4). Until they exist the
  §8/§9 non-merge guarantees are documentation only — they bind once those slices land.

**Committed build order (step by step):**

1. **Slice 1 (this slice):** `kpi_catalog_release` + `kpi_catalog` + `kpi_external_code` + `kpi_alias`;
   CHECK enums; REVOKE+GRANT SELECT; CHECKs (`is_derived ⇔ formula_id`; `value_kind='panel' ⇒ unit null`;
   `tier ∈ {specialist,research} ⇒ patient_visible=false`); alias collision = migration/seed failure;
   seed the full catalog (Core enabled) + verified external codes + aliases; `observations.kpi_code`;
   normalizer resolves `kpi_code`; tests under `hadp_app`.
2. **Slice 2:** `kpi_secondary_domain` + dashboard primary/secondary grouping.
3. **Slice 3:** `Observation.source_category`/`source_system` + measurement context + §8/§9 non-merge rules.
4. **Slice 4:** versioned formula registry + derived-Observation computation (`derived_from` + algorithm +
   version) — the **only** place the validate-never-derive risk lives; its own review + clinical sign-off.

`comparison_policy` is **stored** on the catalog in Slice 1 but **enforced/rendered only later** (internal
review-routing only; never a rendered comparability verdict without clinical sign-off).

**Slice 2 doctrine — secondary domains are navigational only.** A `kpi_secondary_domain` link surfaces
the same single Observation in an additional domain where it is relevant; it is read-only navigation.
It MUST NOT: duplicate the Observation across domains (§3/§15 — one canonical row, many links); feed,
weight, or derive any domain's CIS or Actionability (ADR-0003 — verdicts stay per-axis, tri-state stays
separate); or render a cross-domain aggregate, comparability verdict, or score. `secondary != primary`
is enforced **at seed time** (a seed failure, like the alias-collision guard), not by a table CHECK.
Slice 2 ships the **table + seed + read helpers only** (backend, no UI). The visible domain-view grouping
is **Slice 2b**, gated on its own review, and binds these UI guardrails: (1) a secondary biomarker is
shown in a section visually/semantically separated from the domain's own evidence, carrying its
primary-domain attribution; (2) an un-measured secondary KPI renders `not_observed`, never
"normal/stable/in range" (§13); (3) Specialist/Research (patient-hidden) KPIs are filtered out of any
patient-facing secondary section by the same tier/visibility gates as the primary view; (4) the
secondary-section labels (DE/EN) are added to the language scan before they ship. Slice 2b also adds the
`CLASSIFICATION_REGISTER` row (documentation-support, navigational) and its Regulatory-Lead sign-off.

**Slice 3 doctrine — comparability is fail-closed validation, not derivation.** Slice 3 adds additive,
nullable measurement-context columns to `observations` (`source_category` reusing the `KpiMeasurementClass`
value set, `source_system`, `method`, `protocol`, `device_model`, `firmware_or_algorithm_version`,
`instrument_version`) and wires the §9 non-merge rules into `build_timeline`. The longitudinal delta key
moves from `metric_code` to the canonical `kpi_code` (fallback `metric_code`). Each KPI's comparison policy
is resolved **at read time** per `measurement_class` (a `policy_for_measurement_class` default) — the
catalog's per-KPI `comparison_policy` stays NULL and is the later, clinician-signed override path; **no
catalog reseed**. Only the classes whose §9 cases need recorded context require matching context
(`body_composition`/`wearable` → device+algorithm; `functional_test` → instrument version; `imaging` →
protocol+software; `omics` → platform); `laboratory`/`vital_sign`/`anthropometric`/`derived` stay
`method_aware` (compare on KPI + unit), so existing deltas are unaffected. **Fail-closed:** if a
policy-required context field is missing or differs, the numeric delta is **withheld** (an incomparable
delta is a fabricated change) and a verdict-free `comparability` marker (`comparable` / `not_comparable`

- reason) is set on the timeline point — disjoint from CIS/Actionability, never a score. The §8 columns are
  **required-to-merge, not required-to-store**: they stay nullable, populated only when a source supplies
  them (never inferred, §9.8); the marker is exposed in the API but its UI rendering is a later gated slice
  (DE/EN labels through the language scan). Slice 3 adds a `CLASSIFICATION_REGISTER` row (provenance +
  comparability gating, documentation-support) with Regulatory-Lead sign-off. Derived-Observation provenance
  (`derived_from` / formula version) remains **Slice 4**.

**Slice 4 doctrine — derived values are deterministic, provenance-pinned, fail-closed; not verdicts.** Slice
4 builds a **versioned formula registry** (pure `Decimal→Decimal` functions, `modules/derivations`) + a
**controlled** `compute_derived` service that writes a new `source_category='derived'` Observation carrying a
frozen `formula_id`/`formula_version`/`algorithm_name` snapshot, with the immutable input IDs in a new
tenant-scoped, RLS, **append-only** `observation_derivation` table (ADR-0004 §8). Deterministic arithmetic is
allowed (CLAUDE.md); a derived value is **never** a verdict, score, CIS/Actionability, "optimal" target, or a
_measured_ value, and never feeds a domain verdict automatically. **§10 no-auto-run:** computation is an
explicit controlled call (seed/CLI/clinician-authorized), never on import. **§9.8 fail-closed:** a formula
runs only if every input is PUBLISHED, correct-unit, non-superseded; a missing input yields NO derived value
(never inferred, never partial). The Slice-3 placeholders become real: a `formula_version` column on the
Observation, `POLICY_REQUIRED_COLUMNS[same_formula_version_required] = ("formula_version",)`, and
`_CLASS_DEFAULT_POLICY[derived] = same_formula_version_required` — two derived values only trend if computed
by the same version. **First tranche (built):** trivially-safe arithmetic only — `non_hdl_c.v1`,
`pulse_pressure.v1`, `map.v1`, `nlr.v1`. **Gated OUT (own, clinician-signed sub-slices):** the clinical
estimators `egfr_creatinine.ckd_epi_2021.v1`/`…cystatin`, `fib4.v1`, `homa_ir.v1`, `almi.v1` (named validated
equations + sign-off; eGFR additionally blocked on a `patients.sex` field, a DPO/lawful-basis gate; BMI/WHtR
need a height KPI not yet in the catalog); and all wearable-derived (`sleep_*`, `cgm_glucose_cv`,
`heart_rate_recovery_1min`) until their inputs are modelled. Derived values are **excluded from the report
evidence/narrative** for now (they would read as measured); labelled inclusion is deferred to the derived-UI
slice. Slice 4 adds a `CLASSIFICATION_REGISTER` row (documentation-support, Regulatory-Lead sign-off for the
arithmetic tranche; the estimator tranche stays BLOCKED pending per-equation clinical sign-off).

## 1. Decision summary

Create one global, read-only KPI terminology layer for HADP. The catalog defines **what a KPI is**:
its stable HADP code, display name, primary and secondary domain membership, measurement class,
value kind, canonical UCUM unit, rollout tier, aliases and longitudinal-comparison policy.

The catalog does **not** contain patient values, clinical interpretation, risk status, reference
ranges, target ranges, recommendations, CIS, Actionability or any unified score.

The catalog contains **120 KPI definitions**. Only the **43 Core KPIs** are enabled by default.
Extended, Specialist and Research KPIs are seeded but disabled by default.

| Domain                | Core | Extended | Specialist | Research | Total |
| --------------------- | ---- | -------- | ---------- | -------- | ----- |
| Metabolic             | 9    | 10       | 0          | 1        | 20    |
| Immune / Inflammation | 7    | 6        | 0          | 4        | 17    |
| Cardiovascular        | 9    | 6        | 1          | 1        | 17    |
| Neurocognitive        | 4    | 10       | 3          | 4        | 21    |
| Regenerative Capacity | 9    | 13       | 0          | 0        | 22    |
| Musculoskeletal       | 5    | 16       | 2          | 0        | 23    |

## 2. Why the current proposal must be changed before implementation

The original proposal correctly identifies the need for a global reference table, but four parts
would create avoidable data-quality problems:

1. **LOINC must not be the HADP primary key.** A clinically similar KPI can map to multiple LOINC
   terms depending on specimen, property, timing or method. HADP therefore uses a stable internal
   code such as `cardio.apob`; verified LOINC mappings live in a separate mapping table.
2. **Actual source category belongs to the Observation.** The same KPI can be measured by a clinic,
   laboratory, imaging system, CPET system or wearable. A singular `source_category` on the KPI
   definition would misclassify real observations. For example, directly measured VO₂peak and a
   wearable VO₂max estimate are deliberately separate KPIs.
3. **Domain membership is many-to-many.** Each KPI has one primary domain for navigation and may
   have secondary domain links. The same hs-CRP, eGFR or gait-speed Observation is never duplicated
   across domains.
4. **Versioning must preserve a stable identity.** `code` remains stable. A semantic change creates
   a new KPI code; non-semantic corrections are migration-controlled. Catalog releases record
   `introduced_in` and `deprecated_in`. Do not duplicate the full row set under a new version while
   also using `code` as the primary key.

## 3. Catalog doctrine

The following rules are non-negotiable:

- **Reference data only.** A catalog row is not a diagnosis, clinical recommendation or claim of
  healthspan benefit.
- **No ranges.** Never add `reference_low`, `reference_high`, `optimal`, `target`, `goal` or
  proprietary threshold columns. Laboratory reference intervals remain attached to each
  Observation.
- **No unified score — by design.** The catalog cannot calculate domain status, biological age,
  Healthspan score, CIS or Actionability.
- **No auto-publication.** Unknown, ambiguous, unsupported-unit or low-confidence imports remain
  `PENDING` until reviewed.
- **No duplicate cross-domain values.** One canonical Observation may have several domain links.
- **Source preservation.** Original name, original value, original unit, source document and
  measurement context are immutable.
- **Clinician-first visibility.** All catalog rows default to `patient_visible=false`. Any
  patient-facing display remains physician-gated.
- **No biological-age constructs.** Biological-age scores, methylation-age clocks, telomere-age
  claims, NAD+ scores, vendor readiness scores and unified longevity scores are not production
  catalog KPIs.

## 4. Data model

### 4.1 `kpi_catalog`

Global reference data; no `tenant_id`; no tenant RLS. `hadp_app` receives `SELECT` only.

| Column                | Type                    | Constraint / meaning                                      |
| --------------------- | ----------------------- | --------------------------------------------------------- |
| `code`                | text PK                 | Stable HADP code, e.g. `metabolic.hba1c`                  |
| `display_name`        | text                    | Canonical English name                                    |
| `primary_domain_axis` | `domain_axis`           | Closed six-value enum                                     |
| `measurement_class`   | `kpi_measurement_class` | Closed enum defined below                                 |
| `value_kind`          | `kpi_value_kind`        | Closed enum defined below                                 |
| `canonical_unit_ucum` | text nullable           | Machine unit; null only for panel/container KPIs          |
| `display_unit`        | text nullable           | Human-readable unit                                       |
| `tier`                | `kpi_catalog_tier`      | `core`, `extended`, `specialist`, `research`              |
| `default_enabled`     | boolean                 | True only for the Core default loadout                    |
| `is_derived`          | boolean                 | True only when value is computed from source Observations |
| `formula_id`          | text nullable           | Required for derived KPIs; versioned                      |
| `comparison_policy`   | `kpi_comparison_policy` | Required longitudinal comparability rule                  |
| `clinician_visible`   | boolean                 | Default true                                              |
| `patient_visible`     | boolean                 | Default false                                             |
| `status`              | `kpi_status`            | `active`, `deprecated`, `blocked`                         |
| `introduced_in`       | text FK                 | Catalog release                                           |
| `deprecated_in`       | text nullable FK        | Catalog release                                           |
| `created_at`          | timestamptz             | Server timestamp                                          |

### 4.2 Supporting KPI-reference tables

These tables remain global and read-only to the application role.

#### `kpi_alias`

| Column             | Type          | Meaning                                     |
| ------------------ | ------------- | ------------------------------------------- |
| `id`               | bigint PK     |                                             |
| `kpi_code`         | text FK       | `kpi_catalog.code`                          |
| `alias_normalized` | text          | Lowercased, Unicode-normalized source label |
| `locale`           | text          | Default `und`; examples `en`, `de`          |
| `source_system`    | text nullable | Optional lab/vendor namespace               |
| `priority`         | smallint      | Deterministic alias preference              |
| `created_at`       | timestamptz   |                                             |

A normalized alias may map to only one active KPI within the same source-system namespace. Any
collision is a migration failure, not a runtime guess.

#### `kpi_external_code`

| Column                | Type                 | Meaning                                            |
| --------------------- | -------------------- | -------------------------------------------------- |
| `kpi_code`            | text FK              | HADP canonical KPI                                 |
| `code_system`         | text                 | `LOINC`, `SNOMED_CT`, another verified system      |
| `external_code`       | text                 | Exact external identifier                          |
| `mapping_context`     | jsonb                | Specimen, method, property or protocol constraints |
| `verification_status` | enum                 | `verified`, `pending`, `rejected`                  |
| `verified_at`         | timestamptz nullable |                                                    |
| `verified_by`         | text nullable        | Named reviewer / controlled process                |

Only `verified` mappings are eligible for automatic import mapping. A textual alias can never
upgrade an unverified external-code mapping.

#### `kpi_secondary_domain`

| Column        | Type                      | Meaning     |
| ------------- | ------------------------- | ----------- |
| `kpi_code`    | text FK                   |             |
| `domain_axis` | `domain_axis`             | Closed enum |
| PK            | `(kpi_code, domain_axis)` |             |

The primary domain is stored once in `kpi_catalog`; this table contains only secondary links.

#### `kpi_catalog_release`

| Column        | Type                 | Meaning                                |
| ------------- | -------------------- | -------------------------------------- |
| `version`     | text PK              | Semantic release, e.g. `kpi-cat-2.0.0` |
| `status`      | enum                 | `draft`, `active`, `retired`           |
| `released_at` | timestamptz nullable |                                        |
| `notes`       | text                 |                                        |

### 4.3 Closed enums

```text
kpi_measurement_class =
  laboratory
  vital_sign
  anthropometric
  body_composition
  functional_test
  wearable
  imaging
  derived
  omics

kpi_value_kind =
  quantity
  count
  duration
  ratio
  score
  panel

kpi_catalog_tier =
  core
  extended
  specialist
  research

kpi_comparison_policy =
  method_aware
  same_method_required
  same_protocol_required
  same_device_protocol_required
  same_device_algorithm_required
  same_instrument_version_required
  same_imaging_protocol_required
  same_formula_version_required
  same_omics_platform_required
  not_longitudinal

kpi_status =
  active
  deprecated
  blocked
```

## 5. Observation/source boundary

The following fields belong to the patient Observation or its Provenance record, **not** to
`kpi_catalog`:

- actual source category and source system;
- original label, value and unit;
- specimen and body site;
- collection, measurement, receipt and report timestamps;
- fasting state, challenge protocol and relevant collection context;
- assay, method, instrument, device model, firmware and algorithm version;
- laboratory reference interval supplied with that result;
- source document and source-row identifier;
- import confidence and review status;
- reviewer, verification timestamp and supersession lineage.

The normalizer resolves a source term to a canonical KPI. It does not create clinical meaning.

## 6. Tier semantics

| Tier           | Use                                                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Core**       | Default MVP loadout. Common, operationally feasible and suitable for routine longitudinal display when provenance is complete.    |
| **Extended**   | Optional clinic-protocol KPI. Requires additional context, equipment, protocol or indication.                                     |
| **Specialist** | Specialty-gated KPI. Clinician-only, disabled by default, and not released without the relevant workflow gate.                    |
| **Research**   | Exploratory or platform-sensitive. Disabled by default; cannot independently drive patient-facing language, CIS or Actionability. |

Tier is a product-governance property, not a clinical recommendation or evidence grade.

## 7. Complete six-domain KPI catalog

### Metabolic

| Tier     | Canonical code                     | KPI                                  | Measurement class  | Canonical unit (UCUM) | Secondary domains               | Default |
| -------- | ---------------------------------- | ------------------------------------ | ------------------ | --------------------- | ------------------------------- | ------- |
| Core     | `metabolic.alt`                    | Alanine aminotransferase             | `laboratory`       | `[IU]/L`              | Regenerative Capacity           | Yes     |
| Core     | `metabolic.ast`                    | Aspartate aminotransferase           | `laboratory`       | `[IU]/L`              | Regenerative Capacity           | Yes     |
| Core     | `metabolic.bmi`                    | Body mass index                      | `derived`          | `kg/m2`               | Musculoskeletal, Cardiovascular | Yes     |
| Core     | `metabolic.body_weight`            | Body weight                          | `anthropometric`   | `kg`                  | Musculoskeletal, Cardiovascular | Yes     |
| Core     | `metabolic.fasting_plasma_glucose` | Fasting plasma glucose               | `laboratory`       | `mmol/L`              | Cardiovascular                  | Yes     |
| Core     | `metabolic.ggt`                    | Gamma-glutamyl transferase           | `laboratory`       | `[IU]/L`              | Regenerative Capacity           | Yes     |
| Core     | `metabolic.hba1c`                  | HbA1c                                | `laboratory`       | `%`                   | Cardiovascular, Neurocognitive  | Yes     |
| Core     | `metabolic.triglycerides`          | Triglycerides                        | `laboratory`       | `mmol/L`              | Cardiovascular                  | Yes     |
| Core     | `metabolic.waist_circumference`    | Waist circumference                  | `anthropometric`   | `cm`                  | Cardiovascular                  | Yes     |
| Extended | `metabolic.body_fat_percent`       | Body fat percentage                  | `body_composition` | `%`                   | Musculoskeletal                 | No      |
| Extended | `metabolic.c_peptide`              | C-peptide                            | `laboratory`       | `nmol/L`              | —                               | No      |
| Extended | `metabolic.cgm_glucose_cv`         | CGM glucose coefficient of variation | `derived`          | `%`                   | —                               | No      |
| Extended | `metabolic.cgm_mean_glucose`       | CGM mean glucose                     | `wearable`         | `mmol/L`              | —                               | No      |
| Extended | `metabolic.cgm_time_in_range`      | CGM time in range                    | `wearable`         | `%`                   | —                               | No      |
| Extended | `metabolic.fasting_insulin`        | Fasting insulin                      | `laboratory`       | `m[IU]/L`             | —                               | No      |
| Extended | `metabolic.fib4`                   | FIB-4 index                          | `derived`          | `1`                   | Regenerative Capacity           | No      |
| Extended | `metabolic.ogtt_2h_glucose`        | OGTT 2-hour plasma glucose           | `laboratory`       | `mmol/L`              | —                               | No      |
| Extended | `metabolic.uric_acid`              | Uric acid                            | `laboratory`       | `umol/L`              | Cardiovascular                  | No      |
| Extended | `metabolic.waist_height_ratio`     | Waist-to-height ratio                | `derived`          | `1`                   | Cardiovascular                  | No      |
| Research | `metabolic.homa_ir`                | HOMA-IR                              | `derived`          | `1`                   | —                               | No      |

### Immune / Inflammation

| Tier     | Canonical code                         | KPI                                 | Measurement class | Canonical unit (UCUM) | Secondary domains                      | Default |
| -------- | -------------------------------------- | ----------------------------------- | ----------------- | --------------------- | -------------------------------------- | ------- |
| Core     | `immune.lymphocytes_abs`               | Absolute lymphocyte count           | `laboratory`      | `10*9/L`              | —                                      | Yes     |
| Core     | `immune.neutrophils_abs`               | Absolute neutrophil count           | `laboratory`      | `10*9/L`              | —                                      | Yes     |
| Core     | `immune.albumin`                       | Albumin                             | `laboratory`      | `g/L`                 | Regenerative Capacity                  | Yes     |
| Core     | `immune.ferritin`                      | Ferritin                            | `laboratory`      | `ug/L`                | Regenerative Capacity, Musculoskeletal | Yes     |
| Core     | `immune.hs_crp`                        | High-sensitivity C-reactive protein | `laboratory`      | `mg/L`                | Cardiovascular                         | Yes     |
| Core     | `immune.platelets`                     | Platelet count                      | `laboratory`      | `10*9/L`              | Metabolic, Regenerative Capacity       | Yes     |
| Core     | `immune.wbc`                           | White blood cell count              | `laboratory`      | `10*9/L`              | —                                      | Yes     |
| Extended | `immune.eosinophils_abs`               | Absolute eosinophil count           | `laboratory`      | `10*9/L`              | —                                      | No      |
| Extended | `immune.monocytes_abs`                 | Absolute monocyte count             | `laboratory`      | `10*9/L`              | —                                      | No      |
| Extended | `immune.crp`                           | C-reactive protein                  | `laboratory`      | `mg/L`                | —                                      | No      |
| Extended | `immune.esr`                           | Erythrocyte sedimentation rate      | `laboratory`      | `mm/h`                | —                                      | No      |
| Extended | `immune.fibrinogen`                    | Fibrinogen                          | `laboratory`      | `g/L`                 | —                                      | No      |
| Extended | `immune.nlr`                           | Neutrophil-to-lymphocyte ratio      | `derived`         | `1`                   | —                                      | No      |
| Research | `immune.glyca`                         | GlycA                               | `omics`           | `umol/L`              | —                                      | No      |
| Research | `immune.inflammation_proteomics_panel` | Inflammation proteomics panel       | `omics`           | `—`                   | —                                      | No      |
| Research | `immune.il6`                           | Interleukin-6                       | `laboratory`      | `pg/mL`               | —                                      | No      |
| Research | `immune.tnf_alpha`                     | Tumor necrosis factor alpha         | `laboratory`      | `pg/mL`               | —                                      | No      |

### Cardiovascular

| Tier       | Canonical code                  | KPI                                 | Measurement class | Canonical unit (UCUM) | Secondary domains     | Default |
| ---------- | ------------------------------- | ----------------------------------- | ----------------- | --------------------- | --------------------- | ------- |
| Core       | `cardio.apob`                   | Apolipoprotein B                    | `laboratory`      | `g/L`                 | —                     | Yes     |
| Core       | `cardio.diastolic_bp`           | Diastolic blood pressure            | `vital_sign`      | `mm[Hg]`              | —                     | Yes     |
| Core       | `cardio.hdl_c`                  | HDL cholesterol                     | `laboratory`      | `mmol/L`              | —                     | Yes     |
| Core       | `cardio.ldl_c`                  | LDL cholesterol                     | `laboratory`      | `mmol/L`              | —                     | Yes     |
| Core       | `cardio.lpa`                    | Lipoprotein(a)                      | `laboratory`      | `nmol/L`              | —                     | Yes     |
| Core       | `cardio.non_hdl_c`              | Non-HDL cholesterol                 | `derived`         | `mmol/L`              | —                     | Yes     |
| Core       | `cardio.resting_heart_rate`     | Resting heart rate                  | `vital_sign`      | `/min`                | Regenerative Capacity | Yes     |
| Core       | `cardio.systolic_bp`            | Systolic blood pressure             | `vital_sign`      | `mm[Hg]`              | —                     | Yes     |
| Core       | `cardio.total_cholesterol`      | Total cholesterol                   | `laboratory`      | `mmol/L`              | —                     | Yes     |
| Extended   | `cardio.abi`                    | Ankle-brachial index                | `functional_test` | `1`                   | —                     | No      |
| Extended   | `cardio.apoa1`                  | Apolipoprotein A-I                  | `laboratory`      | `g/L`                 | —                     | No      |
| Extended   | `cardio.cf_pwv`                 | Carotid-femoral pulse wave velocity | `functional_test` | `m/s`                 | —                     | No      |
| Extended   | `cardio.cac_score`              | Coronary artery calcium score       | `imaging`         | `{Agatston}`          | —                     | No      |
| Extended   | `cardio.mean_arterial_pressure` | Mean arterial pressure              | `derived`         | `mm[Hg]`              | —                     | No      |
| Extended   | `cardio.pulse_pressure`         | Pulse pressure                      | `derived`         | `mm[Hg]`              | —                     | No      |
| Specialist | `cardio.central_systolic_bp`    | Central systolic blood pressure     | `vital_sign`      | `mm[Hg]`              | —                     | No      |
| Research   | `cardio.coronary_plaque_volume` | Coronary plaque volume              | `imaging`         | `mm3`                 | —                     | No      |

### Neurocognitive

| Tier       | Canonical code                    | KPI                                | Measurement class | Canonical unit (UCUM) | Secondary domains | Default |
| ---------- | --------------------------------- | ---------------------------------- | ----------------- | --------------------- | ----------------- | ------- |
| Core       | `neuro.cognitive_composite_score` | Cognitive battery composite score  | `functional_test` | `{score}`             | —                 | Yes     |
| Core       | `neuro.episodic_memory_score`     | Episodic memory score              | `functional_test` | `{score}`             | —                 | Yes     |
| Core       | `neuro.executive_function_score`  | Executive function score           | `functional_test` | `{score}`             | —                 | Yes     |
| Core       | `neuro.processing_speed_score`    | Processing speed score             | `functional_test` | `{score}`             | —                 | Yes     |
| Extended   | `neuro.attention_score`           | Attention score                    | `functional_test` | `{score}`             | —                 | No      |
| Extended   | `neuro.folate`                    | Folate                             | `laboratory`      | `nmol/L`              | —                 | No      |
| Extended   | `neuro.homocysteine`              | Homocysteine                       | `laboratory`      | `umol/L`              | Cardiovascular    | No      |
| Extended   | `neuro.hearing_pure_tone_average` | Pure-tone hearing average          | `functional_test` | `dB[HL]`              | —                 | No      |
| Extended   | `neuro.reaction_time`             | Reaction time                      | `functional_test` | `ms`                  | —                 | No      |
| Extended   | `neuro.tsh`                       | Thyroid-stimulating hormone        | `laboratory`      | `m[IU]/L`             | —                 | No      |
| Extended   | `neuro.verbal_fluency`            | Verbal fluency                     | `functional_test` | `{words}/min`         | —                 | No      |
| Extended   | `neuro.visual_acuity_logmar`      | Visual acuity                      | `functional_test` | `{logMAR}`            | —                 | No      |
| Extended   | `neuro.vitamin_b12`               | Vitamin B12                        | `laboratory`      | `pmol/L`              | —                 | No      |
| Extended   | `neuro.working_memory_score`      | Working memory score               | `functional_test` | `{score}`             | —                 | No      |
| Specialist | `neuro.abeta42_40_ratio`          | Plasma amyloid beta 42/40 ratio    | `laboratory`      | `1`                   | —                 | No      |
| Specialist | `neuro.ptau181`                   | Plasma phosphorylated tau 181      | `laboratory`      | `pg/mL`               | —                 | No      |
| Specialist | `neuro.ptau217`                   | Plasma phosphorylated tau 217      | `laboratory`      | `pg/mL`               | —                 | No      |
| Research   | `neuro.gfap`                      | Glial fibrillary acidic protein    | `laboratory`      | `pg/mL`               | —                 | No      |
| Research   | `neuro.hippocampal_volume`        | Hippocampal volume                 | `imaging`         | `mL`                  | —                 | No      |
| Research   | `neuro.nfl`                       | Neurofilament light chain          | `laboratory`      | `pg/mL`               | —                 | No      |
| Research   | `neuro.wmh_volume`                | White matter hyperintensity volume | `imaging`         | `mL`                  | —                 | No      |

### Regenerative Capacity

| Tier     | Canonical code                     | KPI                               | Measurement class | Canonical unit (UCUM) | Secondary domains         | Default |
| -------- | ---------------------------------- | --------------------------------- | ----------------- | --------------------- | ------------------------- | ------- |
| Core     | `regen.creatinine`                 | Creatinine                        | `laboratory`      | `umol/L`              | Cardiovascular, Metabolic | Yes     |
| Core     | `regen.egfr_creatinine`            | eGFR, creatinine-based            | `derived`         | `mL/min/{1.73_m2}`    | Cardiovascular, Metabolic | Yes     |
| Core     | `regen.hrv_rmssd`                  | Heart rate variability RMSSD      | `wearable`        | `ms`                  | —                         | Yes     |
| Core     | `regen.hemoglobin`                 | Hemoglobin                        | `laboratory`      | `g/L`                 | —                         | Yes     |
| Core     | `regen.sleep_efficiency`           | Sleep efficiency                  | `derived`         | `%`                   | Neurocognitive            | Yes     |
| Core     | `regen.steps_per_day`              | Steps per day                     | `wearable`        | `{steps}/d`           | —                         | Yes     |
| Core     | `regen.sleep_duration`             | Total sleep time                  | `wearable`        | `min`                 | Neurocognitive            | Yes     |
| Core     | `regen.uacr`                       | Urine albumin-to-creatinine ratio | `laboratory`      | `mg/mmol{creat}`      | Cardiovascular, Metabolic | Yes     |
| Core     | `regen.vo2peak_direct`             | VO₂peak, directly measured        | `functional_test` | `mL/(kg.min)`         | Cardiovascular            | Yes     |
| Extended | `regen.reticulocytes_abs`          | Absolute reticulocyte count       | `laboratory`      | `10*9/L`              | —                         | No      |
| Extended | `regen.cystatin_c`                 | Cystatin C                        | `laboratory`      | `mg/L`                | Cardiovascular            | No      |
| Extended | `regen.egfr_creatinine_cystatin`   | eGFR, creatinine-cystatin C       | `derived`         | `mL/min/{1.73_m2}`    | Cardiovascular            | No      |
| Extended | `regen.heart_rate_recovery_1min`   | Heart rate recovery at 1 minute   | `derived`         | `/min`                | Cardiovascular            | No      |
| Extended | `regen.hrv_sdnn`                   | Heart rate variability SDNN       | `wearable`        | `ms`                  | —                         | No      |
| Extended | `regen.nocturnal_spo2_mean`        | Mean nocturnal oxygen saturation  | `wearable`        | `%`                   | —                         | No      |
| Extended | `regen.mvpa_minutes_per_day`       | Moderate-to-vigorous activity     | `wearable`        | `min/d`               | —                         | No      |
| Extended | `regen.nocturnal_respiratory_rate` | Nocturnal respiratory rate        | `wearable`        | `/min`                | —                         | No      |
| Extended | `regen.sedentary_minutes_per_day`  | Sedentary time                    | `wearable`        | `min/d`               | —                         | No      |
| Extended | `regen.sleep_onset_latency`        | Sleep onset latency               | `wearable`        | `min`                 | Neurocognitive            | No      |
| Extended | `regen.sleep_regularity`           | Sleep regularity index            | `derived`         | `%`                   | Neurocognitive            | No      |
| Extended | `regen.vo2max_estimated`           | VO₂max, estimated                 | `wearable`        | `mL/(kg.min)`         | Cardiovascular            | No      |
| Extended | `regen.waso`                       | Wake after sleep onset            | `wearable`        | `min`                 | Neurocognitive            | No      |

### Musculoskeletal

| Tier       | Canonical code               | KPI                                            | Measurement class  | Canonical unit (UCUM) | Secondary domains                     | Default |
| ---------- | ---------------------------- | ---------------------------------------------- | ------------------ | --------------------- | ------------------------------------- | ------- |
| Core       | `msk.appendicular_lean_mass` | Appendicular lean mass                         | `body_composition` | `kg`                  | —                                     | Yes     |
| Core       | `msk.almi`                   | Appendicular lean mass index                   | `derived`          | `kg/m2`               | —                                     | Yes     |
| Core       | `msk.chair_stand_5_time`     | Five-chair-stand time                          | `functional_test`  | `s`                   | —                                     | Yes     |
| Core       | `msk.grip_strength`          | Grip strength                                  | `functional_test`  | `[kgf]`               | —                                     | Yes     |
| Core       | `msk.gait_speed`             | Usual gait speed                               | `functional_test`  | `m/s`                 | Neurocognitive, Regenerative Capacity | Yes     |
| Extended   | `msk.vitamin_d_25oh`         | 25-hydroxyvitamin D                            | `laboratory`       | `nmol/L`              | —                                     | No      |
| Extended   | `msk.alp`                    | Alkaline phosphatase                           | `laboratory`       | `[IU]/L`              | —                                     | No      |
| Extended   | `msk.calcium`                | Calcium                                        | `laboratory`       | `mmol/L`              | —                                     | No      |
| Extended   | `msk.femoral_neck_bmd`       | Femoral neck bone mineral density              | `imaging`          | `g/cm2`               | —                                     | No      |
| Extended   | `msk.femoral_neck_t_score`   | Femoral neck T-score                           | `imaging`          | `{T-score}`           | —                                     | No      |
| Extended   | `msk.lumbar_spine_bmd`       | Lumbar spine bone mineral density              | `imaging`          | `g/cm2`               | —                                     | No      |
| Extended   | `msk.lumbar_spine_t_score`   | Lumbar spine T-score                           | `imaging`          | `{T-score}`           | —                                     | No      |
| Extended   | `msk.pth`                    | Parathyroid hormone                            | `laboratory`       | `pmol/L`              | —                                     | No      |
| Extended   | `msk.phosphate`              | Phosphate                                      | `laboratory`       | `mmol/L`              | —                                     | No      |
| Extended   | `msk.sppb_total`             | Short Physical Performance Battery total score | `functional_test`  | `{score}`             | —                                     | No      |
| Extended   | `msk.single_leg_stance`      | Single-leg stance time                         | `functional_test`  | `s`                   | —                                     | No      |
| Extended   | `msk.six_min_walk_distance`  | Six-minute walk distance                       | `functional_test`  | `m`                   | Cardiovascular, Regenerative Capacity | No      |
| Extended   | `msk.timed_up_and_go`        | Timed Up and Go                                | `functional_test`  | `s`                   | —                                     | No      |
| Extended   | `msk.total_hip_bmd`          | Total hip bone mineral density                 | `imaging`          | `g/cm2`               | —                                     | No      |
| Extended   | `msk.total_hip_t_score`      | Total hip T-score                              | `imaging`          | `{T-score}`           | —                                     | No      |
| Extended   | `msk.total_lean_mass`        | Total lean mass                                | `body_composition` | `kg`                  | —                                     | No      |
| Specialist | `msk.ctx`                    | C-terminal telopeptide of type I collagen      | `laboratory`       | `ng/L`                | —                                     | No      |
| Specialist | `msk.p1np`                   | Procollagen type I N-terminal propeptide       | `laboratory`       | `ug/L`                | —                                     | No      |

## 8. Required provenance by measurement class

| Measurement class  | Minimum required provenance                                                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `laboratory`       | specimen, collection time, laboratory, assay/method, instrument where available, original unit, source reference interval, fasting/challenge context where relevant |
| `vital_sign`       | device model, cuff/sensor details, body position, rest period, anatomical site, protocol, timestamp                                                                 |
| `anthropometric`   | device, clothing/fasting convention where relevant, anatomical landmark, operator/protocol, timestamp                                                               |
| `body_composition` | modality, device/scanner model, software version, calibration, positioning, region-of-interest protocol                                                             |
| `functional_test`  | instrument/test name, version, language where applicable, protocol, operator, attempts, completion/termination reason                                               |
| `wearable`         | vendor, model, firmware, algorithm version, wear interval, valid-data percentage, aggregation window                                                                |
| `imaging`          | modality, scanner, acquisition protocol, software/segmentation version, quality statement, source report/DICOM reference                                            |
| `derived`          | formula ID/version and immutable input Observation IDs                                                                                                              |
| `omics`            | platform, assay/panel version, sample type, batch, normalization pipeline and quality-control metadata                                                              |

## 9. Normalization behavior

1. Prefer a **verified external code** with matching context.
2. Otherwise resolve an exact source-system alias.
3. Otherwise resolve an unambiguous global alias.
4. Validate value kind and source unit.
5. Convert only through the separately approved, versioned conversion registry.
6. Store original value/unit and normalized value/unit.
7. Route ambiguous aliases, unsupported units, method conflicts and missing required context to review.
8. Never infer fasting status, specimen, method, device, instrument or protocol.
9. Never merge:

- generic CRP with hs-CRP;
- directly measured VO₂peak with estimated wearable VO₂max;
- Lp(a) `mg/dL` with `nmol/L` through a fixed conversion;
- cognitive scores across different instruments or versions;
- DXA/BIA body-composition values across undocumented device or software changes.

## 10. Derived KPI rules

Derived KPI rows are definitions only. Computation belongs to a versioned formula registry and
creates a new derived Observation with `derived_from` links.

Minimum formula IDs in this release:

```text
bmi.v1
waist_height_ratio.v1
fib4.v1
cgm_glucose_cv.v1
homa_ir.v1
nlr.v1
pulse_pressure.v1
map.v1
non_hdl_c.v1
heart_rate_recovery_1min.v1
sleep_efficiency.v1
sleep_regularity.v1
egfr_creatinine.ckd_epi_2021.v1
egfr_creatinine_cystatin.ckd_epi_2021.v1
almi.v1
```

No formula executes automatically merely because its KPI exists in the catalog. Computation requires
explicitly validated source Observations and a controlled job or clinician-authorized workflow.

## 11. Verified external-code starter set

The production migration should seed only mappings that have been verified against the current
terminology release. The included starter file contains:

| HADP KPI              | System | External code | Context                               |
| --------------------- | ------ | ------------- | ------------------------------------- |
| `metabolic.hba1c`     | LOINC  | `4548-4`      | HbA1c, NGSP-aligned reporting         |
| `metabolic.hba1c`     | LOINC  | `59261-8`     | HbA1c, IFCC protocol                  |
| `immune.hs_crp`       | LOINC  | `30522-7`     | Serum/plasma, high-sensitivity method |
| `cardio.apob`         | LOINC  | `1884-6`      | Serum/plasma mass concentration       |
| `cardio.systolic_bp`  | LOINC  | `8480-6`      | Systolic blood pressure               |
| `cardio.diastolic_bp` | LOINC  | `8462-4`      | Diastolic blood pressure              |
| `cardio.lpa`          | LOINC  | `43583-4`     | Serum/plasma substance concentration  |

All other LOINC mappings remain `pending` until separately verified. Never copy unverified codes
from a prototype seed into production.

## 12. Explicitly blocked production KPI concepts

Do not seed these as active production KPIs:

```text
unified_healthspan_score
biological_age_score
epigenetic_age_years_younger
aging_reversal_score
telomere_age
nad_plus_score
vendor_readiness_score
vendor_sleep_score_without_algorithm_identity
ai_confidence_percent_for_clinical_truth
```

A research protocol may later introduce a narrowly defined raw observation with its actual assay or
algorithm provenance. It must not be renamed into an age-reversal or Healthspan claim.

## 13. Migration and application plan

### Migration

1. Create the closed enums.
2. Create `kpi_catalog_release`, `kpi_catalog`, `kpi_alias`,
   `kpi_external_code` and `kpi_secondary_domain`.
3. Do **not** add any table to `TENANT_TABLES`.
4. Grant `SELECT` only to `hadp_app`.
5. Seed `kpi-cat-2.0.0` from `kpi_catalog_v2.json`.
6. Seed aliases and verified external codes.
7. Add checks:

- derived rows require `formula_id`;
- non-derived rows must not have `formula_id`;
- panel rows have a null canonical unit;
- specialist/research rows have `patient_visible=false`;
- secondary domain cannot equal primary domain.

8. Migration downgrade removes grants, rows, tables and enums in reverse dependency order.

### Normalizer

- Replace `_TERMINOLOGY` with a cached catalog repository.
- Use external-code context first, aliases second.
- Return `kpi_code`, primary domain, canonical unit, mapping source and mapping confidence.
- Keep the approved conversion registry separate.
- Route alias collisions and unsupported units to review.
- Remove `_MARKERS_BY_AXIS`; seed/demo code reads the same catalog source.

### Dashboard API

Return observed KPIs grouped by primary domain with optional secondary-domain links. Do not return
empty KPIs as normal results. Missing means `not_observed`, never `stable`.

## 14. Required tests

### Schema and security

- catalog tables are readable with no tenant bound;
- `hadp_app` cannot INSERT, UPDATE or DELETE;
- all vocabularies reject unknown values;
- a KPI has exactly one primary domain;
- a secondary domain cannot equal the primary domain;
- derived/formula and panel/unit checks hold;
- no range or target columns exist.

### Seed integrity

- exactly 120 active KPI rows are loaded;
- exactly 43 are Core/default-enabled;
- canonical codes are unique;
- aliases are unique within namespace;
- all canonical units are valid against the approved UCUM allowlist;
- all six domains are represented;
- all Specialist/Research KPIs are patient-hidden;
- blocked concepts are absent.

### Import behavior

- every canonical code imports without `unmapped_metric`;
- every seeded alias resolves deterministically;
- unknown aliases route to review;
- ambiguous aliases fail closed;
- generic CRP never maps to hs-CRP;
- direct VO₂peak never maps to estimated VO₂max;
- Lp(a) mass/molar conversion is blocked;
- cognitive scores with different instrument versions are not merged;
- imaging and body-composition device/software changes create a comparability warning;
- derived Observations retain formula version and input IDs.

## 15. Acceptance criteria

This ADR is complete when:

- the migration and seed are reproducible from the provided JSON;
- live normalization and demo seeding use the same catalog repository;
- no hardcoded KPI dictionaries remain;
- the six-domain dashboard renders only observed KPIs;
- cross-domain links do not duplicate Observations;
- provenance and review gates remain intact;
- no catalog field or UI copy introduces a target range, diagnosis, recommendation, unified score
  or biological-age claim.

## 16. Reference basis

The KPI set is intentionally conservative and separates established routine measurements,
functional measures, specialist markers and research-only observations. Implementation should
re-verify external terminology mappings against the current releases before real-data use.

- [HL7 FHIR Observation](https://fhir.hl7.org/fhir/observation-definitions.html) and
  [Provenance](https://fhir.hl7.org/fhir/provenance.html): device, specimen, method and lineage
  belong to the Observation/provenance layer.
- [LOINC mapping guidance](https://loinc.org/kb/users-guide/recommendations-for-best-practices-in-using-and-mapping-to-loinc/)
  and [LOINC term structure](https://loinc.org/kb/users-guide/major-parts-of-a-loinc-term/):
  specimen, property and method can distinguish different observations of the same apparent analyte.
- [UCUM specification](https://ucum.org/ucum): canonical machine-readable units.
- [ADA Standards of Care 2026 — Diagnosis and Classification](https://diabetesjournals.org/care/article/49/Supplement_1/S27/163926/2-Diagnosis-and-Classification-of-Diabetes):
  HbA1c, fasting plasma glucose and OGTT measurement pathways.
- [2026 ACC/AHA Dyslipidemia Guideline](https://professional.heart.org/en/science-news/2026-guideline-on-the-management-of-dyslipidemia):
  standard lipids, ApoB and Lp(a) context.
- [KDIGO 2024 CKD Guideline](https://kdigo.org/guidelines/ckd-evaluation-and-management/):
  eGFR and albuminuria/UACR.
- [EWGSOP2](https://academic.oup.com/ageing/article/48/1/16/5126243): grip strength, chair stand,
  appendicular lean mass and physical performance.
- [WHO ICOPE](https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/ageing-and-health/integrated-care-for-older-people-icope):
  functional capacity domains, including cognition and locomotion.
- [Alzheimer's Association 2025 blood-biomarker guideline](https://aaic.alz.org/releases-2025/clinical-practice-guideline-blood-based-biomarkers.asp):
  blood-based Alzheimer biomarkers remain specialist-context measurements for people with cognitive
  impairment.
- [CDC hs-CRP laboratory documentation](https://wwwn.cdc.gov/nchs/data/nhanes/public/2021/labmethods/HSCRP-L-MET-508.pdf):
  hs-CRP is sensitive but non-specific and method/context matter.

## 17. Out of scope

- any unified or biological-age score;
