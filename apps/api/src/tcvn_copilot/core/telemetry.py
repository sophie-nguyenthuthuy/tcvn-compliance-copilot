"""OpenTelemetry + Sentry + Prometheus wiring.

Call `init_telemetry()` once at app startup. All three are best-effort: if the
endpoint is missing or unreachable, we log a warning and continue — telemetry
must never crash the API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from tcvn_copilot.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

log = logging.getLogger(__name__)


def init_telemetry(app: FastAPI) -> None:
    settings = get_settings()
    _init_sentry(settings.sentry_dsn, settings.environment.value)
    _init_otel(app, settings.otel_exporter_otlp_endpoint, settings.otel_service_name)


def _init_sentry(dsn: str | None, env: str) -> None:
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            send_default_pii=False,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        log.info("sentry initialised")
    except Exception:
        log.warning("sentry init failed", exc_info=True)


def _init_otel(app: FastAPI, endpoint: str | None, service_name: str) -> None:
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,readyz,metrics")
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
        log.info("opentelemetry initialised", extra={"endpoint": endpoint})
    except Exception:
        log.warning("opentelemetry init failed", exc_info=True)
