import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { byCount, fill } from "../src/lib/i18n/fill";
import { de } from "../src/lib/i18n/messages/de";
import { en } from "../src/lib/i18n/messages/en";

// The helper that puts a value into a sentence of either language (apps/web/src/lib/i18n).
// No browser: this runner is the one the web app has.

test("a value goes where the wording names it, and nowhere else", () => {
  expect(fill("Zeige {shown} von {total}", { shown: 3, total: 12 })).toBe(
    "Zeige 3 von 12",
  );
  expect(fill("{n} of {n}", { n: 0 })).toBe("0 of 0");
  expect(fill("no place at all", { n: 1 })).toBe("no place at all");

  // A place the values do not hold is left as written — visible, not silently empty. That
  // goes for a name every object has, too.
  expect(fill("Hello {name}", {})).toBe("Hello {name}");
  expect(fill("x {constructor} {toString} y", {})).toBe(
    "x {constructor} {toString} y",
  );

  // A value is text: what looks like a place or a replacement pattern in it stays as it is.
  expect(
    fill("Open patient {name}, {ref}", { name: "{ref} $& $1", ref: "SYN-1" }),
  ).toBe("Open patient {ref} $& $1, SYN-1");
});

test("one wording for a count of one, another for every other count", () => {
  const wording = { one: "{n} patient", other: "{n} patients" };
  expect(byCount(wording, 0)).toBe("0 patients");
  expect(byCount(wording, 1)).toBe("1 patient");
  expect(byCount(wording, 2)).toBe("2 patients");
});

// The two dictionaries have the same keys (the compiler holds that). The places of a sentence
// it cannot see: an English sentence that lost its "{n}" compiles, and shows a bare sentence.
test("a sentence names the same places in both languages", () => {
  const places = (wording: unknown, path = ""): Record<string, string[]> =>
    typeof wording === "string"
      ? {
          [path]: [...wording.matchAll(/\{(\w+)\}/g)]
            .map((m) => m[1] ?? "")
            .sort(),
        }
      : Object.assign(
          {},
          ...Object.entries(wording as Record<string, unknown>).map(
            ([key, value]) => places(value, path ? `${path}.${key}` : key),
          ),
        );
  expect(places(en)).toEqual(places(de));
});

// German is what a device without a choice gets: the sentences the dialog to add a patient
// puts together read as they did before they were split into wording and values.
test("the German of the dialog to add a patient, put together", () => {
  const t = de.addPatient;
  expect(fill(t.stepLabel, { n: 1, label: t.stepNames.identity })).toBe(
    "1. Identität",
  );
  expect(fill(t.stepDone, { n: 2, label: t.stepNames.consent })).toBe(
    "2. Einwilligung – abgeschlossen",
  );
  expect(fill(t.done.summary, { consents: byCount(t.done.consents, 1) })).toBe(
    "· synthetischer Demodatensatz · 1 Einwilligung dokumentiert.",
  );
  expect(fill(t.done.summary, { consents: byCount(t.done.consents, 2) })).toBe(
    "· synthetischer Demodatensatz · 2 Einwilligungen dokumentiert.",
  );
  expect(fill(t.done.summary, { consents: t.done.noConsents })).toBe(
    "· synthetischer Demodatensatz · keine Einwilligungen dokumentiert.",
  );
  expect(fill(t.errors.dobTooEarly, { year: 1900 })).toBe(
    "Bitte ein Geburtsdatum ab 1900 angeben.",
  );
  // The one sentence that changed: an age of one.
  expect(byCount(t.review.age, 1)).toBe("· 1 Jahr");
  expect(byCount(t.review.age, 0)).toBe("· 0 Jahre");
  expect(byCount(t.review.age, 34)).toBe("· 34 Jahre");
});

