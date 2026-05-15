"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from tcvn_copilot import __version__
from tcvn_copilot.api.middleware.request_context import RequestContextMiddleware
from tcvn_copilot.api.middleware.security_headers import SecurityHeadersMiddleware
from tcvn_copilot.api.routes import api_router
from tcvn_copilot.config import get_settings
from tcvn_copilot.core.errors import register_exception_handlers
from tcvn_copilot.core.logging import configure_logging, get_logger
from tcvn_copilot.core.telemetry import init_telemetry
from tcvn_copilot.db.session import dispose_engine, init_engine

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    configure_logging()
    log.info("api_starting", version=__version__, env=get_settings().environment.value)
    init_engine()
    init_telemetry(app)
    try:
        yield
    finally:
        log.info("api_stopping")
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TCVN/QCVN Compliance Copilot",
        description=(
            "RAG-based compliance review of AEC drawings against Vietnamese TCVN/QCVN standards."
        ),
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    # --- Middleware (outer-to-inner) ---
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.api_cors_origins] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    # --- Routes ---
    app.include_router(api_router)

    # --- Error handling ---
    register_exception_handlers(app)

    return app


app = create_app()
