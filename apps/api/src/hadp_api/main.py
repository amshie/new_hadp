"""FastAPI application factory.

Wires middleware (correlation IDs, security headers, no-store caching), safe error
handling (no echoing of request bodies), and the /api/v1 routers.
"""

from __future__ import annotations

import hmac
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from hadp_api.api import (
    auth_routes,
    consents_routes,
    health,
    imports_routes,
    interpretation_routes,
    invitations_routes,
    members_routes,
    observations_routes,
    patient_view_routes,
    patients_routes,
    privacy_routes,
    reports_routes,
    staff_invitations_routes,
    tenancy_routes,
    worklist_routes,
)
from hadp_api.config import get_settings
from hadp_api.errors import AppError, app_error_handler
from hadp_api.logging import configure_logging
from hadp_api.modules.audit.service import record_security_event

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
        if get_settings().is_production:
            response.headers["strict-transport-security"] = "max-age=63072000; includeSubDomains"
        return response

    # CSRF guard (P-pre-2, docs/notes/0010): unsafe methods on cookie-authenticated
    # requests must prove same-origin — an allow-listed Origin/Referer OR the
    # double-submit token (x-csrf-token header matching the non-httpOnly csrf cookie,
    # issued at login). Exempt: login (no auth cookie is required to reach it; it is
    # rate-limited instead). The token-credentialed patient surface is anonymous (no
    # session cookie), so the guard below never triggers on it.
    _CSRF_EXEMPT = {f"{API_PREFIX}/auth/dev-login"}
    _UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

    @app.middleware("http")
    async def csrf_guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        settings = get_settings()
        if (
            request.method in _UNSAFE
            and settings.session_cookie_name in request.cookies
            and request.url.path not in _CSRF_EXEMPT
        ):
            allowed = {settings.web_base_url.rstrip("/"), settings.api_base_url.rstrip("/")}
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            ok = False
            if origin is not None:
                ok = origin.rstrip("/") in allowed
            elif referer is not None:
                ok = any(referer == a or referer.startswith(a + "/") for a in allowed)
            if not ok:
                header = request.headers.get("x-csrf-token", "")
                cookie = request.cookies.get(settings.csrf_cookie_name, "")
                ok = bool(header) and bool(cookie) and hmac.compare_digest(header, cookie)
            if not ok:
                record_security_event(
                    action="csrf.denied",
                    correlation_id=request.headers.get("x-correlation-id"),
                    detail={"method": request.method},
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "csrf_rejected",
                            "detail": "cross-site request rejected",
                        }
                    },
                )
        return await call_next(request)

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)

    for router in (
        health.router,
        auth_routes.router,
        tenancy_routes.router,
        patients_routes.router,
        consents_routes.router,
        invitations_routes.router,
        staff_invitations_routes.router,
        members_routes.router,
        privacy_routes.router,
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
