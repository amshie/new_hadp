"""Versioned formula registry (ADR-0004 §10, Slice 4 — first tranche).

Each Formula is a PURE, deterministic function over same-patient input Observation values, with its
required input KPIs + units, output KPI + unit, and an output quantization that is PART OF the
version (changing the rounding = a new formula version). No demographics, no clinical estimator
equations — only trivially-safe arithmetic (eGFR/FIB-4/HOMA-IR/ALMI and wearable-derived are gated
to a later, clinician-signed slice). The registry touches no DB; the compute service applies it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Formula:
    formula_id: str  # e.g. "non_hdl_c.v1" — frozen onto the derived Observation
    formula_version: str  # e.g. "v1" — the longitudinal-comparability key
    algorithm_name: str
    output_kpi_code: str
    output_unit: str  # must match the catalog canonical_unit_ucum of output_kpi_code
    inputs: dict[str, str]  # role -> required input kpi_code
    input_units: dict[str, str]  # role -> required normalized_unit (no inference, §9.8)
    quantize: Decimal  # output rounding (clinically conventional; part of the version)
    fn: Callable[[Mapping[str, Decimal]], Decimal]


def _non_hdl_c(v: Mapping[str, Decimal]) -> Decimal:
    return v["total_cholesterol"] - v["hdl"]


def _pulse_pressure(v: Mapping[str, Decimal]) -> Decimal:
    return v["systolic"] - v["diastolic"]


def _mean_arterial_pressure(v: Mapping[str, Decimal]) -> Decimal:
    return v["diastolic"] + (v["systolic"] - v["diastolic"]) / Decimal(3)


def _nlr(v: Mapping[str, Decimal]) -> Decimal:
    return v["neutrophils"] / v["lymphocytes"]


FORMULAS: dict[str, Formula] = {
    "non_hdl_c.v1": Formula(
        formula_id="non_hdl_c.v1",
        formula_version="v1",
        algorithm_name="non_hdl_c",
        output_kpi_code="cardio.non_hdl_c",
        output_unit="mmol/L",
        inputs={"total_cholesterol": "cardio.total_cholesterol", "hdl": "cardio.hdl_c"},
        input_units={"total_cholesterol": "mmol/L", "hdl": "mmol/L"},
        quantize=Decimal("0.01"),
        fn=_non_hdl_c,
    ),
    "pulse_pressure.v1": Formula(
        formula_id="pulse_pressure.v1",
        formula_version="v1",
        algorithm_name="pulse_pressure",
        output_kpi_code="cardio.pulse_pressure",
        output_unit="mm[Hg]",
        inputs={"systolic": "cardio.systolic_bp", "diastolic": "cardio.diastolic_bp"},
        input_units={"systolic": "mm[Hg]", "diastolic": "mm[Hg]"},
        quantize=Decimal("1"),
        fn=_pulse_pressure,
    ),
    "map.v1": Formula(
        formula_id="map.v1",
        formula_version="v1",
        algorithm_name="mean_arterial_pressure",
        output_kpi_code="cardio.mean_arterial_pressure",
        output_unit="mm[Hg]",
        inputs={"systolic": "cardio.systolic_bp", "diastolic": "cardio.diastolic_bp"},
        input_units={"systolic": "mm[Hg]", "diastolic": "mm[Hg]"},
        quantize=Decimal("1"),
        fn=_mean_arterial_pressure,
    ),
    "nlr.v1": Formula(
        formula_id="nlr.v1",
        formula_version="v1",
        algorithm_name="nlr",
        output_kpi_code="immune.nlr",
        output_unit="1",
        inputs={"neutrophils": "immune.neutrophils_abs", "lymphocytes": "immune.lymphocytes_abs"},
        input_units={"neutrophils": "10*9/L", "lymphocytes": "10*9/L"},
        quantize=Decimal("0.01"),
        fn=_nlr,
    ),
}
