"""Chat domain models.

Defines the request/response shapes for the POST /v1/chat endpoint.
These are kept separate from GenerateRequest to isolate the plain-chat
domain from the draft-generation domain.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in a conversation.

    Attributes:
        role: Who sent the message — ``user``, ``assistant``, or ``system``.
        content: The message body. Must be non-empty (max 20 000 chars).
    """

    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    """Payload for ``POST /v1/chat``.

    Attributes:
        messages: Ordered conversation history. Must contain at least one
                  message; capped at 50 to prevent oversized prompts.
        provider: Optional provider override (e.g. ``"openai"``). When
                  ``None`` the server falls back to the ``LLM_PROVIDER``
                  env var, then ``"mock"``.
    """

    messages: list[ChatMessage] = Field(..., min_length=1, max_length=50)
    # Optional provider override. If None, the server's LLM_PROVIDER env var is used.
    provider: str | None = None
