"""The xDT line format shared by LDT 2 and LDT 3.

Every line is `LLL FFFF content CR LF`: a 3-digit length (content + 9), a 4-digit field
identifier, then the content. A line whose declared length does not match is refused — the
length is the format's own integrity check, and a file that fails it is not read at all.

Lives with the documents module because upload validation and the readers must agree on what a
well-formed file is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ASCII digits only: `\d` would also accept other scripts' digits, which int() then converts.
_LINE = re.compile(rb"([0-9]{3})([0-9]{4})(.*)", re.DOTALL)
_PREFIX = re.compile(rb"[0-9]{3}8000")
RECORD_START = "8000"


class XdtFormatError(Exception):
    """The bytes are not a well-formed xDT file. `detail` names a position, never content."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class Line:
    number: int
    field_id: str
    raw: bytes
    offset: int  # byte offset of the line's start in the file


def starts_like_xdt(data: bytes) -> bool:
    """A cheap sniff: the file opens with a length prefix and the record-start field."""
    return _PREFIX.match(data) is not None


def read_lines(data: bytes) -> list[Line]:
    """Split a file into its lines, refusing anything that is not exactly the line format."""
    if not data.endswith(b"\r\n"):
        raise XdtFormatError(
            "malformed_line", "every line, including the last, must end with CR LF"
        )
    lines: list[Line] = []
    offset = 0
    for number, chunk in enumerate(data[:-2].split(b"\r\n"), start=1):
        match = _LINE.fullmatch(chunk)
        if match is None:
            raise XdtFormatError("malformed_line", f"line {number}: not a length-and-field line")
        if int(match[1]) != len(match[3]) + 9:
            raise XdtFormatError(
                "malformed_line", f"line {number}: the declared length does not match"
            )
        lines.append(
            Line(number=number, field_id=match[2].decode("ascii"), raw=match[3], offset=offset)
        )
        offset += len(chunk) + 2
    if lines[0].field_id != RECORD_START:
        raise XdtFormatError("malformed_record", "the file must start with a record (8000)")
    return lines


def is_wellformed_xdt(data: bytes) -> bool:
    """True only when EVERY line of the file is a well-formed xDT line."""
    try:
        read_lines(data)
    except XdtFormatError:
        return False
    return True
