from __future__ import annotations

import os
import pytest
from pydantic import ValidationError

os.environ.setdefault("LLM_API_KEY", "test-key")


def test_chat_message_valid_roles():
    from llm_api.models.chat import ChatMessage
    for role in ("user", "assistant", "system"):
        msg = ChatMessage(role=role, content="hello")
        assert msg.role == role


def test_chat_message_invalid_role():
    from llm_api.models.chat import ChatMessage
    with pytest.raises(ValidationError):
        ChatMessage(role="bot", content="hello")


def test_chat_message_content_cannot_be_empty():
    from llm_api.models.chat import ChatMessage
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="")


def test_chat_request_requires_at_least_one_message():
    from llm_api.models.chat import ChatRequest
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])


def test_chat_request_valid():
    from llm_api.models.chat import ChatRequest, ChatMessage
    req = ChatRequest(messages=[ChatMessage(role="user", content="Hello DM!")])
    assert len(req.messages) == 1


def test_chat_request_optional_provider_defaults_none():
    from llm_api.models.chat import ChatRequest, ChatMessage
    req = ChatRequest(messages=[ChatMessage(role="user", content="test")])
    assert req.provider is None


def test_chat_request_provider_can_be_set():
    from llm_api.models.chat import ChatRequest, ChatMessage
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        provider="openai",
    )
    assert req.provider == "openai"
