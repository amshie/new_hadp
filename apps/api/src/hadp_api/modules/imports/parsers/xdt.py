"""The xDT line format shared by LDT 2 and LDT 3.

Every line is `LLL FFFF content CR LF`: a 3-digit length (content + 9), a 4-digit field
identifier, then the content. A line whose declared length does not match is refused — the
length is the format's own integrity check, and a file that fails it is not read at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hadp_api.modules.imports.parsers.base import SourceParseError

_LINE = re.compile(rb"(\d{3})(\d{4})(.*)", re.DOTALL)
RECORD_START = "8000"


@dataclass(frozen=True)
class Line:
    number: int
    field_id: str
    raw: bytes


def looks_like_xdt(data: bytes) -> bool:
    """True when the content starts like an xDT file: a well-formed 8000 line."""
    first = data.split(b"\r\n", 1)[0]
    match = _LINE.fullmatch(first)
    return bool(match and match[2] == b"8000" and int(match[1]) == len(match[3]) + 9)


def read_lines(data: bytes) -> list[Line]:
    if b"\r\n" not in data:
        raise SourceParseError("malformed_line", "lines must end with CR LF")
    chunks = data.split(b"\r\n")
    if chunks[-1] in (b"", b"\x1a"):  # the end of the file, optionally with an EOF mark
        chunks.pop()
    lines = []
    for number, chunk in enumerate(chunks, start=1):
        match = _LINE.fullmatch(chunk)
        if match is None:
            raise SourceParseError("malformed_line", f"line {number}: not a length-and-field line")
        if int(match[1]) != len(match[3]) + 9:
            raise SourceParseError(
                "malformed_line", f"line {number}: the declared length does not match"
            )
        lines.append(Line(number=number, field_id=match[2].decode("ascii"), raw=match[3]))
    if not lines or lines[0].field_id != RECORD_START:
        raise SourceParseError("malformed_record", "the file must start with a record (8000)")
    return lines
