"""Shared utilities for D&D resource generators.

This module provides two building blocks used by every generator:

- ``resolve_title_and_slug`` — normalise the title/slug from a request.
- ``run_generation`` — execute a structured LLM call with usage limits and
  convert ``UsageLimitExceeded`` into an ``ApiError`` so callers never need
  to handle pydantic-ai internals directly.
"""
from __future__ import annotations

from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from pydantic_ai import UsageLimitExceeded, UsageLimits
from pydantic_ai.exceptions import UnexpectedModelBehavior
from slugify import slugify

from llm_api.models.requests import GenerateRequest
from llm_api.providers.factory import build_agent
from llm_api.services.config import Settings
from llm_api.services.errors import ApiError

log = structlog.get_logger(__name__)

OutputT = TypeVar("OutputT", bound=BaseModel)


def resolve_title_and_slug(*, request: GenerateRequest, fallback_title: str) -> tuple[str, str]:
    """Resolve a display title and URL slug from a generation request.

    If ``request.title`` is blank, ``fallback_title`` is used.  If
    ``request.slug`` is blank it is derived from the resolved title via
    python-slugify.

    Args:
        request: The incoming ``GenerateRequest``.
        fallback_title: Used when ``request.title`` is empty.

    Returns:
        A ``(title, slug)`` tuple, both non-empty strings.
    """
    title = (request.title or "").strip() or fallback_title
    slug = (request.slug or "").strip()
    if not slug:
        slug = slugify(title)
    return title, slug


async def run_generation(
    *,
    output_type: type[OutputT],
    system_prompt: str,
    user_prompt: str,
    provider: str,
    settings: Settings,
) -> OutputT:
    """Run a structured LLM generation call and return the typed output.

    Handles usage-limit enforcement and converts ``UsageLimitExceeded`` into
    an ``ApiError`` with code ``usage_limit_exceeded`` (HTTP 507) so generator
    functions never need to import pydantic-ai internals.

    Args:
        output_type: Pydantic model class that defines the expected output shape.
        system_prompt: The system-level instruction for the LLM.
        user_prompt: The user-facing prompt assembled by the generator.
        provider: Resolved provider name (e.g. ``"anthropic"``, ``"ollama"``).
                  Must NOT be ``"mock"`` — callers short-circuit before calling
                  this function.
        settings: A ``Settings`` instance (instantiated fresh per request so
                  env-var changes in tests are picked up without a server restart).

    Returns:
        An instance of ``output_type`` populated from the LLM response.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) when the model exceeds the
                  configured request or token limits.
        ApiError: ``provider_not_configured`` / ``unknown_provider`` (400) when
                  ``build_agent`` cannot satisfy the provider (propagated as-is).
        ApiError: ``model_behavior_error`` (502) when the model returns invalid
                  structured output after exhausting retries.
    """
    log.debug("generation.llm_call", provider=provider, prompt_length=len(user_prompt))

    agent = build_agent(
        output_type=output_type,
        system_prompt=system_prompt,
        provider_override=provider,
    )
    try:
        result = await agent.run(
            user_prompt,
            usage_limits=UsageLimits(
                request_limit=settings.max_model_requests_per_generation,
                response_tokens_limit=settings.max_output_tokens,
            ),
        )
    except UsageLimitExceeded as exc:
        raise ApiError(
            code="usage_limit_exceeded",
            message="Generation exceeded configured usage limits",
            status_code=507,
            details={"error": str(exc)},
        )
    except UnexpectedModelBehavior as exc:
        log.warning(
            "generation.model_behavior_error",
            provider=provider,
            error=str(exc),
        )
        raise ApiError(
            code="model_behavior_error",
            message="The model failed to produce valid structured output after retries",
            status_code=502,
            details={"error": str(exc)},
        ) from exc

    log.debug("generation.llm_done", output_type=output_type.__name__)
    return result.output  # type: ignore[return-value]
