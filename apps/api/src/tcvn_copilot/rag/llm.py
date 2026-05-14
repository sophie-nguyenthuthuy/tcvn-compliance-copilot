"""Thin async wrapper around the Anthropic Claude API.

Centralises prompt caching, retries, and response parsing so call sites in the
compliance engine stay declarative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.errors import ExternalServiceError
from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)

ModelRole = Literal["reasoning", "extraction"]


@dataclass(slots=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    model: str


_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client  # noqa: PLW0603
    if _client is None:
        settings = get_settings()
        _client = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            timeout=settings.claude_request_timeout_seconds,
        )
    return _client


def _model_for(role: ModelRole) -> str:
    s = get_settings()
    return s.claude_reasoning_model if role == "reasoning" else s.claude_extraction_model


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
)
async def complete(
    *,
    system: str | list[dict[str, Any]],
    messages: list[MessageParam],
    role: ModelRole = "reasoning",
    max_tokens: int | None = None,
    temperature: float = 0.0,
    cacheable_system: bool = True,
) -> LLMResponse:
    """Run a single Claude completion.

    `cacheable_system` marks the system prompt as a cache control point so the
    standards corpus and instructions are billed at the cached rate after the
    first call.
    """
    settings = get_settings()
    model = _model_for(role)

    sys_block: list[dict[str, Any]]
    if isinstance(system, str):
        sys_block = [{"type": "text", "text": system}]
    else:
        sys_block = list(system)

    if cacheable_system and settings.claude_prompt_cache_enabled and sys_block:
        sys_block[-1] = {**sys_block[-1], "cache_control": {"type": "ephemeral"}}

    try:
        resp = await _get_client().messages.create(
            model=model,
            system=sys_block,
            messages=messages,
            max_tokens=max_tokens or settings.claude_max_output_tokens,
            temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("anthropic_call_failed", error=str(exc), model=model)
        raise ExternalServiceError(f"Claude API call failed: {exc}") from exc

    text_parts = [block.text for block in resp.content if block.type == "text"]
    usage = resp.usage
    return LLMResponse(
        text="".join(text_parts),
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        model=model,
    )


async def complete_json(
    *,
    system: str | list[dict[str, Any]],
    messages: list[MessageParam],
    role: ModelRole = "reasoning",
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Convenience wrapper that asks for and parses a JSON-only response."""
    resp = await complete(
        system=system,
        messages=messages,
        role=role,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    body = resp.text.strip()
    # Strip ```json fences if the model added them despite instructions.
    if body.startswith("```"):
        body = body.strip("`")
        body = body.split("\n", 1)[1] if "\n" in body else body
        body = body.rstrip("`").strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        log.warning("llm_returned_invalid_json", body_preview=body[:500])
        raise ExternalServiceError(f"LLM returned non-JSON: {exc}") from exc
