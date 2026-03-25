# services/llm_api/tests/test_providers_openrouter.py
from __future__ import annotations

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


def test_build_agent_openrouter_missing_key_raises_api_error(monkeypatch):
    """factory.build_agent raises ApiError(400) when OPENROUTER_API_KEY is unset."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from pydantic import BaseModel

    from llm_api.providers.factory import build_agent
    from llm_api.services.errors import ApiError

    class _Out(BaseModel):
        name: str

    with pytest.raises(ApiError) as exc_info:
        build_agent(
            output_type=_Out,
            system_prompt="system",
            provider_override="openrouter",
        )

    err = exc_info.value
    assert err.status_code == 400
    assert err.code == "provider_not_configured"
    assert "OPENROUTER_API_KEY" in err.message


def test_build_agent_openrouter_returns_agent_when_key_present(monkeypatch):
    """factory.build_agent returns a pydantic_ai Agent when OPENROUTER_API_KEY is set."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

    from pydantic import BaseModel
    from pydantic_ai import Agent

    from llm_api.providers.factory import build_agent

    class _Out(BaseModel):
        name: str

    agent = build_agent(
        output_type=_Out,
        system_prompt="system",
        provider_override="openrouter",
    )
    assert isinstance(agent, Agent)


def test_settings_expose_openrouter_fields(monkeypatch):
    """Settings correctly reads all three OPENROUTER_* env vars."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

    from llm_api.services.config import Settings

    s = Settings()  # type: ignore[call-arg]
    assert s.openrouter_api_key == "sk-or-test"
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert s.openrouter_model == "google/gemini-2.5-flash"