// The same for the review queue. The sentences that changed: a count of reports is no longer
// "Bericht(en)" — one report, or reports.
test("the German of the review queue, put together", () => {
  const t = de.reviewQueue;
  const held = "5.4 % · 10.06.2025 (veröffentlicht)";
  expect(fill(t.replacesOnPublish, { held })).toBe(
    "Ersetzt bei Veröffentlichung: 5.4 % · 10.06.2025 (veröffentlicht)",
  );
  expect(fill(t.alreadyHeld, { held })).toBe(
    "Bereits vorhanden: 5.4 % · 10.06.2025 (veröffentlicht)",
  );
  expect(byCount(t.citedIn, 1)).toBe(" — in 1 Bericht zitiert");
  expect(byCount(t.citedIn, 2)).toBe(" — in 2 Berichten zitiert");
  expect(fill(t.reference.line, { bounds: "0–3 mmol/L" })).toBe(
    "Referenz der Quelle: 0–3 mmol/L",
  );
  expect(
    fill(t.reference.lineConverted, {
      bounds: fill(t.reference.upper, { high: 5.2 }) + " mmol/L",
    }),
  ).toBe("Referenz der Quelle (umgerechnet): obere Grenze 5.2 mmol/L");
  expect(fill(t.reference.lower, { low: 40 })).toBe("untere Grenze 40");
  expect(fill(t.dialog.replacesReject, { held })).toBe(
    "Der frühere Wert 5.4 % · 10.06.2025 (veröffentlicht) bleibt bestehen.",
  );
  expect(byCount(t.dialog.citedInReports, 1)).toMatch(
    /^ Er ist in 1 Bericht zitiert: Dieser kann erst /,
  );
  expect(byCount(t.dialog.citedInReports, 3)).toMatch(
    /^ Er ist in 3 Berichten zitiert: Diese können erst /,
  );
});

// The same for the patient page: every sentence that is put together from wording and values.
test("the German of the patient page, put together", () => {
  const t = de.patientPage;
  expect(byCount(t.age, 46)).toBe("46 Jahre");
  // The one sentence of this page that changed: an age of one.
  expect(byCount(t.age, 1)).toBe("1 Jahr");
  expect(byCount(t.age, 0)).toBe("0 Jahre");
  expect(fill(t.reportVersion, { version: 2 })).toBe("Bericht · v2");
  expect(fill(t.coverage.days, { n: 489 })).toBe("489 T");
  expect(fill(t.domains.select, { axis: "Metabolisch" })).toBe(
    "Domäne Metabolisch auswählen",
  );
  expect(fill(t.domains.show, { n: 2 })).toBe("Biomarker ansehen (2)");
  expect(fill(t.evidence.open, { name: "HbA1c" })).toBe("Marker HbA1c öffnen");
  expect(fill(t.evidence.reference, { range: "0–5.6" })).toBe("Ref 0–5.6");
  const converted = { source: "97 mg/dL", unit: "mmol/L" };
  expect(fill(t.sourceNote.converted.short, converted)).toBe(
    "umgerechnet aus 97 mg/dL",
  );
  expect(fill(t.sourceNote.converted.full, converted)).toBe(
    "Die Quelle nennt 97 mg/dL; der Wert – und das Referenzintervall, soweit eines angezeigt ist – wurde in mmol/L umgerechnet.",
  );
  // Where the metric's unit is not named.
  expect(
    fill(t.sourceNote.converted.full, {
      source: "97 mg/dL",
      unit: t.sourceNote.converted.unitOfMetric,
    }),
  ).toBe(
    "Die Quelle nennt 97 mg/dL; der Wert – und das Referenzintervall, soweit eines angezeigt ist – wurde in die Einheit der Kennzahl umgerechnet.",
  );
  const event = {
    day: "12.10.2026",
    how: t.consent.channels.in_person,
    version: "synthetic-v1",
  };
  expect(fill(t.consent.granted, event)).toBe(
    "Erteilt am 12.10.2026 (vor Ort erklärt) · Textversion synthetic-v1",
  );
  expect(fill(t.consent.withdrawn, event)).toBe(
    "Widerrufen am 12.10.2026 (vor Ort erklärt) · Textversion synthetic-v1",
  );
  expect(t.consent.note + t.consent.readOnly).toBe(
    "Stand je Zweck. Jeder Eintrag ist ein neuer, zugeordneter und auditierter Vermerk — frühere Einträge werden nie geändert. Das Dokumentieren ist dem Praxisteam vorbehalten (Nur-Lese-Ansicht).",
  );

  const lab = t.lab;
  expect(fill(lab.read, { parser: "ldt", version: 3 })).toBe(
    "Eingelesen (ldt v3): ",
  );
  expect(
    [
      fill(lab.counts.published, { n: 3 }),
      fill(lab.counts.review, { n: 1 }),
      fill(lab.counts.duplicate, { n: 0 }),
      fill(lab.counts.notImported, { n: 2 }),
    ].join(" · "),
  ).toBe(
    "3 veröffentlicht · 1 zur Prüfung · 0 bereits vorhanden · 2 nicht übernommen",
  );
  const where = fill(lab.errors.line, { line: 4 });
  expect(
    fill(lab.errors.nothingTaken, {
      reason: lab.refusals.ambiguous_header,
      where,
    }),
  ).toBe(
    "Der Tabellenkopf nennt eine Spalte doppelt. (Zeile 4) Es wurde nichts übernommen.",
  );
  expect(
    fill(lab.errors.nothingTaken, {
      reason: lab.refusals.empty_document,
      where: "",
    }),
  ).toBe("Die Datei enthält keine Laborwerte. Es wurde nichts übernommen.");
  expect(fill(lab.errors.unreadableCode, { code: "new_code", where })).toBe(
    "Die Datei konnte nicht eingelesen werden (Grund: new_code) (Zeile 4). Es wurde nichts übernommen.",
  );

  const file = t.dataExport;
  expect(
    `${byCount(file.values, 12)} · ${byCount(file.files, 3)}${fill(file.filesChanged, { n: 1 })}${fill(file.filesNeverRead, { n: 2 })} · ${byCount(file.versions, 2)}`,
  ).toBe(
    "12 Werte · 3 Originaldateien (1 nicht mehr unverändert im Speicher) (2 nie eingelesen, nicht enthalten) · 2 Berichtsfassungen",
  );
  // German as it was for a count of one, too (main forms no singular here).
  expect(
    `${byCount(file.values, 1)} · ${byCount(file.files, 1)} · ${byCount(file.versions, 1)}`,
  ).toBe("1 Werte · 1 Originaldateien · 1 Berichtsfassungen");

  // Sentences the page joins from two pieces around a name shown as it is recorded.
  expect(`${t.domains.adequacy} adäquat`).toBe("Follow-up-Adäquanz: adäquat");
  expect(
    `${t.consent.footnoteBefore} Freigabe geprüfter Berichte ${t.consent.footnoteAfter}`,
  ).toBe(
    "Synthetische Demo: Zwecke und Einwilligungstext sind Platzhalter. Technisch durchgesetzt wird derzeit nur die Freigabe geprüfter Berichte (ohne aktive Einwilligung keine Freigabe; ein Widerruf entzieht bestehende Zugriffslinks). Die übrigen Zwecke werden dokumentiert, aber noch nicht technisch durchgesetzt.",
  );
});

