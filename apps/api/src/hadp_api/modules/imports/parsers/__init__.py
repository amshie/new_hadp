"""Deterministic readers for structured laboratory source files (ingestion tier 1).

Each reader turns the bytes of a stored source document into rows in the pipeline's
intermediate form (`ParsedValue`). Readers only TRANSPORT source values: names, values, units
and reference bounds are passed on verbatim, and every row carries a source locator. They never
normalize, convert, or interpret — that stays with `imports.normalize` and the human review
queue. A structurally unreadable file is refused as a whole (`SourceParseError`); nothing is
imported from a file that could only be read in part.
"""

from hadp_api.modules.imports.parsers.base import ParsedDocument, ParsedValue, SourceParseError
from hadp_api.modules.imports.parsers.detect import parse_source_document

__all__ = ["ParsedDocument", "ParsedValue", "SourceParseError", "parse_source_document"]
