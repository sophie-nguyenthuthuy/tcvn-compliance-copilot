"""Request-scoped context: assign / propagate request_id and time the request."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach `request_id` to every request, log access lines, set the header."""

    header_name = "x-request-id"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            status_code = response.status_code if response else 500
            log.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=round(duration_ms, 2),
                client=request.client.host if request.client else None,
            )
            if response is not None:
                response.headers[self.header_name] = request_id
            structlog.contextvars.clear_contextvars()
