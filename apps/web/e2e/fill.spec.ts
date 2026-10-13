import { expect, test } from "@playwright/test";

import { byCount, fill } from "../src/lib/i18n/fill";

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
