"""FastAPI application factory.

Wires middleware (correlation IDs, security headers, no-store caching), safe error
handling (no echoing of request bodies), and the /api/v1 routers.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from hadp_api.api import (
    auth_routes,
    health,
    imports_routes,
    interpretation_routes,
    observations_routes,
    patient_view_routes,
    patients_routes,
    reports_routes,
    tenancy_routes,
    worklist_routes,
)
from hadp_api.config import get_settings
from hadp_api.errors import AppError, app_error_handler
from hadp_api.logging import configure_logging

API_PREFIX = "/api/v1"

_DESCRIPTION = (
    "Longevity Health Analytics Platform API. Documentation-support software — not an "
    "autonomous medical decision-maker. Synthetic data only in development and tests."
)


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Never echo submitted values (may contain health data); report only field locations.
    assert isinstance(exc, RequestValidationError)
    fields = [{"loc": list(e.get("loc", [])), "type": e.get("type", "")} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_failed",
                "detail": "request validation failed",
                "fields": fields,
            }
        },
    )


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Longevity Health Analytics Platform API",
        version="0.0.0",
        description=_DESCRIPTION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )

    @app.middleware("http")
    async def context_and_security(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or uuid.uuid4().hex
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        # Health data must not be cached by intermediaries or browsers.
        response.headers["cache-control"] = "no-store"
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)

    for router in (
        health.router,
        auth_routes.router,
        tenancy_routes.router,
        patients_routes.router,
        worklist_routes.router,
        # Milestone 0.5 vertical spike:
        imports_routes.router,
        observations_routes.router,
        interpretation_routes.router,
        reports_routes.router,
        patient_view_routes.router,
    ):
        app.include_router(router, prefix=API_PREFIX)

    return app


# Settings are read eagerly so misconfiguration fails fast at import time.
get_settings()
app = create_app()
