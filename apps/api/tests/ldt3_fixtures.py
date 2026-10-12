"""Synthetic LDT 3 files for the reader tests — built object by object, never real reports.

The patient ("Erika Mustermann") is fictional. The builder writes every line with its correct
length and closes the file with the trailer checksum, so a test can break exactly one thing.
"""

from __future__ import annotations

import hashlib

from tests.ldt_fixtures import Field, ldt_line


def obj(attribute_id: str, attribute_name: str, name: str, *items: list[Field]) -> list[Field]:
    """An attribute line followed by its object, as LDT 3 requires."""
    inner = [f for item in items for f in item]
    return [(attribute_id, attribute_name), ("8002", name), *inner, ("8003", name)]


def fields(*pairs: Field) -> list[Field]:
    return list(pairs)


def timestamp(
    attribute_id: str,
    attribute_name: str,
    day: str | None = "20250610",
    clock: str | None = "081500",
    zone: str | None = "UTC+2",
) -> list[Field]:
    parts = [("7278", day), ("7279", clock), ("7273", zone)]
    return obj(
        attribute_id, attribute_name, "Obj_0054", [(f, c) for f, c in parts if c is not None]
    )


def material(
    sample: str = "S1", *, sampled: list[Field] | None = None, with_time: bool = True
) -> list[Field]:
    stamp = (
        sampled if sampled is not None else timestamp("8219", "Timestamp_Materialabnahme_entnahme")
    )
    return obj(
        "8137",
        "Material",
        "Obj_0037",
        fields(("7364", sample), ("8430", "Serum")),
        stamp if with_time else [],
    )


def reference(
    low: str | None = None,
    high: str | None = None,
    *,
    text: tuple[str, ...] = (),
    unit: str | None = None,
    note: str | None = None,
) -> list[Field]:
    body: list[Field] = [("8424", "20")]
    body += [("8460", t) for t in text]
    for field_id, bound in (("8461", low), ("8462", high)):
        if bound is not None:
            body.append((field_id, bound))
            if unit is not None:
                body += [("8419", "2"), ("8421", unit)]
    body.append(("8422", "N"))
    attention = (
        obj(
            "8126",
            "Fehlermeldung_Aufmerksamkeit",
            "Obj_0026",
            fields(("7280", "5")),
            obj("8167", "Zusaetzliche_Informationen", "Obj_0068", fields(("3564", note))),
        )
        if note
        else []
    )
    return obj("8142", "Normalwert", "Obj_0042", body, attention)


def value(
    result: str,
    unit: str | None = "mmol/l",
    *,
    system: str = "1",
    shape: str = "01",
    references: tuple[list[Field], ...] = (),
) -> list[Field]:
    body: list[Field] = [("7306", shape), ("8420", result), ("8419", system)]
    if unit is not None:
        body.append(("8421", unit))
    for ref in references:
        body += ref
    body += timestamp("8225", "Timestamp_Messung", "20250610", "143000")
    return body


def chemistry(
    ident: str,
    name: str | None,
    *values: list[Field],
    samples: tuple[str, ...] = ("S1",),
    status: str = "06",
    extra: list[Field] | None = None,
) -> list[Field]:
    head: list[Field] = [("7304", f"R-{ident}")]
    head += [("7364", s) for s in samples]
    head.append(("8410", ident))
    if name is not None:
        head.append(("8411", name))
    head.append(("8418", status))
    return obj("8160", "UE_Klinische_Chemie", "Obj_0060", head, *values, extra or [])


def note(text: str = "Probe hämolytisch") -> list[Field]:
    return obj("8167", "Zusaetzliche_Informationen", "Obj_0068", fields(("3564", text)))


def microbiology() -> list[Field]:
    return obj("8161", "UE_Mikrobiologie", "Obj_0061", fields(("7304", "R-MIBI"), ("8418", "06")))


def header(version: str = "LDT3.2.20") -> list[Field]:
    return [
        ("8000", "8220"),
        *obj("8132", "Kopfdaten", "Obj_0032", fields(("0001", version))),
        ("8001", "8220"),
    ]


def report(
    *parts: list[Field],
    born: str | None = "19800115",
    last_name: str = "Mustermann",
    first_name: str = "Erika",
    record_type: str = "8205",
) -> list[Field]:
    """A report record. `parts` are materials (record level) and results (inside the report)."""
    materials = [p for p in parts if p[0][0] == "8137"]
    results = [p for p in parts if p[0][0] != "8137"]
    person: list[Field] = [("3101", last_name), ("3102", first_name)]
    if born is not None:
        person.append(("3103", born))
    return [
        ("8000", record_type),
        *obj("8145", "Patient", "Obj_0045", obj("8147", "Person", "Obj_0047", person)),
        *obj(
            "8117",
            "Befundinformationen",
            "Obj_0017",
            fields(("8311", "L-2025-000123"), ("8401", "2")),
        ),
        *[f for m in materials for f in m],
        *obj("8135", "Laborergebnisbericht", "Obj_0035", *results),
        ("8001", record_type),
    ]


def ldt3_file(*records: list[Field], checksum: bool = True) -> bytes:
    body = b"".join(ldt_line(f, c) for record in records for f, c in record)
    body += ldt_line("8000", "8221")
    if checksum:
        body += ldt_line("9300", hashlib.sha1(body, usedforsecurity=False).hexdigest())
    return body + ldt_line("8001", "8221")
