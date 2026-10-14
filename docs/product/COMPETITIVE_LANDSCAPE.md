# Competitive landscape — ten platforms beside HADP

Status: research note, 2026-10-14. What ten companies in and around HADP's field advertise, what
HADP has today, and the ten features they have that HADP does not — each sorted into
"in scope", "gated by the doctrine" or "deliberately not".

**Method and its limit.** The feature claims come from the vendors' own sites, app-store
listings, help centres and launch press as summarised by web search on the date above;
the sites were not opened directly from this environment, and nothing was tried as a
customer. A claim here is what a vendor says, not what was verified. Pricing is left out
where sources disagreed. Synthetic-data-only applies to HADP, not to any of them.

## The ten

| #   | Company                              | Where        | Who it sells to                       | What it is                                                                                                 |
| --- | ------------------------------------ | ------------ | ------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1   | **Heads Up Health**                  | US           | clinics, practitioners                | the closest analogue: labs + wearables + EHR data in one practitioner dashboard, white-label               |
| 2   | **Longevitix** (launched 2026-06)    | US           | longevity / concierge / DPC clinics   | "clinical intelligence": labs, wearables, notes, intake → physician summaries, plans, patient reports      |
| 3   | **Fullscript Labs** (ex-Rupa Health) | US / CA      | functional-medicine practitioners     | lab ordering + results with interpretations, optimal ranges, trends, supplements                           |
| 4   | **Healthie**                         | US           | longevity and integrative practices   | an EHR for longevity care: member portal, labs, wearables, billing, API/SDK                                |
| 5   | **Sonar Health** (Atlas)             | AU / UK / EU | coaches, practices                    | practice-level dashboard over 600+ wearables and apps, labs, nutrition, training                           |
| 6   | **Junction** (ex-Vital)              | US / EU      | developers, health products           | API: 300+ wearables, lab ordering through results, US/EU data region                                       |
| 7   | **Function Health**                  | US           | consumers (members)                   | 100+ biomarkers a year, clinician notes, biological age, AI chat, MRI and cancer screening add-ons         |
| 8   | **InsideTracker**                    | US           | consumers                             | optimal zones per person, InnerAge, action plan, wearables, DNA                                            |
| 9   | **Superpower**                       | US           | consumers                             | 100+ biomarkers, 17 body-system scores, biological age, concierge physician team, AI advisor               |
| 10  | **Aware**                            | DE / AT / NL | consumers (B2C and B2B subscriptions) | blood test in 25+ cities, app with explanations and lifestyle advice, doctor booking, upload of old values |

Watched but thin evidence, DACH: **care** (CH: physician-reviewed checks, app with value history,
now via partner practices, pharmacies and labs), **NOA Health** (DE: 100+ values, physicians
validate and explain by telemedicine), **YEARS** (Berlin clinic, 230 lab parameters),
**medicalvalues** (DE: explainable decision support for labs and practices, HL7/FHIR/LIS
interfaces, configurable reference ranges). **Terra** ships a reference app (Terra Panel) whose
Lab Reports API turns a lab PDF into biomarkers with ranges, flags and provenance.

## What HADP has that most of them do not

Worth saying first, because it is the positioning:

- A **physician-governed interpretation** as the core artifact: per domain, one clinical-significance
  verdict and one actionability verdict from closed vocabularies, authored by a clinician, locked by
  a medical director, append-only. None of the ten has a governance object like it; they have
  "insights", "plans" or "scores".
- **Provenance to the source value**: original name, value, unit and reference text kept verbatim
  beside the normalised value; corrections supersede, never overwrite. Only Terra's reference app
  and medicalvalues talk about provenance at all.
- **Tenant isolation at the database** (row-level security), an **append-only audit trail** the
  clinic can read, tested log redaction, consent versioning, four-eyes erasure, GDPR export. The
  consumer products do not need this; the practitioner platforms do not advertise it.
- **DACH-native data path**: LDT 2 and LDT 3 readers, German first, EU hosting.

## Feature matrix

✓ advertised · ◐ partial · – not advertised · ✗ excluded by HADP's doctrine or scope

