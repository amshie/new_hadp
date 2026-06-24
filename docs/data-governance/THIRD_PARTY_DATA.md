# Third-Party & Research Data

This document governs every external, public, or research dataset that enters or
touches the Longevity Health Analytics Platform — for synthetic-fixture
generation, offline analytics experiments, or an investor/demo context. It is the
`docs/data-governance/THIRD_PARTY_DATA.md` register required by the project
contract (`CLAUDE.md`, "Data-source governance").

Public and research datasets are **not** the commercial data moat. Long-term
defensibility comes from consented longitudinal data partnerships with clinics and
laboratories, not from repackaging public datasets. These sources are auxiliary
and must never be mixed casually with clinical patient data.

> This document is engineering and governance guidance. It is **not** legal or
> regulatory advice. Dataset license terms, Data Use Agreements (DUAs), and
> permitted-use determinations are owned by qualified counsel and the data
> protection officer, not by this file.

---

## Scope

Applies to any dataset originating outside a pilot clinic or laboratory feed,
including but not limited to: public health surveys, longitudinal aging studies,
ICU/clinical research corpora, reference-range or terminology reference data, and
any model or notebook trained or evaluated on such data.

It does **not** apply to:

- Synthetic data produced by the platform's own generator (every synthetic
  `Tenant` / `User` / `Patient` / `SourceDocument` carries `is_synthetic`).
- Real patient and laboratory data received through a pilot clinic under an
  Art. 28 DPA — that data is governed by the privacy, consent, and tenant-isolation
  controls described in `CLAUDE.md` and the security/regulatory docs.

---

## Rules (binding)

1. **No raw datasets in Git.** Downloaded raw datasets are never committed to the
   repository — not to fixtures, not to `tests/`, not to issues, not to branches.
   Reference them by source, version, and access location in the inventory below.
2. **No commercial use unless the terms explicitly allow it.** A dataset is used
   commercially only when its license or DUA explicitly permits the intended
   commercial use. Ambiguous terms are treated as not permitted until counsel
   confirms otherwise.
3. **Restricted datasets stay in a separate approved environment.** Datasets under
   a DUA or other access restriction (e.g. credentialed access) remain in an
   isolated, approved environment and never enter the clinical application, its
   database, its object storage, or its backups.
4. **Never attempt re-identification.** Re-identification of any individual in any
   third-party dataset is prohibited, including linkage attacks across datasets.
5. **Demo fixtures are synthetic or demonstrably permitted + de-identified.** Any
   fixture shown in a demo is either synthetic data from the platform generator or
   data whose license/DUA demonstrably permits that use and which is
   de-identified. Parser and test fixtures contain no real patient data.
6. **Research models are not production clinical features.** Models, notebooks, or
   analyses built on research datasets are not exposed as production clinical
   features without separate validation, clinical review, privacy review, and a
   regulatory classification review. A research-only prototype remains isolated
   from the clinical application (`CLAUDE.md`, "Prohibited MVP behavior" and
   "Regulatory classification and governance").
7. **No mixing with patient data.** Third-party data is never co-located with, or
   joined to, real patient data in clinical storage.
8. **Intended-use boundary still applies.** No third-party dataset is used to
   build a biological-age score, disease-risk score, "optimal" reference range, or
   any other feature on the prohibited list. Such work would change the device
   classification and is blocked pending the documented review process.
9. **Register before use.** A dataset is added to the inventory below — with an
   assigned access owner and recorded permitted use — _before_ it is downloaded or
   used. An unregistered dataset is not approved.

---

## Inventory

No third-party or research datasets are currently in use. The platform operates on
synthetic data only.

| Source        | Version | Purpose | License / DUA | Access owner | Permitted use | Retention | Redistribution |
| ------------- | ------- | ------- | ------------- | ------------ | ------------- | --------- | -------------- |
| _none in use_ | —       | —       | —             | —            | —             | —         | —              |

When a dataset is adopted, add a row capturing every column above, assign an access
owner, and record the license/DUA reference. Restricted entries must also name the
separate approved environment in which the data resides.

---

## Candidate public sources (not yet used)

The following are candidate sources for synthetic-example design, offline analytics
experiments, or demo material. **None are in use.** Each requires its access terms
to be read and recorded in the inventory before any download, and each carries the
rules above. Access terms vary by dataset and several are restricted/credentialed.

- **NHANES** — US national health and nutrition survey data.
- **SHARE** — Survey of Health, Ageing and Retirement in Europe.
- **HRS** — Health and Retirement Study.
- **NACDA** — National Archive of Computerized Data on Aging resources.
- **Gateway to Global Aging Data** — harmonized cross-national aging study data.
- **MIMIC-IV** — restricted/credentialed ICU clinical research corpus (requires a
  DUA and credentialed access; if adopted it is a restricted dataset and must stay
  in a separate approved environment).

Listing a source here is not approval to use it. Adoption requires registration in
the inventory, an assigned access owner, recorded permitted use, and — for any
clinical-meaning or production exposure — the separate validation and review gates
named in rule 6.

---

## Review cadence

- Review this register before adopting any new dataset and whenever a dataset's
  license/DUA or intended use changes.
- The access owner named in each inventory row is responsible for keeping that
  row's terms, retention, and environment accurate.
- Re-confirm that no entry has drifted into the clinical application, its
  database/object storage, or its backups.
