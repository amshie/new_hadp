"""Synthetic LDT 2 files for the reader tests — built line by line, never real reports.

The patient ("Erika Mustermann") is fictional. Every line is generated with its correct length
prefix, so a test can also produce a deliberately broken file by editing the bytes.
"""

from __future__ import annotations

Field = tuple[str, str]


def ldt_line(field_id: str, content: str, encoding: str = "iso-8859-15") -> bytes:
    raw = content.encode(encoding)
    return f"{len(raw) + 9:03d}{field_id}".encode("ascii") + raw + b"\r\n"


def ldt_file(*records: list[Field], encoding: str = "iso-8859-15") -> bytes:
    return b"".join(ldt_line(f, c, encoding) for record in records for f, c in record)


def header(version: str = "LDT1014.01", charset: str | None = "4") -> list[Field]:
    fields = [("8000", "8220"), ("8100", "00000"), ("9212", version)]
    if charset is not None:
        fields.append(("9106", charset))
    return fields


TRAILER: list[Field] = [("8000", "8221"), ("8100", "00000")]


def report(
    *tests: list[Field],
    kind: str | None = "E",
    last_name: str = "Mustermann",
    first_name: str = "Erika",
    born: str | None = "19800115",
    record_type: str = "8201",
) -> list[Field]:
    fields = [
        ("8000", record_type),
        ("8100", "00000"),
        ("8310", "A-0001"),
        ("8311", "L-2025-000123"),
        ("8302", "20250611"),
        ("3101", last_name),
        ("3102", first_name),
    ]
    if born is not None:
        fields.append(("3103", born))
    if kind is not None:
        fields.append(("8401", kind))
    for test in tests:
        fields.extend(test)
    fields.append(("8490", "Auftragsbezogener Hinweis"))
    return fields


def lab_test(
    ident: str,
    name: str | None = None,
    *,
    value: str | None = None,
    unit: str | None = None,
    low: str | None = None,
    high: str | None = None,
    reference: tuple[str, ...] = (),
    day: str | None = "20250610",
    clock: str | None = None,
    status: str | None = None,
    text: tuple[str, ...] = (),
) -> list[Field]:
    fields = [("8410", ident)]
    optional = [
        ("8411", name),
        ("8418", status),
        ("8432", day),
        ("8433", clock),
        ("8420", value),
        ("8421", unit),
    ]
    fields += [(f, c) for f, c in optional if c is not None]
    fields += [("8480", t) for t in text]
    fields += [("8460", r) for r in reference]
    fields += [(f, c) for f, c in (("8461", low), ("8462", high)) if c is not None]
    return fields