| Feature                                             | Heads Up | Longevitix | Fullscript | Healthie | Sonar | Junction | Function | InsideTracker | Superpower | Aware | **HADP** |
| --------------------------------------------------- | :------: | :--------: | :--------: | :------: | :---: | :------: | :------: | :-----------: | :--------: | :---: | :------: |
| Lab results, longitudinal trends                    |    ✓     |     ✓      |     ✓      |    ◐     |   ✓   |    ✓     |    ✓     |       ✓       |     ✓      |   ◐   |    ✓     |
| Source reference intervals shown                    |    ✓     |     ?      |     ✓      |    ?     |   ?   |    ✓     |    ✓     |       ✓       |     ✓      |   ✓   |    ✓     |
| Structured lab feeds (HL7 / LDT / API)              |    ✓     |     ?      |     ✓      |    ✓     |   –   |    ✓     |    ✓     |       ✓       |     ✓      |   –   |    ✓     |
| Lab PDF ingestion                                   |    ✓     |     ?      |     –      |    –     |   –   |    ✓     |    –     |       –       |     –      |   ◐   |    –     |
| Lab **ordering** from the platform                  |    –     |     –      |     ✓      |    ✓     |   –   |    ✓     |    ✓     |       ✓       |     ✓      |   ✓   |    –     |
| Wearables / devices                                 |    ✓     |     ✓      |     –      |    ✓     |   ✓   |    ✓     |    –     |       ✓       |     –      |   –   |    –     |
| Intake forms, history, lifestyle data               |    ✓     |     ✓      |     –      |    ✓     |   ✓   |    –     |    ◐     |       ✓       |     ◐      |   ◐   |    –     |
| Practice-level view (who deviated, stale data)      |    ✓     |     ◐      |     –      |    –     |   ✓   |    –     |    –     |       –       |     –      |   –   |    ◐     |
| Alerts / notifications (results, deviation)         |    ✓     |     ?      |     ✓      |    ✓     |   ✓   |    ✓     |    ✓     |       ✓       |     ✓      |   ✓   |   ◐ ⁴    |
| Configurable reference ranges / protocols           |    ✓     |     ✓      |     ✓      |    –     |   –   |    –     |    –     |       ✓       |     –      |   –   |   ✗ ¹    |
| "Optimal" zones, body-system scores, biological age |    –     |     ?      |     ✓      |    –     |   –   |    –     |    ✓     |       ✓       |     ✓      |   –   |    ✗     |
| AI summary / chat over the patient's data           |    –     |     ✓      |     –      |    ◐     |   ✓   |    –     |    ✓     |       –       |     ✓      |   –   |   ✗ ²    |
| Plans / recommendations / supplements               |    –     |     ✓      |     ✓      |    ✓     |   –   |    –     |    ✓     |       ✓       |     ✓      |   ✓   |    ✗     |
| Clinician review before the patient sees it         |    ◐     |     ◐      |     ✓      |    ◐     |   –   |    –     |    ✓     |       –       |     ◐      |   ◐   |    ✓     |
| Patient app / portal (trends, explanations)         |    ✓     |     ✓      |     ✓      |    ✓     |   –   |    –     |    ✓     |       ✓       |     ✓      |   ✓   |    ◐     |
| Patient ↔ clinic messaging                         |    ✓     |     ?      |     –      |    ✓     |   –   |    –     |    ✓     |       –       |     ✓      |   –   |    –     |
| Branded / white-label patient report, PDF           |    ✓     |     ✓      |     ◐      |    ✓     |   –   |    –     |    –     |       –       |     –      |   –   |    ◐     |
| EHR / practice-system integration or export         |    ✓     |     ✓      |     ✓      |    ✓     |   –   |    ✓     |    –     |       –       |     –      |   –   |    –     |
| Public API / SDK                                    |    ◐     |     –      |     –      |    ✓     |   –   |    ✓     |   ◐ ³    |       –       |     –      |   –   |    –     |
| Interventions tracked against later values          |    –     |     ✓      |     ◐      |    ◐     |   ✓   |    –     |    ◐     |       ✓       |     ◐      |   –   |    –     |
| Governed interpretation object, append-only         |    –     |     –      |     –      |    –     |   –   |    –     |    –     |       –       |     –      |   –   |    ✓     |
| Audit trail readable by the clinic                  |    –     |     –      |     –      |    –     |   –   |    –     |    –     |       –       |     –      |   –   |    ✓     |
| Consent versioning, erasure, GDPR export            |    –     |     –      |     –      |    –     |   –   |    –     |    –     |       –       |     –      |   ◐   |    ✓     |
| EU data residency                                   |    –     |     –      |     –      |    –     |   ◐   |    ✓     |    –     |       –       |     –      |   ✓   |    ✓     |

¹ Clinic-configured _rules_ ("configured clinic threshold", "rule match") are allowed by CLAUDE.md;
replacing the laboratory's interval with an undocumented "optimal" one is not. ² AI as a constrained
drafting component over verified facts is allowed by CLAUDE.md's AI contract; AI that derives a
verdict, a score or a recommendation is not. ³ Function exposes member data to AI assistants
through connectors (Claude, Perplexity), not an API for clinics. ⁴ In-app only: the overview names
the records in which something arrived or moved since the person last opened them
(`docs/notes/0024`); e-mail and push wait for a mail provider inside the EU residency constraint.

