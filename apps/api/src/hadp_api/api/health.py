"""Health/readiness endpoint (no auth)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from hadp_api.config import get_settings

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    app_env: str
    synthetic_data_only: bool


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    return HealthOut(
        status="ok",
        app_env=settings.app_env,
        synthetic_data_only=not settings.is_production,
    )