test("the English of the patient page, put together", () => {
  const t = en.patientPage;
  expect(byCount(t.age, 1)).toBe("1 year");
  expect(
    fill(t.lab.errors.nothingTaken, {
      reason: t.lab.refusals.ambiguous_header,
      where: fill(t.lab.errors.line, { line: 4 }),
    }),
  ).toBe(
    "The table header names a column twice. (line 4) Nothing was taken over.",
  );
  expect(
    `${byCount(t.dataExport.values, 1)} · ${byCount(t.dataExport.files, 1)} · ${byCount(t.dataExport.versions, 1)}`,
  ).toBe("1 value · 1 original file · 1 report version");
});

// The report review page is not translated yet, and its presenter is shared with the patient
// page: it keeps its own German wording, and the patient page words the same things from the
// dictionary. Two sources of one German sentence — this holds them together until the review
// page follows. (Sentences with a value in them are pinned above instead.)
test("the German the patient page words itself is the German of the shared presenter", () => {
  const presenter = readFileSync(
    join(__dirname, "../src/lib/presenters/review.ts"),
    "utf8",
  );
  const t = de.patientPage;
  const steps = t.audit.steps;
  const shared = [
    ...Object.values(t.reportStatus).filter(
      (name) => name !== t.reportStatus.none,
    ),
    t.ageUnknown,
    t.valueStatus.pending,
    t.valueStatus.rejected,
    ...Object.values(t.sourceNote.text),
    ...Object.values(t.sourceNote.source_unit),
    t.sourceNote.converted.unitOfMetric,
    ...Object.values(steps.capture),
    ...Object.values(steps.draft),
    ...Object.values(steps.clinical),
    ...Object.values(steps.release),
    ...Object.values(steps.patient),
  ];
  expect(shared.length).toBeGreaterThan(25);
  for (const wording of shared) {
    expect(presenter, wording).toContain(JSON.stringify(wording));
  }
});
