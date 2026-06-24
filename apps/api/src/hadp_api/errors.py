"""Stable, machine-readable application errors.

Errors expose a stable `code` plus a safe human-readable detail. They never echo
request bodies, document contents, or secrets (CLAUDE.md API conventions).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    code: str = "error"
    http_status: int = 400

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.code
        super().__init__(self.detail)


class NotAuthenticated(AppError):
    code = "not_authenticated"
    http_status = 401


class PermissionDenied(AppError):
    code = "permission_denied"
    http_status = 403


class NotFound(AppError):
    code = "not_found"
    http_status = 404


class Conflict(AppError):
    code = "conflict"
    http_status = 409


class ValidationFailed(AppError):
    code = "validation_failed"
    http_status = 422


class IntendedUseViolation(AppError):
    """Raised when an operation would cross the documented intended-use boundary."""

    code = "intended_use_violation"
    http_status = 409


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "detail": exc.detail}},
    )
