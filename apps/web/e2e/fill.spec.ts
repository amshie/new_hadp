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
