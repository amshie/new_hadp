"""The shape of a proposal at the system boundary (the agent's one write tool, the API).

Validated with `extra="forbid"`: a proposal that carries `status`, `kpi_code`, `checks` or any
other field the model is not asked for is refused whole — nothing of it is written. Those
fields are computed by the checks and only by them.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from hadp_api.modules.imports.parsers.base import (
    MAX_BOUND,
    MAX_NAME,
    MAX_REFERENCE_TEXT,
    MAX_UNIT,
    MAX_VALUE,
    MAX_VALUES,
)


class ProposedValueIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyte_text: str = Field(min_length=1, max_length=MAX_NAME)
    value_text: str = Field(min_length=1, max_length=MAX_VALUE)
    unit_text: str | None = Field(default=None, max_length=MAX_UNIT)
    # The sampling date the document names for the value; a date alone stays a date alone.
    observed_at: datetime | None = None
    observed_at_is_date_only: bool = True
    reference_low: str | None = Field(default=None, max_length=MAX_BOUND)
    reference_high: str | None = Field(default=None, max_length=MAX_BOUND)
    reference_text: str | None = Field(default=None, max_length=MAX_REFERENCE_TEXT)
    page: int = Field(ge=1)
    # [x0, y0, x1, y1] in PDF points, origin top-left; None when the provider gives none.
    bbox: tuple[float, float, float, float] | None = None
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)


class ProposedBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction_provider: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=120)
    prompt_version: str = Field(min_length=1, max_length=40)
    patient_date_of_birth: date | None = None
    issue_date: date | None = None
    values: list[ProposedValueIn] = Field(min_length=1, max_length=MAX_VALUES)