## The ten features they have and HADP does not — ranked

Ranked by value to a DACH clinic pilot, with the doctrine's answer to each.

| #   | Gap                                                                | Who has it                                                               | Doctrine                   | Shape of the HADP version                                                                                                                                                                                                                                                          | Effort            |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------------ | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 1   | **Wearables and devices**                                          | 6 of 10 (Heads Up, Longevitix, Healthie, Sonar, Junction, InsideTracker) | in scope (Phase 2)         | one provider behind an interface, as planned; values are observations with source and provenance like a lab value, never a score. Junction or Terra as the aggregator keeps it one integration                                                                                     | 2–3 weeks         |
| 2   | **Lab feeds that arrive by themselves, and PDF as the fallback**   | all practitioner platforms                                               | in scope                   | a lab-side push (LDT/HL7 from the Laborgemeinschaft or LIS) so staff upload nothing; one pilot lab's PDF layout as the documented fallback; a Terra-style standardisation step would be bought, not built                                                                          | 2 weeks + per lab |
| 3   | **Notifications**                                                  | 9 of 10                                                                  | in scope                   | e-mail (later push) for: new values arrived, a run waits for the director, a report was released; nothing clinical in the message body; deterministic, audited                                                                                                                     | 1 week            |
| 4   | **A patient portal that is more than one page**                    | 8 of 10                                                                  | in scope, gated            | the patient sees approved reports _and_ the approved values over time with the source interval and the clinic's wording, in their language; explanations are the clinic's, never generated; no values before release                                                               | 2 weeks           |
| 5   | **Practice-level view: who changed, what went stale, who stopped** | Heads Up, Sonar, (Longevitix)                                            | in scope, gated            | deterministic facts across the clinic's patients: new values since last run, values outside the source interval, data older than N days, no interpretation yet. Ordered by workflow, never by "urgency"                                                                            | 1 week            |
| 6   | **Clinic-configured rules on top of the source interval**          | Heads Up, Longevitix, Fullscript, InsideTracker                          | gated: register row        | a clinic threshold per marker, versioned, with who set it and why, shown as "Praxisregel" beside the source interval, never instead of it; CLAUDE.md's rules engine (Milestone 2), still unbuilt                                                                                   | 1–2 weeks         |
| 7   | **A pre-visit summary**                                            | Longevitix, Sonar, Function, Terra                                       | gated: deterministic first | "since the last interpretation": which values are new, which moved outside their interval, which are stale, which domains have no verdict — generated from facts with evidence links. An AI narrative over it only under the AI contract (evidence IDs, fake provider, validation) | 1 week; AI later  |
| 8   | **Export into the practice system, and a branded PDF**             | Heads Up, Longevitix, Fullscript, Healthie                               | in scope                   | PDF of the released report with the clinic's name and address (already shown on screen); GDT/LDT export of the released report and values for medatixx/CGM-class systems; FHIR later                                                                                               | 1–2 weeks         |
| 9   | **Structured intake: history, medication, lifestyle**              | Heads Up, Longevitix, Healthie, Sonar, InsideTracker                     | in scope, gated            | a clinician-entered, versioned anamnesis and lifestyle record the interpretation can cite as evidence; closed vocabularies where they exist; no derivation from it                                                                                                                 | 2 weeks           |
| 10  | **Interventions and goals tracked against later values**           | Longevitix, Sonar, InsideTracker                                         | gated: register row        | a clinician-authored "Maßnahme" with a date, linked to the run; later values are shown beside it; adherence is recorded by the clinic, nothing is inferred                                                                                                                         | 1–2 weeks         |

Also missing, lower value for a pilot: a partner API with keys and scopes (Healthie, Junction);
patient ↔ clinic messaging (Heads Up, Healthie, Function); a mobile app (excluded for the pilot
by CLAUDE.md).

## Where they go and HADP deliberately does not

These are the features that define the consumer products and some practitioner ones, and that
HADP's doctrine, intended use and MDR position exclude. They are not gaps; they are the line.

- **Scores and ages**: body-system scores (Superpower), biological age (Function, Superpower,
  InsideTracker's InnerAge). ADR-0003: no unified score, no percentage, no biological age.
- **"Optimal" ranges** that replace the laboratory's interval (InsideTracker, Fullscript's medical
  advisory ranges). CLAUDE.md prohibits undocumented optimal ranges; a documented clinic rule
  beside the source interval is the allowed form (gap 6).
