# Fix NPC Summary Validation & Add OpenRouter Provider

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the `UnexpectedModelBehavior` crash when llama3.2 returns a function-call-style JSON instead of a flat `NpcOutput` object, then wire OpenRouter (`google/gemini-2.5-flash`) as a selectable provider.

**Architecture:** Two independent changes. Part A patches `generators/base.py` (catch the exception, raise `ApiError`) and `generators/npc.py` (clearer prompt with a concrete JSON example). Part B adds three settings to `config.py`, one new `if` branch in `providers/factory.py`, and env file updates — all using pydantic_ai's existing OpenAI-compatible provider mechanism; no custom HTTP client needed.

**Tech Stack:** Python 3.12, pydantic-ai, pydantic-settings, structlog, pytest-asyncio, unittest.mock

---

## Part A: Fix NPC summary validation

### Task 1: Write a failing test for `UnexpectedModelBehavior` → `ApiError` conversion

**Files:**
- Modify: `services/llm_api/tests/test_generators_base.py`

**Step 1: Open the test file and append the new test**

```python
# services/llm_api/tests/test_generators_base.py  (append at end)
import os
import pytest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "ollama")


@pytest.mark.asyncio
async def test_run_generation_converts_unexpected_model_behavior_to_api_error():
    """UnexpectedModelBehavior must become a 502 ApiError, not bubble as 500."""
    from pydantic_ai.exceptions import UnexpectedModelBehavior
    from pydantic import BaseModel
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
```

**Step 2: Run the test — expect FAIL**

```bash
cd services/llm_api
pytest tests/test_generators_base.py::test_run_generation_converts_unexpected_model_behavior_to_api_error -v
```

Expected: `FAILED` — `ApiError` not raised, raw `UnexpectedModelBehavior` propagates.

---

### Task 2: Catch `UnexpectedModelBehavior` in `run_generation`

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/base.py:54-110`

**Step 3: Add the import and except block**

In `base.py`, add `UnexpectedModelBehavior` to the pydantic_ai import line and add an `except` clause inside `run_generation`:

```python
# Change this import line (around line 16):
from pydantic_ai import UsageLimitExceeded, UsageLimits
# to:
from pydantic_ai import UsageLimitExceeded, UsageLimits
from pydantic_ai.exceptions import UnexpectedModelBehavior
```

Then in `run_generation`, after the `except UsageLimitExceeded` block, add:

```python
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
```

**Step 4: Run the test — expect PASS**

```bash
pytest tests/test_generators_base.py::test_run_generation_converts_unexpected_model_behavior_to_api_error -v
```

Expected: `PASSED`

**Step 5: Run the full base test suite to check for regressions**

```bash
pytest tests/test_generators_base.py -v
```

Expected: all PASSED.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/base.py \
        services/llm_api/tests/test_generators_base.py
git commit -m "fix: convert UnexpectedModelBehavior to 502 ApiError in run_generation"
```

---

### Task 3: Strengthen the legacy NPC user prompt

**Background:** llama3.2 returns `{"name": "generate_npc", "parameters": {...}}` (a function-call shape) instead of the flat `{"name": "...", "summary": "...", "tags": [...]}` shape pydantic_ai expects. The fix is to make the prompt explicit about the exact JSON structure with a concrete example.

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/npc.py`
- Modify: `services/llm_api/tests/test_generator_npc.py`

**Step 1: Write a failing unit test that asserts the prompt contains an example**

The clearest way to catch prompt regressions is to intercept `run_generation` and inspect the `user_prompt` argument:

```python
# services/llm_api/tests/test_generator_npc.py  (append at end)

@pytest.mark.asyncio
async def test_legacy_user_prompt_includes_json_example_and_field_names():
    """The legacy user_prompt must contain the expected output field names and a
    concrete JSON example so small models do not return function-call shapes."""
    from unittest.mock import AsyncMock, patch
    from llm_api.generators.npc import generate_npc, NpcOutput
    from llm_api.models.requests import GenerateRequest

    captured: dict = {}

    async def _fake_run_generation(**kwargs):
        captured["user_prompt"] = kwargs["user_prompt"]
        # Return a valid NpcOutput so the generator can continue
        return NpcOutput(
            name="Test NPC",
            summary="A test NPC for unit testing.",
            tags=["test"],
        )

    with patch("llm_api.generators.npc.run_generation", side_effect=_fake_run_generation):
        req = GenerateRequest(prompt="generate a 2nd level paladin", title="")
        await generate_npc(request=req, campaign="test-campaign", provider_override="ollama")

    prompt = captured["user_prompt"]
    assert '"name"' in prompt, 'prompt must include "name" field example'
    assert '"summary"' in prompt, 'prompt must include "summary" field example'
    assert '"tags"' in prompt, 'prompt must include "tags" field example'
    assert "JSON" in prompt.upper(), "prompt must explicitly mention JSON"
