from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_run_chat_mock_returns_string():
    from llm_api.models.chat import ChatMessage, ChatRequest
    from llm_api.services.chat_service import run_chat

    req = ChatRequest(messages=[ChatMessage(role="user", content="What is a goblin?")])
    result = await run_chat(req)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_run_chat_mock_provider_override():
    from llm_api.models.chat import ChatMessage, ChatRequest
    from llm_api.services.chat_service import run_chat

    req = ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
    result = await run_chat(req, provider_override="mock")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_run_chat_raises_on_no_user_message():
    from llm_api.models.chat import ChatMessage, ChatRequest
    from llm_api.services.chat_service import run_chat
    from llm_api.services.errors import ApiError

    # System-only message — no user message
    req = ChatRequest(
        messages=[ChatMessage(role="system", content="You are a DM.")],
        provider="mock",
    )
    with pytest.raises(ApiError) as exc_info:
        await run_chat(req)
    assert exc_info.value.code == "no_user_message"


@pytest.mark.asyncio
async def test_build_system_prompt_includes_history():
    from llm_api.models.chat import ChatMessage
    from llm_api.services.chat_service import _build_system_prompt

    messages = [
        ChatMessage(role="user", content="First question"),
        ChatMessage(role="assistant", content="First answer"),
        ChatMessage(role="user", content="Second question"),
    ]
    prompt = _build_system_prompt(messages)
    assert "First question" in prompt
    assert "First answer" in prompt
    # Last message should NOT be in system prompt (it's the active user turn)
    assert "Second question" not in prompt