- **Recommendations, plans and supplements** (Function's protocols, InsideTracker's action plan,
  Fullscript's and Superpower's supplement tie-ins, Longevitix's intervention plans). Prohibited
  as product output; a clinician's own recorded measure is the allowed form (gap 10).
- **AI that interprets** (Longevitix's "15 organ-system AI specialists", Function's chat,
  Superpower's advisor). The engine validates and records; it never derives. AI may draft over
  verified facts with evidence IDs, nothing more.
- **Imaging, DNA, cancer screening add-ons** (Function's MRI and Galleri, InsideTracker's DNA).
  Out of scope.

Said to a clinic or an investor: every one of the ten sells _conclusions_; HADP sells the
_governed record of the physician's own conclusion_, with the data path and the audit to defend
it. That is narrower, and it is the reason the MDR question is open rather than answered against
us.

## What this changes in the plan

Nothing in the agreed order: production sign-in, worker, monitoring stay first once a clinic or
funding exists. Of the ten gaps, three fit before a pilot and are cheap: **notifications (3)**,
the **practice-level facts view (5)** and the **pre-visit summary (7)** — together about three
weeks, all deterministic, all inside the doctrine. **Wearables (1)** and **lab feeds (2)** are
the Phase 2 the plan already names; the lab push is the one to negotiate with the pilot
laboratory now, since it is procurement more than code.

## Sources

Vendor sites, listings and press as summarised on 2026-10-14; none opened directly.

- Heads Up: [longevity platform](https://headsuphealth.com/longevity-platform/), [App Store listing](https://apps.apple.com/app/id1399133678), [Elation partner page](https://partners.elationhealth.com/partners/heads-up-health), [vendor profile](https://outliyr.com/headsuphealth)
- Longevitix: [launch release, GlobeNewswire 2026-06-08](https://www.globenewswire.com/news-release/2026/06/08/3308080/0/en/longevitix-launches-clinical-intelligence-platform-for-preventive-and-longevity-medicine.html), [Longevity.Technology](https://longevity.technology/news/longevitix-launches-ai-platform-to-tackle-longevity-data-overload/)
- Fullscript Labs: [lab interpretations](https://fullscript.com/lab-interpretations), [interpretations and trends, help centre](https://support.fullscript.com/articles/lab-interpretations-and-trends), [Rupa migration](https://fullscript.com/lp/rupa-move)
- Healthie: [longevity care EHR](https://www.gethealthie.com/plus/longevity-care-ehr)
- Sonar Health: [longevity dashboard for your practice](https://www.sonarhealth.co/blog/longevity-dashboard-for-your-practice/)
- Junction: [docs](https://docs.junction.com/lab/overview/introduction), [TechCrunch, 2025-03](https://techcrunch.com/2025/03/11/junction-an-api-to-link-health-wearables-with-labs-raises-18m)
- Function Health: [Claude integration, Longevity.Technology](https://longevity.technology/news/function-health-launches-claude-integration-to-enhance-ai-powered-health-insights/), [Fierce Healthcare](https://www.fiercehealthcare.com/health-tech/function-health-lands-298m-series-b-rolls-out-medical-intelligence-ai-model-health-data), [review](https://crowncounseling.com/reviews/function-health-review/)
- InsideTracker: [membership benefits](https://blog.insidetracker.com/insidetracker-membership-benefits), [InnerAge vs optimal zones](https://blog.insidetracker.com/optimal-zones-versus-innerage)
- Superpower: [vs InsideTracker](https://superpower.com/biomarker-testing-companies/insidetracker), [review](https://crowncounseling.com/reviews/superpower-health-review/)
- Aware: [nextpit test (DE)](https://www.nextpit.de/tests/blut-app-im-test-besser-als-der-arztbesuch), [Sifted](https://sifted.eu/articles/aware-amsterdam-lakestar-healthtech-news), [YEARS vs Aware](https://www.years.co/de/blog/aware-vs-years-vergleich)
- care: [App Store (DE)](https://apps.apple.com/de/app/care/id6443989606), [Horizont](https://www.horizont.net/schweiz/nachrichten/gesundheitspraevention-per-app-care-nutzt-partnerschaften-zur-geschaeftserweiterung-225796)
- medicalvalues: [platform](https://medicalvalues.de/?p=238), [diagnostic intelligence](https://medicalvalues.de/diagnostic-intelligence)
- Terra Panel: [example app](https://tryterra.co/examples/terra-panel), [docs](https://docs.tryterra.co/developer-tools/example-apps/terra-panel)
- Longevitix / Reya and market context: [agetechworld](https://agetechworld.co.uk/news/longevitix-launches-clinical-intelligence-platform-for-preventive-and-longevity-medicine-smart26/), [Reya.ai, Longevity.Technology](https://longevity.technology/clinics/reya-ai-powers-next-gen-longevity-clinics-with-ai/)
