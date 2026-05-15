"""Structured logging configuration.

JSON in production, pretty console output in development. All logs flow through
structlog so we get consistent key/value context (request_id, trace_id, user_id).
"""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

from tcvn_copilot.config import LogFormat, get_settings


def _drop_color_message(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Uvicorn dumps a colored copy of the message under `color_message`; drop it."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _drop_color_message,
    ]

    if settings.log_format is LogFormat.JSON:
        renderer: Processor = structlog.processors.JSONRenderer()
        shared_processors.append(structlog.processors.format_exc_info)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Silence noisy libraries
    for noisy in ("uvicorn.access", "httpx", "httpcore", "botocore"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
