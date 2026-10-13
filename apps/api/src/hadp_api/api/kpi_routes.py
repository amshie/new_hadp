"""KPI catalog route: the core markers a domain view expects (ADR-0004).

Global reference data, the same for every clinic: names, domains and classes — no patient data,
no ranges, no scores. Read by the same staff who read a patient's values.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hadp_api.auth.authz import Action
from hadp_api.auth.dependencies import TenantContext, require
from hadp_api.modules.kpi import service as kpi_service

router = APIRouter(tags=["kpi-catalog"])


class CoreKpiOut(BaseModel):
    code: str
    display_name: str
    primary_domain_axis: str
    measurement_class: str


@router.get("/kpi-catalog/core", response_model=list[CoreKpiOut])
def core_catalog(
    ctx: TenantContext = Depends(require(Action.OBSERVATION_READ)),
) -> list[CoreKpiOut]:
    return [
        CoreKpiOut(
            code=k.code,
            display_name=k.display_name,
            primary_domain_axis=k.primary_domain_axis.value,
            measurement_class=k.measurement_class.value,
        )
        for k in kpi_service.core_kpis(ctx.db)
    ]
