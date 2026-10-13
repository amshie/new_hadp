// Wording with a value in it: fill("{n} Einträge", { n: 3 }). The two languages put a value
// where their sentence needs it. A place the wording names and the values do not hold is left
// as it is — visible on the page, not silently empty.
export function fill(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in values ? String(values[name]) : whole,
  );
}

// One wording for a count of one, another for every other count.
export function byCount(
  wording: { one: string; other: string },
  n: number,
): string {
  return fill(n === 1 ? wording.one : wording.other, { n });
}
