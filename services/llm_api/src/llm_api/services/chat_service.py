"""Chat service — plain conversational LLM interaction.

This module handles the business logic for ``POST /v1/chat``.  It differs
from the generator services in that it **never writes a draft file** — it
simply passes the conversation history to the LLM and returns the assistant
reply as a string.

Typical call flow
-----------------
1. ``routes/chat.py`` receives the request and resolves the optional
   ``X-LLM-Provider`` header.
2. ``run_chat()`` is called with the validated ``ChatRequest``.
3. Mock provider is handled inline (no API call, instant response).
4. For real providers, prior turns are folded into the system prompt via
   ``_build_system_prompt()``, and the last user message is the active
   prompt sent to ``build_agent()``.

Developer notes
---------------
- ``_build_system_prompt`` is intentionally public (underscore = internal
  to this module) so it can be unit-tested without running the full LLM stack.
- Settings are instantiated fresh per call so that environment variable
  changes (e.g. in tests) are picked up without restarting the server.
- The mock path short-circuits before calling ``build_agent`` because the
  factory raises ``RuntimeError`` for the mock provider by design.
"""
from __future__ import annotations

import structlog

from llm_api.models.chat import ChatMessage, ChatRequest
from llm_api.providers.factory import build_agent
from llm_api.services.config import Settings
from llm_api.services.errors import ApiError

log = structlog.get_logger(__name__)

_MOCK_RESPONSE = (
    "I'm a mock DM assistant. "
    "Set LLM_PROVIDER to a real provider (ollama, openai, anthropic, gemini) "
    "to get actual responses."
)


def _build_system_prompt(messages: list[ChatMessage]) -> str:
    """Build a system prompt that includes conversation history.

    All messages **except** the final one are baked into the system prompt so
    that the LLM has full context.  The last message is the active user turn
    and is passed directly to ``agent.run()``.

    System-role messages from the request are excluded from the history block
    to avoid duplicating any DM persona instructions.

    Args:
        messages: The full conversation history from the ``ChatRequest``.

    Returns:
        A single string system prompt with a DM persona header and,
        when there are prior turns, a formatted conversation history block.
    """
    parts = ["You are a helpful Dungeon Master assistant for a D&D campaign."]

    # Include prior turns (exclude last message — that's the active user prompt)
    history = [m for m in messages[:-1] if m.role != "system"]
    if history:
        lines = [f"{m.role.capitalize()}: {m.content}" for m in history]
        parts.append("Conversation so far:\n" + "\n".join(lines))

    return "\n\n".join(parts)


async def run_chat(
    request: ChatRequest,
    provider_override: str | None = None,
) -> str:
    """Run a plain chat completion and return the assistant's response text.

    Args:
        request: Validated ``ChatRequest`` containing the message history.
        provider_override: Optional provider name (e.g. from ``X-LLM-Provider``
                           header).  Falls back to ``request.provider``, then
                           the ``LLM_PROVIDER`` env var, then ``"mock"``.

    Returns:
        The assistant's response as a plain string.

    Raises:
        ApiError: ``no_user_message`` (400) if no user turn is found in the
                  history (only relevant for non-mock providers).
        ApiError: ``provider_not_configured`` (400) if the chosen provider
                  lacks a required API key (raised by ``build_agent``).
        ApiError: ``unknown_provider`` (400) if an unrecognised provider name
                  is supplied (raised by ``build_agent``).
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    provider = (
        provider_override or request.provider or settings.llm_provider or "mock"
    ).strip().lower()

    log.info("chat.start", provider=provider, message_count=len(request.messages))

    # Validate before any provider-specific logic so the rule is universal.
    last_user = next(
        (m for m in reversed(request.messages) if m.role == "user"), None
    )
    if last_user is None:
        raise ApiError(
            code="no_user_message",
            message="At least one user message is required.",
            status_code=400,
        )

    if provider == "mock":
        log.debug("chat.mock_response")
        return _MOCK_RESPONSE

    system_prompt = _build_system_prompt(request.messages)
    agent = build_agent(
        output_type=str,
        system_prompt=system_prompt,
        provider_override=provider,
    )

    log.debug("chat.llm_call", prompt_length=len(last_user.content))
    result = await agent.run(last_user.content)
    response_text = str(result.output)

    log.info("chat.done", response_length=len(response_text))
    return response_text
