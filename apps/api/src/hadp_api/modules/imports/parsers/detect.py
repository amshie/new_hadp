"""Pick the reader for a stored source document by inspecting its content."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from hadp_api.modules.imports.parsers.base import ParsedDocument, SourceParseError
from hadp_api.modules.imports.parsers.csv_reader import parse_csv
from hadp_api.modules.imports.parsers.ldt2_reader import parse_ldt2
from hadp_api.modules.imports.parsers.ldt3_reader import is_ldt3, parse_ldt3
from hadp_api.modules.imports.parsers.xdt import looks_like_xdt, read_lines


def parse_ldt(data: bytes, *, zone: ZoneInfo) -> ParsedDocument:
    """Read an LDT file with the reader for the version the file itself declares."""
    lines = read_lines(data)
    if is_ldt3(lines):
        return parse_ldt3(data, lines, zone=zone)
    return parse_ldt2(lines, zone=zone)


def parse_source_document(data: bytes, *, zone: ZoneInfo) -> ParsedDocument:
    """Read a structured laboratory file. Raises SourceParseError for anything else.

    The decision is made on the bytes, never on a file name or a declared content type.
    """
    if data.startswith(b"%PDF"):
        raise SourceParseError(
            "unsupported_format", "there is no structured reader for PDF documents"
        )
    if looks_like_xdt(data):
        return parse_ldt(data, zone=zone)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceParseError(
            "unsupported_format", "not a recognized structured laboratory file"
        ) from exc
    return parse_csv(text, zone=zone)
