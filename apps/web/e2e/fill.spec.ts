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

// The same for the interpretation form: the checks it makes before anything is sent read as
// they did before they were split into wording and values.
test("the German of the interpretation form, put together", () => {
  const t = de.interpretation;
  expect(fill(t.titleCorrection, { run: 3 })).toBe(
    "Korrektur-Run erfassen (nach Run #3)",
  );
  expect(fill(t.crumb, { patient: "Synthetic Patient One" })).toBe(
    "Interpretation erfassen · Synthetic Patient One",
  );
  expect(fill(t.evidence, { n: 2 })).toBe("Belege (2 gewählt)");
  expect(fill(t.invalid.domain, { axis: "Metabolisch" })).toBe(
    "Metabolisch: CIS, Actionability und Follow-up-Adäquanz sind Pflichtangaben.",
  );
  const cell = { axis: "Metabolisch", cell: "Biologisch" };
  expect(fill(t.invalid.cell, cell)).toBe(
    "Metabolisch / Biologisch: Zustand und Endpunkt-Adäquanz sind Pflichtangaben.",
  );
  expect(fill(t.invalid.evidence, cell)).toBe(
    "Metabolisch / Biologisch: eine bestimmte Zelle braucht mindestens einen Beleg.",
  );
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

// The report page, as it was in German before it followed the choice: the sentences it puts
// together from pieces and values.
test("the German of the report page, put together", () => {
  const t = de.reportPage;
  expect(
    fill(t.bar.status, {
      version: 2,
      status: de.patientPage.reportStatus.draft,
    }),
  ).toBe("Bericht v2 · Status: Klinische Prüfung offen");
  expect(fill(t.rework.note, { next: 3, version: 2 })).toBe(
    "Die Belege bleiben an die jeweilige Aussage gebunden. Beim Speichern entsteht Version v3 als Entwurf; die zurückgewiesene Version v2 bleibt erhalten. Die neue Version muss erneut genehmigt und freigegeben werden.",
  );
  expect(`${t.dialog.body.redraft} ${t.dialog.body.redraftReleased}`).toBe(
    "Aus den aktuell gültigen Werten wird eine neue Entwurfsversion erstellt. Die bisherige Version bleibt gespeichert, wird hier aber nicht mehr angezeigt; manuell überarbeitete Formulierungen werden nicht übernommen. Der Zugriff der Patientin auf den freigegebenen Bericht wird damit zurückgezogen, bis die neue Version genehmigt und erneut freigegeben ist.",
  );
  expect(
    `${t.citesReplaced.note}${t.citesReplaced.released}${t.citesReplaced.clinician}`,
  ).toBe(
    "Ein zitierter Wert wurde vom Labor korrigiert. Diese Fassung kann nicht genehmigt oder freigegeben werden. Der Zugriff der Patientin auf diese Fassung wird erst mit einem neuen Entwurf zurückgezogen. Erstellen Sie einen neuen Entwurf aus den aktuellen Werten.",
  );
  // Around a name shown as it is recorded.
  expect(`${t.secondary.noteBefore} Metabolisch${t.secondary.noteAfter}`).toBe(
    "Auch für Metabolisch relevant. Zur Übersicht angezeigt – geführt und bewertet wird jeder Wert in seiner Primärdomäne; hieraus wird keine Domänen-Bewertung abgeleitet.",
  );
  expect(`${t.evidence.noteDomain} Metabolisch.`).toBe(
    "Eigene Beobachtungen der Domäne: Metabolisch.",
  );
  expect(`${t.domains.adequacy} adäquat`).toBe("Follow-up-Adäquanz: adäquat");
  expect(
    `${t.rejected.title} ${t.rejected.reason} Formulierung. Die Formulierung muss geändert werden.`,
  ).toBe(
    "Zurückgewiesen. Grund: Formulierung. Die Formulierung muss geändert werden.",
  );
  expect(fill(t.statement.label, { n: 1 }) + t.statement.removing).toBe(
    "Aussage 1 · wird entfernt",
  );
  expect(fill(t.errors.restricted, { terms: "x" })).toBe(
    "Nicht gespeichert: Der Text enthält für Berichte nicht zulässige Begriffe (x).",
  );
  // A released status says what it proves, the same way above the text and under it.
  expect(t.bar.hint.released).toBe(
    `${t.stage.badge.released} — ${t.stage.detail.released}`,
  );
});

test("the English of the report page, put together", () => {
  const t = en.reportPage;
  expect(
    fill(t.bar.status, {
      version: 2,
      status: en.patientPage.reportStatus.draft,
    }),
  ).toBe("Report v2 · Status: Clinical review open");
  expect(`${t.secondary.noteBefore} Metabolisch${t.secondary.noteAfter}`).toBe(
    "Also relevant to Metabolisch. Shown for an overview – each value is kept and assessed in its primary domain; no domain assessment is derived from this.",
  );
  expect(`${t.dialog.body.redraft} ${t.dialog.body.redraftOther}`).toBe(
    "A new draft version is created from the values that currently stand. The previous version stays stored but is no longer shown here; wording that was reworked by hand is not carried over. The new version has to be approved and released.",
  );
  expect(t.bar.hint.released).toBe(
    `${t.stage.badge.released} — ${t.stage.detail.released}`,
  );
});

// Members and deletion requests under settings, as they were in German: the sentences they
// put together from pieces and values.
test("the German of members and deletion requests, put together", () => {
  const m = de.membersPage;
  expect(
    `${m.invite.createdBefore} ${de.roles.medical_director} ${m.invite.createdAfter} ${m.invite.once}.`,
  ).toBe(
    "Einladung für Ärztliche Leitung erstellt. Geben Sie diesen Link an die eingeladene Person weiter — er wird nur einmal angezeigt.",
  );
  expect(fill(m.removeConfirm, { name: "Synthetic Clinician" })).toBe(
    "Synthetic Clinician aus dem Team entfernen?",
  );
  expect(fill(m.roleOf, { name: "Synthetic Clinician" })).toBe(
    "Rolle von Synthetic Clinician",
  );
  expect(fill(m.pending.validUntil, { day: "2026-10-20" })).toBe(
    "gültig bis 2026-10-20",
  );

  const d = de.deletionRequestsPage;
  expect(
    `${de.patientPage.deletion.reasons.patient_request} · ${fill(d.requested, { day: "13.10.2026" })}`,
  ).toBe("Betroffenenanfrage (Art. 17) · beantragt 13.10.2026");
  expect(fill(d.executeConfirm, { name: "Synthetic E2E" })).toBe(
    'Daten von „Synthetic E2E" jetzt endgültig und unwiderruflich löschen? Der Datensatz wird anonymisiert; abgeleitete Daten, Dokumente und Berichte werden gelöscht. Dies kann nicht rückgängig gemacht werden.',
  );
  expect(fill(d.approveConfirm, { name: "Synthetic E2E" })).toBe(
    'Löschung für „Synthetic E2E" freigeben? Die Ausführung erfolgt gesondert und ist unwiderruflich.',
  );
});

test("the English of members and deletion requests, put together", () => {
  const m = en.membersPage;
  expect(
    `${m.invite.createdBefore} ${en.roles.medical_director} ${m.invite.createdAfter} ${m.invite.once}.`,
  ).toBe(
    "Invitation for Medical director created. Pass this link on to the person invited — it is shown only once.",
  );
  expect(
    `${en.patientPage.deletion.reasons.data_minimization} · ${fill(en.deletionRequestsPage.requested, { day: "13.10.2026" })}`,
  ).toBe("Data minimisation · requested 13.10.2026");
});
