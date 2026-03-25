# services/llm_api/tests/test_generators_base.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


def test_resolve_title_and_slug_uses_title():
    from llm_api.generators.base import resolve_title_and_slug
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="test", title="Dragon Cave", slug="")
    title, slug = resolve_title_and_slug(request=req, fallback_title="Fallback")
    assert title == "Dragon Cave"
    assert slug == "dragon-cave"


def test_resolve_title_and_slug_uses_fallback():
    from llm_api.generators.base import resolve_title_and_slug
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="test", title="", slug="")
    title, slug = resolve_title_and_slug(request=req, fallback_title="New NPC")
    assert title == "New NPC"
    assert slug == "new-npc"


def test_resolve_title_and_slug_preserves_explicit_slug():
    from llm_api.generators.base import resolve_title_and_slug
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="test", title="Something", slug="my-custom-slug")
    title, slug = resolve_title_and_slug(request=req, fallback_title="Fallback")
    assert slug == "my-custom-slug"


@pytest.mark.asyncio
async def test_run_generation_mock_raises_on_real_provider(monkeypatch):
    """run_generation should not be called with 'mock' — but if build_agent
    raises for an unconfigured provider, ApiError propagates correctly."""
    from llm_api.generators.base import run_generation
    from llm_api.services.config import Settings
    from llm_api.services.errors import ApiError
    from pydantic import BaseModel

    class Out(BaseModel):
        value: str

    # "unknown_provider" triggers ApiError from build_agent
    with pytest.raises((ApiError, RuntimeError)):
        await run_generation(
            output_type=Out,
            system_prompt="sys",
            user_prompt="user",
            provider="nonexistent_provider_xyz",
            settings=Settings(),  # type: ignore[call-arg]
        )


@pytest.mark.asyncio
async def test_run_generation_converts_unexpected_model_behavior_to_api_error():
    """UnexpectedModelBehavior must become a 502 ApiError, not bubble as 500."""
    from unittest.mock import AsyncMock, patch

    from pydantic import BaseModel
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    from llm_api.generators.base import run_generation
    from llm_api.services.config import Settings
    from llm_api.services.errors import ApiError

    class _Out(BaseModel):
        name: str

    with patch("llm_api.generators.base.build_agent") as mock_build:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = UnexpectedModelBehavior(
            "Exceeded maximum retries (1) for output validation"
        )
        mock_build.return_value = mock_agent

        with pytest.raises(ApiError) as exc_info:
            await run_generation(
                output_type=_Out,
                system_prompt="system",
                user_prompt="user",
                provider="ollama",
                settings=Settings(),  # type: ignore[call-arg]
            )

    err = exc_info.value
    assert err.status_code == 502
    assert err.code == "model_behavior_error"
    assert "retries" in err.message.lower() or "model" in err.message.lower()
