"""Extraction providers: what turns a stored PDF into a PROPOSAL.

Every provider implements `ExtractionProvider` and hands back the shape the one write takes
(`ProposedBatchIn`), so the checks and the confirmation screen do not know which provider
proposed. The provider is chosen by configuration (`INTAKE_PROVIDER`), never by the document.

Built here: `TextLayerProvider`, a deterministic reader of the text layer. It knows no
laboratory layout; it takes a line that reads "name value unit [reference]" as a value and
proposes it with LOW confidence (0.6), so everything it proposes is yellow and a human looks at
each value. It is the provider that needs no model and no network: the default for development
and tests, and the floor a model provider is measured against. A model-backed provider behind
the same protocol is a later slice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from hadp_api.config import Settings, get_settings
from hadp_api.modules.intake.pages import PageSet
from hadp_api.modules.intake.schemas import ProposedBatchIn

TEXT_LAYER_PROVIDER = "text-layer"
MODEL_PROVIDER = "model"
LOW_CONFIDENCE = Decimal("0.600")


class ExtractionProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    def extract(self, data: bytes, pages: PageSet) -> ProposedBatchIn: ...


_DATE = r"(\d{2})\.(\d{2})\.(\d{4})"
_DOB = re.compile(r"(?:geb\.|\*)\s*" + _DATE)
_ISSUE = re.compile(r"(?:Befunddatum|Befund vom|Befund erstellt am)\s*:?\s*" + _DATE)
_SAMPLED = re.compile(r"(?:Probenentnahme|Entnahme)\s*:?\s*" + _DATE)
_INLINE_SAMPLED = re.compile(r"\(Entnahme\s+" + _DATE + r"\)")
# "Name 5,4 % 4,0 - 6,0", "Name: 5,4 % [4,0 - 6,0]", "Name 128 mg/dl Norm: 50 - 130".
_LINE = re.compile(
    r"^(?P<name>[^\s:\[\]][^:\[\]]{1,59}?):?\s+"
    r"(?P<value>[<>]?\d+(?:[.,]\d+)?)\s+"
    r"(?P<unit>(?=\S*[A-Za-zµ%])[^\s\[\]()·]{1,20})"
    r"(?:\s+(?:Norm:\s*)?\[?(?P<ref>[<>]?\s*\d[\d.,]*(?:\s*-\s*\d[\d.,]*)?)\]?)?"
)
_HEADER_WORDS = ("Patient", "Pat.", "Entnahme", "Probenentnahme", "Befund", "Seite", "Parameter")


def _iso(m: re.Match[str]) -> str:
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def _reference(text: str | None) -> tuple[str | None, str | None, str | None]:
    if not text:
        return None, None, None
    raw = " ".join(text.split())
    if raw.startswith("<"):
        return None, raw[1:].strip(), raw
    if raw.startswith(">"):
        return raw[1:].strip(), None, raw
    if "-" in raw:
        low, high = (p.strip() for p in raw.split("-", 1))
        return low, high, raw
    return None, None, raw


@dataclass(frozen=True)
class TextLayerProvider:
    name: str = TEXT_LAYER_PROVIDER
    model_id: str = "none"
    prompt_version: str = "text-layer-1"

    def extract(self, data: bytes, pages: PageSet) -> ProposedBatchIn:
        text = "\n".join(pages.texts)
        first_line = next((ln.strip() for ln in pages.text(1).splitlines() if ln.strip()), None)
        dob = _DOB.search(text)
        issue = _ISSUE.search(text)
        sampled = _SAMPLED.search(text)
        values: list[dict[str, Any]] = []
        for page_no, page_text in enumerate(pages.texts, start=1):
            for line in page_text.splitlines():
                stripped = line.strip()
                if (
                    not stripped
                    or "·" in stripped
                    or any(stripped.startswith(w) for w in _HEADER_WORDS)
                ):
                    continue
                m = _LINE.match(stripped)
                if m is None or m.group("name").rstrip().endswith(","):
                    continue
                inline = _INLINE_SAMPLED.search(stripped)
                when = inline or sampled
                low, high, ref_text = _reference(m.group("ref"))
                values.append(
                    {
                        "analyte_text": m.group("name").strip(),
                        "value_text": m.group("value"),
                        "unit_text": m.group("unit"),
                        "observed_at": _iso(when) if when else None,
                        "observed_at_is_date_only": True,
                        "reference_low": low,
                        "reference_high": high,
                        "reference_text": ref_text,
                        "page": page_no,
                        # Where it is printed is found by code when the batch is written.
                        "bbox": None,
                        "confidence": LOW_CONFIDENCE,
                    }
                )
        return ProposedBatchIn.model_validate(
            {
                "extraction_provider": self.name,
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "patient_date_of_birth": _iso(dob) if dob else None,
                "issue_date": _iso(issue) if issue else None,
                # The letterhead: the first line of the first page, as printed.
                "source_lab": first_line[:200] if first_line else None,
                "values": values or [_nothing_found(len(pages.texts))],
            }
        )


def _nothing_found(page_count: int) -> dict[str, Any]:
    """A provider that read nothing still answers: one proposal that cannot pass (the word
    stands on no page), so the batch shows a human that nothing was read, instead of being
    silently empty."""
    return {
        "analyte_text": "(nichts erkannt)",
        "value_text": "0",
        "unit_text": None,
        "observed_at": None,
        "observed_at_is_date_only": True,
        "page": max(1, page_count),
        "bbox": None,
        "confidence": Decimal("0"),
    }


def get_provider(name: str, settings: Settings | None = None) -> ExtractionProvider:
    """The provider configuration names. An unknown name is a configuration error, not a
    fallback: nothing proposes by accident. The model provider needs settings (which model,
    which key) and refuses, visibly, when they are missing."""
    if name == TEXT_LAYER_PROVIDER:
        return TextLayerProvider()
    if name == MODEL_PROVIDER:
        from hadp_api.modules.intake.model_provider import build_model_provider

        return build_model_provider(settings if settings is not None else get_settings())
    raise LookupError(f"unknown intake provider {name!r}")


def provider_names() -> tuple[str, ...]:
    return (TEXT_LAYER_PROVIDER, MODEL_PROVIDER)