```

**Step 2: Run the test — expect FAIL**

```bash
pytest tests/test_generator_npc.py::test_legacy_user_prompt_includes_json_example_and_field_names -v
```

Expected: `FAILED` — the assertions about `"name"`, `"summary"`, `"tags"`, and `"JSON"` in the prompt will fail because the current prompt reads `"Return: name (full), summary (markdown), tags (list)."`.

**Step 3: Update the legacy `user_prompt` string in `npc.py`**

Locate this block in `npc.py` (around line 186–190, the legacy path under `# ── Legacy path`):

```python
        user_prompt = (
            f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
            "Return: name (full), summary (markdown), tags (list)."
        )
```

Replace it with:

```python
        user_prompt = (
            f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
            "Respond with ONLY a JSON object (no markdown fences, no function-call wrapper).\n"
            "Required top-level fields:\n"
            '  "name"    — full NPC name (non-empty string)\n'
            '  "summary" — 1–3 paragraph markdown description (non-empty string)\n'
            '  "tags"    — list of 2–5 short descriptor strings\n\n'
            "Example:\n"
            '{"name": "Aldric the Grey", '
            '"summary": "A weathered elven wizard who guards the northern pass. '
            'He speaks little but carries ancient secrets.", '
            '"tags": ["wizard", "elf", "mysterious"]}'
        )
```

**Step 4: Run the test — expect PASS**

```bash
pytest tests/test_generator_npc.py::test_legacy_user_prompt_includes_json_example_and_field_names -v
```

Expected: `PASSED`

**Step 5: Run the full NPC test suite**

```bash
pytest tests/test_generator_npc.py -v
```

Expected: all PASSED.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/npc.py \
        services/llm_api/tests/test_generator_npc.py
git commit -m "fix: clarify legacy NPC user_prompt to prevent function-call-style responses"
```

---

## Part B: Add OpenRouter provider

> OpenRouter exposes an OpenAI-compatible API (`https://openrouter.ai/api/v1`).
> pydantic_ai's `OpenAIChatModel` + `OpenAIProvider` already handles the full
> request/response cycle including streaming. No custom HTTP client is needed.

### Task 4: Write failing tests for the OpenRouter factory branch

**Files:**
- Create: `services/llm_api/tests/test_providers_openrouter.py`

**Step 1: Create the test file**

```python
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
```

**Step 2: Run the tests — expect FAIL**

```bash
pytest tests/test_providers_openrouter.py -v
```

Expected: all three tests `FAILED` — `openrouter_api_key` attribute doesn't exist on `Settings` and there is no `openrouter` branch in `factory.py`.

---

### Task 5: Add OpenRouter settings to `config.py`

**Files:**
- Modify: `services/llm_api/src/llm_api/services/config.py`

**Step 1: Add the three new fields after the `gemini_model` line**

```python
    # OpenRouter (OpenAI-compatible proxy)
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash",
        alias="OPENROUTER_MODEL",
    )
```

**Step 2: Run the settings test only — expect PASS**

```bash
pytest tests/test_providers_openrouter.py::test_settings_expose_openrouter_fields -v
```

Expected: `PASSED`

---

### Task 6: Add the `openrouter` branch to `factory.py`

**Files:**
- Modify: `services/llm_api/src/llm_api/providers/factory.py`

**Step 1: Add the branch**

After the `if provider == "gemini":` block and before the `if provider == "mock":` block, insert:

```python
    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ApiError(
                code="provider_not_configured",
                message="OPENROUTER_API_KEY is required when provider=openrouter",
                status_code=400,
            )
        model = OpenAIChatModel(
            settings.openrouter_model,
            provider=OpenAIProvider(
                base_url=settings.openrouter_base_url.rstrip("/"),
                api_key=settings.openrouter_api_key,
            ),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)
```

**Step 2: Run all three provider tests — expect PASS**

```bash
pytest tests/test_providers_openrouter.py -v
```

