# Chat Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a `/v1/chat` endpoint for plain conversational chat (Ask mode in the widget), after enhancing config, logging, and error services with developer-experience improvements.

**Architecture:** Phase 1 enhances three existing prerequisite services in-place (backward-compatible, minimal changes). Phase 2 adds `routes/chat.py` + `services/chat_service.py` + `models/chat.py` — no draft writing, no YAML, just LLM conversation routed through the existing provider factory.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pydantic-settings, pydantic-ai, structlog (ConsoleRenderer for dev / JSONRenderer for prod), pytest, httpx.

---

## Files to read before starting

- `services/llm_api/src/llm_api/services/config.py` — Pydantic Settings, env var aliases
- `services/llm_api/src/llm_api/services/logging.py` — structlog configuration
- `services/llm_api/src/llm_api/services/errors.py` — ApiError, install_exception_handlers
- `services/llm_api/src/llm_api/providers/factory.py` — build_agent signature
- `services/llm_api/src/llm_api/app.py` — router registration pattern
- `services/llm_api/src/llm_api/routes/generate.py` — route pattern to copy
- `services/llm_api/tests/conftest.py` — shared fixtures (currently empty)

---

## GitHub / branch convention

Before starting any code, follow this workflow:

1. Create a GitHub issue titled: `feat: add chat service with config/logging/error prerequisites`
2. Note the issue number (e.g., `#15`)
3. Create branch: `git checkout -b 15-feat-chat-service`
4. All commits use Conventional Commits format: `feat:`, `test:`, `refactor:`, `docs:`

---

## Phase 1 — Prerequisite Service Enhancements

---

### Task 1: Add APP_ENV to config service

**Why:** Logging and error behavior need to differ between dev and production. No value is hardcoded — it comes from the `APP_ENV` env var (default: `development`).

**Files:**
- Modify: `services/llm_api/src/llm_api/services/config.py`
- Create: `services/llm_api/tests/test_config.py`

---

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_config.py
from __future__ import annotations

import os
import pytest

# Ensure required env vars are set before importing Settings
os.environ.setdefault("LLM_API_KEY", "test-key")


def test_app_env_defaults_to_development():
    from llm_api.services.config import Settings
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.app_env == "development"


def test_app_env_reads_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    # Force a fresh Settings instance (pydantic-settings reads env at init)
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    assert s.app_env == "production"
    monkeypatch.delenv("APP_ENV", raising=False)


def test_is_production_false_by_default():
    from llm_api.services.config import Settings
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.is_production is False


