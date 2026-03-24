"""Chat route — POST /v1/chat.

Handles plain conversational chat for the widget's Ask mode.  No draft is
written; the LLM response is returned directly in the standard
``{request_id, data}`` envelope.

Endpoint
--------
``POST /v1/chat``

Request body (JSON):

.. code-block:: json

    {
        "messages": [
            {"role": "user", "content": "Describe a goblin warcamp."}
        ],
        "provider": "openai"
    }

Success response (200 OK):

.. code-block:: json

    {
        "request_id": "...",
        "data": {
            "message": {
                "role": "assistant",
                "content": "The goblin warcamp sprawls..."
            }
        }
    }

Optional headers
----------------
- ``X-LLM-Provider`` — Override the server's default LLM provider for this
  single request (e.g. ``"ollama"``, ``"openai"``).
- ``X-API-Key`` — Required unless ``RELAX_AUTH_ON_LOCALHOST=true``.

Error codes
-----------
- ``no_user_message`` (400) — All messages are system-role; no user turn found.
- ``provider_not_configured`` (400) — Chosen provider missing an API key.
- ``rate_limited`` (429) — Global rate limit exceeded.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from llm_api.models.chat import ChatRequest
from llm_api.services.chat_service import run_chat
from llm_api.services.limits import get_limits
from llm_api.services.responses import ok
from llm_api.services.security import require_api_key

router = APIRouter()


@router.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(
    req: ChatRequest,
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
):
    """Run a plain chat completion and return the assistant's reply.

    Args:
        req: Validated request body containing the conversation history.
        x_llm_provider: Optional provider override from the ``X-LLM-Provider``
                        request header.

    Returns:
        JSON response with ``data.message`` containing ``role`` and ``content``.
    """
    limits = get_limits()
    async with limits.guard():
        response_text = await run_chat(req, provider_override=x_llm_provider)

    return ok({"message": {"role": "assistant", "content": response_text}})