Expected: all three `PASSED`

**Step 3: Run the full test suite to check no regressions**

```bash
pytest -v
```

Expected: all previously passing tests still PASS.

**Step 4: Commit**

```bash
git add services/llm_api/src/llm_api/services/config.py \
        services/llm_api/src/llm_api/providers/factory.py \
        services/llm_api/tests/test_providers_openrouter.py
git commit -m "feat: add openrouter provider (OpenAI-compatible, default google/gemini-2.5-flash)"
```

---

### Task 7: Update `.env.example` and `docker-compose.yml`

**Files:**
- Modify: `services/llm_api/.env.example`
- Modify: `docker-compose.yml`

**Step 1: Add OpenRouter env block to `.env.example`**

After the `# GEMINI_MODEL=...` line, append:

```env
# OpenRouter (OpenAI-compatible proxy — supports google/gemini-2.5-flash etc.)
# OPENROUTER_API_KEY=
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# OPENROUTER_MODEL=google/gemini-2.5-flash
```

**Step 2: Add OpenRouter env vars to `docker-compose.yml`**

In the `api` service's `environment:` section, after the last `GEMINI_*` line, add:

```yaml
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
      - OPENROUTER_MODEL=${OPENROUTER_MODEL:-google/gemini-2.5-flash}
```

> The `:-` default syntax keeps the value blank if unset so the API stays in `mock` mode without a key.

**Step 3: Verify docker compose config parses cleanly**

```bash
docker compose config --quiet
```

Expected: exits with code 0, no YAML errors.

**Step 4: Commit**

```bash
git add services/llm_api/.env.example docker-compose.yml
git commit -m "chore: add OPENROUTER_* env vars to .env.example and docker-compose"
```

---

### Task 8: Update `services/llm_api/README.md`

**Files:**
- Modify: `services/llm_api/README.md`

**Step 1: Add an OpenRouter section under the providers table**

Find the providers documentation section (the table or list that describes `LLM_PROVIDER` values) and add a row or bullet:

```markdown
| `openrouter` | `OPENROUTER_API_KEY` | `OPENROUTER_MODEL` (default `google/gemini-2.5-flash`) | OpenRouter proxy — OpenAI-compatible |
```

**Step 2: Add a quick `curl` example**

Under the examples section, add:

```bash
# Generate an NPC via OpenRouter / Gemini 2.5 Flash
curl -X POST 'http://localhost:8000/v1/generate/npc' \
  -H 'X-API-Key: your_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "campaign": "my-campaign",
    "slug": "gemini-paladin",
    "fields": {},
    "provider": "openrouter"
  }'
```

**Step 3: Commit**

```bash
git add services/llm_api/README.md
git commit -m "docs: add OpenRouter provider to README with curl example"
```

---

## Verification checklist (run after all tasks complete)

```bash
# 1. Full Python test suite
cd services/llm_api && pytest -v

# 2. Smoke the API (mock mode, no real provider needed)
docker compose up -d --build api && sleep 3
bash scripts/smoke-api

# 3. Manual OpenRouter test (requires real key in .env)
# Set OPENROUTER_API_KEY in .env, then:
curl -X POST 'http://localhost:8000/v1/generate/npc' \
  -H 'X-API-Key: dev-key' \
  -H 'Content-Type: application/json' \
  -d '{"campaign":"rpg-theForsakenCrown","slug":"test-paladin","fields":{"type":"2nd level paladin"},"provider":"openrouter"}'
# Expected: 200 JSON with non-empty "summary" field

# 4. UI integration test
npm run test:ui
```

---

## Quick reference: key file locations

| Purpose | File |
|---|---|
| Generator entry point | `services/llm_api/src/llm_api/generators/npc.py` |
| Shared generation runner | `services/llm_api/src/llm_api/generators/base.py` |
| Provider factory | `services/llm_api/src/llm_api/providers/factory.py` |
| Settings / env vars | `services/llm_api/src/llm_api/services/config.py` |
| Error types | `services/llm_api/src/llm_api/services/errors.py` |
| NPC tests | `services/llm_api/tests/test_generator_npc.py` |
| Base generator tests | `services/llm_api/tests/test_generators_base.py` |
| New OpenRouter tests | `services/llm_api/tests/test_providers_openrouter.py` |
| Env example | `services/llm_api/.env.example` |
| Docker compose | `docker-compose.yml` |