def test_is_production_true_when_set(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    assert s.is_production is True
    monkeypatch.delenv("APP_ENV", raising=False)
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_config.py -v
```

Expected: `FAILED` — `Settings` has no `app_env` attribute.

**Step 3: Add `app_env` to Settings**

Add these two items to `services/llm_api/src/llm_api/services/config.py` inside the `Settings` class, after the `debug_prompts` field:

```python
    # Environment: "development" | "staging" | "production"
    app_env: str = Field(default="development", alias="APP_ENV")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"
```

**Step 4: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_config.py -v
```

Expected: `4 passed`

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/services/config.py \
        services/llm_api/tests/test_config.py
git commit -m "feat(config): add APP_ENV setting with is_production property"
```

---

### Task 2: Color-coded console logging

**Why:** JSON logs are hard to read locally. Dev mode should emit human-readable, color-coded output. Production keeps JSON for log aggregators. No new packages needed — `structlog.dev.ConsoleRenderer` is bundled with structlog.

**Files:**
- Modify: `services/llm_api/src/llm_api/services/logging.py`
- Create: `services/llm_api/tests/test_logging.py`

---

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_logging.py
from __future__ import annotations

import os
import logging

import structlog

os.environ.setdefault("LLM_API_KEY", "test-key")


def _make_settings(app_env: str = "development"):
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    os.environ["APP_ENV"] = app_env
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    os.environ.pop("APP_ENV", None)
    return s


def test_configure_logging_dev_does_not_raise():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("development")
    configure_logging(settings)  # must not raise


def test_configure_logging_prod_does_not_raise():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("production")
    configure_logging(settings)  # must not raise


def test_dev_logging_uses_console_renderer():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("development")
    configure_logging(settings)
    # ConsoleRenderer is used in dev — structlog config should have it
    config = structlog.get_config()
    processor_types = [type(p).__name__ for p in config["processors"]]
    assert "ConsoleRenderer" in processor_types


def test_prod_logging_uses_json_renderer():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("production")
    configure_logging(settings)
    config = structlog.get_config()
    processor_types = [type(p).__name__ for p in config["processors"]]
    assert "JSONRenderer" in processor_types
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_logging.py -v
```

Expected: `FAILED` — `ConsoleRenderer` / `JSONRenderer` checks fail because current code always uses JSONRenderer.

**Step 3: Replace `configure_logging` implementation**

Replace the entire content of `services/llm_api/src/llm_api/services/logging.py`:

```python
from __future__ import annotations

import logging

import structlog

from llm_api.services.config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level)

    if settings.is_production:
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_logging.py -v
```

Expected: `4 passed`

**Step 5: Smoke-test color output manually**

```bash
cd services/llm_api
LLM_API_KEY=dev APP_ENV=development python -c "
from llm_api.services.config import Settings
from llm_api.services.logging import configure_logging
import structlog
s = Settings()
configure_logging(s)
log = structlog.get_logger('smoke')
log.info('logging smoke test', env=s.app_env, color='yes')
"
```

Expected: A colored, human-readable log line with timestamp, level, and key=value pairs.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/services/logging.py \
        services/llm_api/tests/test_logging.py
git commit -m "feat(logging): add color-coded ConsoleRenderer for dev, keep JSON for prod"
```

---

### Task 3: Dev/prod stack trace behavior in error service

**Why:** In development, the 500 response should include the exception message in `details.debug` so developers see the problem immediately without scanning logs. In production, `details` is empty — no internal info leaks to users.

**Files:**
- Modify: `services/llm_api/src/llm_api/services/errors.py`
- Modify: `services/llm_api/src/llm_api/app.py` (pass `settings` to `install_exception_handlers`)
- Create: `services/llm_api/tests/test_errors.py`

---

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_errors.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")


def _make_client(app_env: str):
    """Build a TestClient with the given APP_ENV."""
    os.environ["APP_ENV"] = app_env
    # Re-import to pick up env var changes
    import importlib
    import llm_api.services.config as config_mod
    import llm_api.app as app_mod
    importlib.reload(config_mod)
    importlib.reload(app_mod)
    from fastapi.testclient import TestClient
    app = app_mod.create_app()
    os.environ.pop("APP_ENV", None)
    return TestClient(app, raise_server_exceptions=False)


def test_api_error_returns_structured_json():
    client = _make_client("development")
    # /v1/generate/unknown-kind should raise an ApiError (no active campaign)
    resp = client.post("/v1/generate/npc", json={"prompt": "test"})
    # Will fail with no active campaign — still a 4xx ApiError
    assert resp.status_code in (400, 404, 422)
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]


def test_500_in_dev_includes_debug_details(monkeypatch):
    """In dev mode, unhandled exceptions expose exception message in details.debug."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from llm_api.services.errors import install_exception_handlers
    from llm_api.services.config import Settings

    os.environ["APP_ENV"] = "development"
    import importlib
    import llm_api.services.config as cfg
    importlib.reload(cfg)
    settings = cfg.Settings()  # pyright: ignore[reportCallIssue]

    app = FastAPI()
    install_exception_handlers(app, settings)

    @app.get("/boom")
    def boom():
        raise ValueError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert "debug" in body["error"]["details"]
    assert "secret internal detail" in body["error"]["details"]["debug"]
    os.environ.pop("APP_ENV", None)


def test_500_in_production_hides_debug_details(monkeypatch):
    """In production, unhandled exceptions return a generic message with no internal info."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from llm_api.services.errors import install_exception_handlers

    os.environ["APP_ENV"] = "production"
    import importlib
    import llm_api.services.config as cfg
    importlib.reload(cfg)
    settings = cfg.Settings()  # pyright: ignore[reportCallIssue]

    app = FastAPI()
    install_exception_handlers(app, settings)

    @app.get("/boom")
    def boom():
        raise ValueError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["details"] == {}
    assert "secret internal detail" not in resp.text
    os.environ.pop("APP_ENV", None)
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_errors.py -v
```

Expected: `FAILED` — `install_exception_handlers` doesn't accept a `settings` arg yet.

**Step 3: Update `install_exception_handlers` to accept settings**

Replace the entire content of `services/llm_api/src/llm_api/services/errors.py`:

```python
from __future__ import annotations

import traceback
from dataclasses import dataclass

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict | None = None


def _request_id() -> str | None:
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("request_id")


def install_exception_handlers(app: FastAPI, settings=None) -> None:
    """Install exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
        settings: Optional Settings instance. When provided, dev mode
                  (settings.is_production == False) includes exception
                  details in 500 responses to aid local debugging.
    """
    is_production = getattr(settings, "is_production", True)

    def _json_sanitize(value):
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {k: _json_sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_sanitize(v) for v in value]
        if isinstance(value, tuple):
            return [_json_sanitize(v) for v in value]
        if isinstance(value, set):
            return [_json_sanitize(v) for v in value]
        return value

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or {},
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        errors = _json_sanitize(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        log = structlog.get_logger(__name__)
        log.exception("Unhandled exception")

        # In development, expose the exception message (not stack trace) to
        # help developers diagnose issues without scanning server logs.
        # In production, details are always empty to avoid leaking internals.
        details: dict = {}
        if not is_production:
            details["debug"] = str(exc)

        return JSONResponse(
            status_code=500,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": details,
                },
            },
        )
```

**Step 4: Pass settings to `install_exception_handlers` in app.py**

In `services/llm_api/src/llm_api/app.py`, change line:

```python
install_exception_handlers(app)
```

to:

```python
install_exception_handlers(app, settings)
```

**Step 5: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_errors.py -v
```

Expected: `3 passed`

**Step 6: Run full test suite to confirm nothing regressed**

```bash
cd services/llm_api
pytest -v
```

Expected: all previously passing tests still pass.

**Step 7: Commit**

```bash
git add services/llm_api/src/llm_api/services/errors.py \
        services/llm_api/src/llm_api/app.py \
        services/llm_api/tests/test_errors.py
git commit -m "feat(errors): expose exception message in dev 500 responses, hide in production"
```

---

## Phase 2 — Chat Service

---

### Task 4: ChatMessage and ChatRequest models

**Why:** A dedicated model file keeps the chat domain separate from the existing `GenerateRequest`. Validation rules (max messages, max content length) are defined here.

**Files:**
- Create: `services/llm_api/src/llm_api/models/chat.py`
- Create: `services/llm_api/tests/test_chat_models.py`

---

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_chat_models.py
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
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_chat_models.py -v
```

Expected: `FAILED` — `llm_api.models.chat` does not exist.

**Step 3: Create the models file**

```python
# services/llm_api/src/llm_api/models/chat.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=50)
    # Optional provider override. If None, the server's LLM_PROVIDER env var is used.
    provider: str | None = None
```

**Step 4: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_chat_models.py -v
```

Expected: `7 passed`

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/models/chat.py \
        services/llm_api/tests/test_chat_models.py
git commit -m "feat(chat): add ChatMessage and ChatRequest Pydantic models"
```

---

### Task 5: Chat service logic

**Why:** Business logic lives in `services/`, not in routes. The chat service resolves the provider, handles the mock path inline, formats conversation history into a system prompt, and delegates to the existing `build_agent` factory.

**Files:**
- Create: `services/llm_api/src/llm_api/services/chat_service.py`
- Create: `services/llm_api/tests/test_chat_service.py`

---

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_chat_service.py
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
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_chat_service.py -v
```

Expected: `FAILED` — `llm_api.services.chat_service` does not exist.

**Step 3: Create the chat service**

```python
# services/llm_api/src/llm_api/services/chat_service.py
"""Chat service — plain conversational LLM interaction (no draft writing)."""
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
    """Build a system prompt that includes conversation history (all but last message)."""
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
        request: Validated ChatRequest containing the message history.
        provider_override: Optional provider name from the X-LLM-Provider header.
                           Falls back to request.provider, then LLM_PROVIDER env var.

    Returns:
        The assistant's response as a plain string.

    Raises:
        ApiError: If no user message is found, or if the provider is unknown/misconfigured.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    provider = (
        provider_override or request.provider or settings.llm_provider or "mock"
    ).strip().lower()

    log.info("chat.start", provider=provider, message_count=len(request.messages))

    if provider == "mock":
        log.debug("chat.mock_response")
        return _MOCK_RESPONSE

    last_user = next(
        (m for m in reversed(request.messages) if m.role == "user"), None
    )
    if last_user is None:
        raise ApiError(
            code="no_user_message",
            message="At least one user message is required.",
            status_code=400,
        )

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
```

**Step 4: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_chat_service.py -v
```

Expected: `4 passed`

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/services/chat_service.py \
        services/llm_api/tests/test_chat_service.py
git commit -m "feat(chat): add chat_service with mock provider and history formatting"
```

---

### Task 6: Chat route

**Why:** The widget POSTs to `/v1/chat` in Ask mode. This route accepts the message array, enforces rate limits via the existing `limits.guard()`, delegates to `run_chat`, and returns the response in the standard `{request_id, data}` envelope.

**Files:**
- Create: `services/llm_api/src/llm_api/routes/chat.py`
- Create: `services/llm_api/tests/test_chat_route.py`

---

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_chat_route.py
from __future__ import annotations

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("RELAX_AUTH_ON_LOCALHOST", "true")

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from llm_api.app import create_app
    app = create_app()
    return TestClient(app)


def test_chat_returns_200(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "What is a goblin?"}]},
    )
    assert resp.status_code == 200


def test_chat_response_has_message_key(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Describe the dungeon."}]},
    )
    body = resp.json()
    assert "data" in body
    assert "message" in body["data"]


def test_chat_message_has_role_and_content(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Tell me about orcs."}]},
    )
    msg = resp.json()["data"]["message"]
    assert msg["role"] == "assistant"
    assert isinstance(msg["content"], str)
    assert len(msg["content"]) > 0


def test_chat_response_has_request_id(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    body = resp.json()
    assert "request_id" in body


def test_chat_empty_messages_returns_422(client):
    resp = client.post("/v1/chat", json={"messages": []})
    assert resp.status_code == 422


def test_chat_missing_messages_returns_422(client):
    resp = client.post("/v1/chat", json={})
    assert resp.status_code == 422


def test_chat_provider_override_via_header(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"X-LLM-Provider": "mock"},
    )
    assert resp.status_code == 200
```

**Step 2: Run tests to verify they fail**

```bash
cd services/llm_api
pytest tests/test_chat_route.py -v
```

Expected: `FAILED` — `POST /v1/chat` returns 404.

**Step 3: Create the chat route**

```python
# services/llm_api/src/llm_api/routes/chat.py
"""Chat route — POST /v1/chat for plain conversational LLM interaction."""
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
    limits = get_limits()
    async with limits.guard():
        response_text = await run_chat(req, provider_override=x_llm_provider)

    return ok({"message": {"role": "assistant", "content": response_text}})
```

**Step 4: Run tests to verify they fail** (route not registered yet)

```bash
cd services/llm_api
pytest tests/test_chat_route.py -v
```

Expected: still `FAILED` — router not registered in `app.py`.

**Step 5: Register the chat router in app.py**

In `services/llm_api/src/llm_api/app.py`, add the import at the top alongside the other router imports:

```python
from llm_api.routes.chat import router as chat_router
```

Then add the include call after the existing `app.include_router(promote_router, ...)` line:

```python
app.include_router(chat_router, prefix="/v1")
```

**Step 6: Run tests to verify they pass**

```bash
cd services/llm_api
pytest tests/test_chat_route.py -v
```

Expected: `7 passed`

**Step 7: Run the full test suite**

```bash
cd services/llm_api
pytest -v
```

Expected: all tests pass. Count should be higher than before.

**Step 8: Commit**

```bash
git add services/llm_api/src/llm_api/routes/chat.py \
        services/llm_api/src/llm_api/app.py \
        services/llm_api/tests/test_chat_route.py
git commit -m "feat(chat): add POST /v1/chat route and register in app"
```

---

### Task 7: Documentation and PR

**Step 1: Update the LLM API README**

Open `services/llm_api/README.md`. Add a section for the chat endpoint after the existing endpoint documentation:

```markdown
### Chat endpoint

**POST /v1/chat**

Plain conversational chat — no draft is written, no active campaign required.

Request:
```json
{
  "messages": [
    {"role": "user", "content": "Describe a goblin warcamp."}
  ],
  "provider": "openai"
}
```

Response (`200 OK`):
```json
{
  "request_id": "...",
  "data": {
    "message": {
      "role": "assistant",
      "content": "The goblin warcamp sprawls..."
    }
  }
}
```

Headers:
- `X-LLM-Provider: <provider>` — override the server's default provider for this request.
- `X-API-Key: <key>` — required unless `RELAX_AUTH_ON_LOCALHOST=true`.

Error codes: `no_user_message` (400), `provider_not_configured` (400), `rate_limited` (429).
```

**Step 2: Run the smoke-api script to verify the live endpoint**

```bash
# Start the server in one terminal:
cd services/llm_api
LLM_API_KEY=dev LLM_PROVIDER=mock uvicorn llm_api.app:create_app --factory --reload --port 8000

# In another terminal:
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello DM!"}]}' | python3 -m json.tool
```

Expected: JSON response with `data.message.role == "assistant"` and a non-empty `content`.

**Step 3: Commit docs**

```bash
git add services/llm_api/README.md
git commit -m "docs(chat): document POST /v1/chat endpoint in README"
```

**Step 4: Push and open PR**

```bash
git push -u origin 15-feat-chat-service
gh pr create \
  --title "feat: add chat service with config/logging/error prerequisites" \
  --body "$(cat <<'EOF'
## Summary
- Adds `APP_ENV` setting to config service (drives dev/prod behavior throughout)
- Enhances logging service: ConsoleRenderer with colors in dev, JSON in prod
- Enhances error service: exposes exception message in 500 details during dev, hides in production
- Adds `POST /v1/chat` endpoint for plain conversational chat (Ask mode in widget)
- Chat service routes through existing `build_agent` provider factory; mock provider works out of the box

## Test plan
- [ ] `pytest -v` from `services/llm_api/` — all tests pass
- [ ] Start server with `LLM_PROVIDER=mock`, POST to `/v1/chat`, verify mock response
- [ ] Set `APP_ENV=development`, trigger a 500, verify `details.debug` appears
- [ ] Set `APP_ENV=production`, trigger a 500, verify `details` is empty
- [ ] Start server without `APP_ENV`, check console — colored human-readable output expected
- [ ] Set `APP_ENV=production`, start server — JSON log output expected

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Quick reference: all test commands

```bash
cd services/llm_api

# Individual task tests
pytest tests/test_config.py -v
pytest tests/test_logging.py -v
pytest tests/test_errors.py -v
pytest tests/test_chat_models.py -v
pytest tests/test_chat_service.py -v
pytest tests/test_chat_route.py -v

# Full suite
pytest -v

# Lint
ruff check src/ tests/
```

---

## Environment variables introduced

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Controls dev vs production behavior (logging format, error details) |

All other variables were already in `config.py` and remain unchanged.
