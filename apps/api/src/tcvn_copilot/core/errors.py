"""Domain exception hierarchy + FastAPI exception handlers.

Every error surfaced to the client follows RFC 9457 (problem details).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)


class DomainError(Exception):
    """Base class for all expected, user-visible errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthenticated"


class AuthorizationError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class RateLimitError(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


class ExternalServiceError(DomainError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "external_service_error"


def _problem(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    extras: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://errors.tcvn-copilot.dev/{code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url),
        "trace_id": request.headers.get("x-request-id", str(uuid4())),
    }
    if extras:
        body.update(extras)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        log.warning("domain_error", code=exc.code, message=exc.message, details=exc.details)
        return _problem(
            request,
            status_code=exc.status_code,
            code=exc.code,
            title=exc.code.replace("_", " ").title(),
            detail=exc.message,
            extras={"details": exc.details} if exc.details else None,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            title="Validation Error",
            detail="One or more fields are invalid.",
            extras={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", path=str(request.url))
        return _problem(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            title="Internal Server Error",
            detail="An unexpected error occurred. The incident has been recorded.",
        )
