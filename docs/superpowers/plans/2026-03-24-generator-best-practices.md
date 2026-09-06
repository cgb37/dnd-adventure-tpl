# Generator Service Best Practices Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the existing D&D resource generator service to eliminate duplication, add structured logging, add docstrings, add unit tests, and remove manual double-registration in dispatch.

**Architecture:** Extract shared LLM-call boilerplate from the five generator files into a single `run_generation()` helper in `base.py`. Add `structlog` logging to all generators following the `chat_service.py` pattern. Convert `dispatch.py` from a manual `match` block to a data-driven registry so adding a new generator only requires one change.

**Tech Stack:** Python 3.12, FastAPI, pydantic-ai, structlog, pytest, pytest-asyncio

---

## Background — What Exists Today

| File | Problem |
|------|---------|
| `generators/npc.py` | No logging, no docstrings, duplicates LLM-call boilerplate |
| `generators/monster.py` | Same |
| `generators/encounter.py` | Same |
| `generators/chapter.py` | Same, plus inconsistent `cast()` instead of type annotation |
| `generators/location.py` | Same |
| `generators/base.py` | Only `resolve_title_and_slug()` — shared LLM logic missing |
| `generators/dispatch.py` | Requires two edits (tuple + match) to register a new kind |
| All generators | Zero unit tests |

`chat_service.py` is the gold standard to follow: structlog, docstrings, Settings-per-call comment, clean error handling.

---

## Task 1: Extract shared `run_generation()` helper into `base.py`

Every generator duplicates this exact pattern — Settings instantiation, provider resolution, `build_agent()`, `agent.run()` with usage limits, and `UsageLimitExceeded` handling. This task moves it into one place.

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/base.py`
- Test: `services/llm_api/tests/test_generators_base.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run to confirm tests pass (they already should)**

```bash
cd services/llm_api && pytest tests/test_generators_base.py -v
```
Expected: all PASS (these test existing behavior — guard rail before refactoring).

**Step 3: Add `run_generation()` to `base.py`**

Replace the entire contents of `services/llm_api/src/llm_api/generators/base.py`:

```python
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

    log.debug("generation.llm_done", output_type=output_type.__name__)
    return result.output  # type: ignore[return-value]
```

**Step 4: Add `run_generation` test**

Add to `services/llm_api/tests/test_generators_base.py`:

```python
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
```

**Step 5: Run all base tests**

```bash
cd services/llm_api && pytest tests/test_generators_base.py -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/base.py \
        services/llm_api/tests/test_generators_base.py
git commit -m "refactor(generators): extract run_generation helper into base.py"
```

---

## Task 2: Refactor `npc.py` — use `run_generation`, add logging and docstrings

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/npc.py`
- Test: `services/llm_api/tests/test_generator_npc.py`

**Step 1: Write the failing test first**

```python
# services/llm_api/tests/test_generator_npc.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_generate_npc_mock_returns_draft():
    from llm_api.generators.npc import generate_npc
    from llm_api.models.generated import GeneratedDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A wise old wizard", title="Aldric the Grey")
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, GeneratedDraft)
    assert draft.title == "Aldric the Grey"
    assert draft.slug == "aldric-the-grey"


@pytest.mark.asyncio
async def test_generate_npc_mock_fallback_title():
    from llm_api.generators.npc import generate_npc
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A sneaky rogue", title="")
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert draft.title == "New NPC"
    assert draft.slug == "new-npc"


@pytest.mark.asyncio
async def test_generate_npc_mock_frontmatter_has_required_keys():
    from llm_api.generators.npc import generate_npc
    from llm_api.models.requests import GenerateRequest
    import uuid

    req = GenerateRequest(prompt="A blacksmith", title="Tom")
    draft = await generate_npc(request=req, campaign="test-campaign")
    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test-campaign")

    for key in draft.required_yaml_keys():
        assert key in fm, f"Missing frontmatter key: {key}"


def test_generate_npc_mock_provider_override():
    """Provider override of 'mock' should resolve immediately without LLM call."""
    import asyncio
    from llm_api.generators.npc import generate_npc
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A merchant", title="Bob")
    draft = asyncio.get_event_loop().run_until_complete(
        generate_npc(request=req, campaign="test-campaign", provider_override="mock")
    )
    assert draft.slug == "bob"
```

**Step 2: Run to confirm tests pass with existing code**

```bash
cd services/llm_api && pytest tests/test_generator_npc.py -v
```
Expected: all PASS (tests verify existing behavior before refactoring).

**Step 3: Rewrite `npc.py` using `run_generation` and add logging/docstrings**

```python
"""NPC generator — produces a D&D NPC draft for a Jekyll campaign site.

The public entry point is :func:`generate_npc`.  In ``mock`` mode it
short-circuits immediately with placeholder content so tests and local
development work without an LLM API key.
"""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field
from pydantic_ai import UsageLimits

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D NPC draft content for a Jekyll campaign site. "
    "Return concise, usable text. Do NOT include YAML frontmatter."
)


class NpcOutput(BaseModel):
    """Structured LLM output for an NPC generation request."""

    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list)


class NpcDraft(GeneratedDraft):
    """Jekyll-ready NPC draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, name: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._name = name
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the NPC layout."""
        return [
            "layout", "title", "name", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this NPC draft.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name (used for campaign-specific paths).

        Returns:
            A dict whose keys match the NPC Jekyll layout requirements.
        """
        return {
            "layout": "npc",
            "title": self.title,
            "name": self._name,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/npcs/:slug",
            "category": "npc",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/npc-thumb.png",
            "portrait": "/assets/images/placeholders/npc-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


async def generate_npc(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D NPC draft and return it as an :class:`NpcDraft`.

    In ``mock`` mode (``LLM_PROVIDER=mock`` or ``provider_override="mock"``)
    the function returns immediately with placeholder content — no API call is
    made.

    Args:
        request: The validated generation request containing the user prompt,
                 optional title, and optional slug.
        campaign: Name of the active campaign (injected into the LLM prompt
                  for context).
        provider_override: Optional provider name from the request header.
                           Falls back to the ``LLM_PROVIDER`` env var.

    Returns:
        An :class:`NpcDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if the LLM exceeds configured
                  request or token limits.
    """
    # Settings are instantiated fresh per call so env-var changes in tests
    # are picked up without restarting the server.
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New NPC")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("npc.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("npc.generate.mock")
        return NpcDraft(title=title, slug=slug, name=title, summary="TBD", tags=[])

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: name (full), summary (markdown), tags (list)."
    )
    out: NpcOutput = await run_generation(
        output_type=NpcOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("npc.generate.done", title=title, slug=slug)
    return NpcDraft(title=title, slug=slug, name=out.name, summary=out.summary, tags=out.tags)
```

**Step 4: Run tests to confirm refactored code still passes**

```bash
cd services/llm_api && pytest tests/test_generator_npc.py -v
```
Expected: all PASS.

**Step 5: Run full test suite to check for regressions**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/npc.py \
        services/llm_api/tests/test_generator_npc.py
git commit -m "refactor(generators): use run_generation, add logging and docstrings to npc"
```

---

## Task 3: Refactor `monster.py` — use `run_generation`, add logging and docstrings

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/monster.py`
- Test: `services/llm_api/tests/test_generator_monster.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_generator_monster.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_generate_monster_mock_returns_draft():
    from llm_api.generators.monster import generate_monster
    from llm_api.models.generated import GeneratedDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A fire-breathing dragon", title="Pyrothorn")
    draft = await generate_monster(request=req, campaign="test-campaign")
    assert isinstance(draft, GeneratedDraft)
    assert draft.title == "Pyrothorn"
    assert draft.slug == "pyrothorn"


@pytest.mark.asyncio
async def test_generate_monster_mock_fallback_title():
    from llm_api.generators.monster import generate_monster
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="An undead warrior", title="")
    draft = await generate_monster(request=req, campaign="test-campaign")
    assert draft.title == "New Monster"


@pytest.mark.asyncio
async def test_generate_monster_mock_frontmatter_has_required_keys():
    from llm_api.generators.monster import generate_monster
    from llm_api.models.requests import GenerateRequest
    import uuid

    req = GenerateRequest(prompt="A troll", title="Bridge Troll")
    draft = await generate_monster(request=req, campaign="test-campaign")
    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test-campaign")

    for key in draft.required_yaml_keys():
        assert key in fm, f"Missing frontmatter key: {key}"
```

**Step 2: Run to confirm tests pass with existing code**

```bash
cd services/llm_api && pytest tests/test_generator_monster.py -v
```
Expected: all PASS.

**Step 3: Rewrite `monster.py`**

Follow the exact same pattern as the refactored `npc.py`:
- Add module docstring
- Import `run_generation` from `base` instead of `build_agent` / `UsageLimitExceeded` / `UsageLimits`
- Remove `from llm_api.providers.factory import build_agent`
- Remove `from pydantic_ai import UsageLimitExceeded, UsageLimits`
- Add `log = structlog.get_logger(__name__)`
- Rename `SYSTEM_PROMPT` → `_SYSTEM_PROMPT` (private convention)
- Add docstrings to `MonsterOutput`, `MonsterDraft`, `required_yaml_keys`, `frontmatter_yaml`, `generate_monster`
- In `generate_monster`: add `log.info("monster.generate.start", ...)`, `log.debug("monster.generate.mock")`, `log.info("monster.generate.done", ...)`
- Replace the `build_agent` / `agent.run` / `except UsageLimitExceeded` block with a single `await run_generation(...)` call

```python
"""Monster generator — produces a D&D monster draft for a Jekyll campaign site."""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D monster draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


class MonsterOutput(BaseModel):
    """Structured LLM output for a monster generation request."""

    summary: str = Field(min_length=1, max_length=6000)
    tags: list[str] = Field(default_factory=list)


class MonsterDraft(GeneratedDraft):
    """Jekyll-ready monster draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the monster layout."""
        return [
            "layout", "title", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this monster draft.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name.

        Returns:
            A dict whose keys match the monster Jekyll layout requirements.
        """
        return {
            "layout": "monster",
            "title": self.title,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/monsters/:slug",
            "category": "monster",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/monster-thumb.png",
            "portrait": "/assets/images/placeholders/monster-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


async def generate_monster(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D monster draft and return it as a :class:`MonsterDraft`.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        A :class:`MonsterDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if LLM exceeds usage limits.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Monster")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("monster.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("monster.generate.mock")
        return MonsterDraft(title=title, slug=slug, summary="TBD", tags=[])

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: summary (markdown), tags (list)."
    )
    out: MonsterOutput = await run_generation(
        output_type=MonsterOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("monster.generate.done", title=title, slug=slug)
    return MonsterDraft(title=title, slug=slug, summary=out.summary, tags=out.tags)
```

**Step 4: Run tests**

```bash
cd services/llm_api && pytest tests/test_generator_monster.py -v
```
Expected: all PASS.

**Step 5: Full suite check**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/monster.py \
        services/llm_api/tests/test_generator_monster.py
git commit -m "refactor(generators): use run_generation, add logging and docstrings to monster"
```

---

## Task 4: Refactor `encounter.py` — use `run_generation`, add logging and docstrings

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/encounter.py`
- Test: `services/llm_api/tests/test_generator_encounter.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_generator_encounter.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_generate_encounter_mock_returns_draft():
    from llm_api.generators.encounter import generate_encounter
    from llm_api.models.generated import GeneratedDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="Ambush at the bridge", title="Bridge Ambush")
    draft = await generate_encounter(request=req, campaign="test-campaign")
    assert isinstance(draft, GeneratedDraft)
    assert draft.title == "Bridge Ambush"
    assert draft.slug == "bridge-ambush"


@pytest.mark.asyncio
async def test_generate_encounter_mock_fallback_title():
    from llm_api.generators.encounter import generate_encounter
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A tavern brawl", title="")
    draft = await generate_encounter(request=req, campaign="test-campaign")
    assert draft.title == "New Encounter"


@pytest.mark.asyncio
async def test_generate_encounter_mock_frontmatter_has_required_keys():
    from llm_api.generators.encounter import generate_encounter
    from llm_api.models.requests import GenerateRequest
    import uuid

    req = GenerateRequest(prompt="Wolves in the forest", title="Wolf Pack")
    draft = await generate_encounter(request=req, campaign="test-campaign")
    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test-campaign")

    for key in draft.required_yaml_keys():
        assert key in fm, f"Missing frontmatter key: {key}"
```

**Step 2: Run to confirm pass with existing code**

```bash
cd services/llm_api && pytest tests/test_generator_encounter.py -v
```
Expected: all PASS.

**Step 3: Rewrite `encounter.py`** — apply the same refactoring pattern as monster/npc above:

- Module docstring
- `import structlog`, `log = structlog.get_logger(__name__)`
- Import `run_generation` from base; remove direct `build_agent`, `UsageLimitExceeded`, `UsageLimits` imports
- Rename `SYSTEM_PROMPT` → `_SYSTEM_PROMPT`
- Docstrings on `EncounterOutput`, `EncounterDraft`, `required_yaml_keys`, `frontmatter_yaml`, `generate_encounter`
- Log calls: `encounter.generate.start`, `encounter.generate.mock`, `encounter.generate.done`
- Replace boilerplate try/except block with `await run_generation(...)`

**Step 4: Run tests**

```bash
cd services/llm_api && pytest tests/test_generator_encounter.py -v
```
Expected: all PASS.

**Step 5: Full suite check**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/encounter.py \
        services/llm_api/tests/test_generator_encounter.py
git commit -m "refactor(generators): use run_generation, add logging and docstrings to encounter"
```

---

## Task 5: Refactor `chapter.py` — use `run_generation`, fix `cast()`, add logging and docstrings

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/chapter.py`
- Test: `services/llm_api/tests/test_generator_chapter.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_generator_chapter.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_generate_chapter_mock_returns_draft():
    from llm_api.generators.chapter import generate_chapter
    from llm_api.models.generated import GeneratedDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="The heroes begin their journey", title="Into the Dark")
    draft = await generate_chapter(request=req, campaign="test-campaign")
    assert isinstance(draft, GeneratedDraft)
    assert draft.title == "Into the Dark"
    assert draft.slug == "into-the-dark"


@pytest.mark.asyncio
async def test_generate_chapter_mock_fallback_title():
    from llm_api.generators.chapter import generate_chapter
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A grand opening", title="")
    draft = await generate_chapter(request=req, campaign="test-campaign")
    assert draft.title == "New Chapter"


@pytest.mark.asyncio
async def test_generate_chapter_mock_frontmatter_has_required_keys():
    from llm_api.generators.chapter import generate_chapter
    from llm_api.models.requests import GenerateRequest
    import uuid

    req = GenerateRequest(prompt="Journey begins", title="Chapter One")
    draft = await generate_chapter(request=req, campaign="test-campaign")
    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test-campaign")

    for key in draft.required_yaml_keys():
        assert key in fm, f"Missing frontmatter key: {key}"
```

**Step 2: Run to confirm pass with existing code**

```bash
cd services/llm_api && pytest tests/test_generator_chapter.py -v
```
Expected: all PASS.

**Step 3: Rewrite `chapter.py`** — same refactoring pattern, plus:

- Remove `from typing import cast` (no longer needed — use type annotation instead)
- Replace `out = cast(ChapterOutput, result.output)` with `out: ChapterOutput = await run_generation(...)`

```python
"""Chapter generator — produces a D&D chapter draft for a Jekyll campaign site."""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D chapter draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


class ChapterOutput(BaseModel):
    """Structured LLM output for a chapter generation request."""

    overview: str = Field(min_length=1, max_length=12000)


class ChapterDraft(GeneratedDraft):
    """Jekyll-ready chapter draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, overview: str):
        self.title = title
        self.slug = slug
        self.markdown_body = overview

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the chapter layout."""
        return [
            "layout", "title", "category", "chapter", "episode", "scene",
            "jumbo", "thumb", "portrait", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this chapter draft.

        Chapter drafts are not automatically published; the promotion script
        will place them under ``_pages/chapters``.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name.

        Returns:
            A dict whose keys match the chapter Jekyll layout requirements.
        """
        return {
            "layout": "chapter",
            "title": self.title,
            "slug": self.slug,
            "id": str(draft_id),
            "category": "chapter",
            "chapter": 1,
            "episode": "",
            "scene": "",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/chapter-thumb.png",
            "portrait": "/assets/images/placeholders/chapter-portrait.png",
            "search": True,
            "excerpt_separator": "",
        }


async def generate_chapter(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D chapter draft and return it as a :class:`ChapterDraft`.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        A :class:`ChapterDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if LLM exceeds usage limits.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Chapter")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("chapter.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("chapter.generate.mock")
        return ChapterDraft(title=title, slug=slug, overview="TBD")

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: overview (markdown)."
    )
    out: ChapterOutput = await run_generation(
        output_type=ChapterOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("chapter.generate.done", title=title, slug=slug)
    return ChapterDraft(title=title, slug=slug, overview=out.overview)
```

**Step 4: Run tests**

```bash
cd services/llm_api && pytest tests/test_generator_chapter.py -v
```
Expected: all PASS.

**Step 5: Full suite check**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/chapter.py \
        services/llm_api/tests/test_generator_chapter.py
git commit -m "refactor(generators): use run_generation, fix cast(), add logging and docstrings to chapter"
```

---

## Task 6: Refactor `location.py` — use `run_generation`, add logging and docstrings

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/location.py`
- Test: `services/llm_api/tests/test_generator_location.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_generator_location.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.mark.asyncio
async def test_generate_location_mock_returns_draft():
    from llm_api.generators.location import generate_location
    from llm_api.models.generated import GeneratedDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A haunted forest", title="Darkwood")
    draft = await generate_location(request=req, campaign="test-campaign")
    assert isinstance(draft, GeneratedDraft)
    assert draft.title == "Darkwood"
    assert draft.slug == "darkwood"


@pytest.mark.asyncio
async def test_generate_location_mock_fallback_title():
    from llm_api.generators.location import generate_location
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A mountain pass", title="")
    draft = await generate_location(request=req, campaign="test-campaign")
    assert draft.title == "New Location"


@pytest.mark.asyncio
async def test_generate_location_mock_frontmatter_has_required_keys():
    from llm_api.generators.location import generate_location
    from llm_api.models.requests import GenerateRequest
    import uuid

    req = GenerateRequest(prompt="A coastal village", title="Port Seaward")
    draft = await generate_location(request=req, campaign="test-campaign")
    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test-campaign")

    for key in draft.required_yaml_keys():
        assert key in fm, f"Missing frontmatter key: {key}"
```

**Step 2: Run to confirm pass with existing code**

```bash
cd services/llm_api && pytest tests/test_generator_location.py -v
```
Expected: all PASS.

**Step 3: Rewrite `location.py`** — same pattern as encounter/monster.

**Step 4: Run tests**

```bash
cd services/llm_api && pytest tests/test_generator_location.py -v
```
Expected: all PASS.

**Step 5: Full suite check**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/location.py \
        services/llm_api/tests/test_generator_location.py
git commit -m "refactor(generators): use run_generation, add logging and docstrings to location"
```

---

## Task 7: Convert `dispatch.py` to a data-driven registry

Currently, adding a new kind requires editing two places: `SUPPORTED_KINDS` and the `match` block. A registry dict eliminates the double-update.

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/dispatch.py`
- Test: `services/llm_api/tests/test_generator_dispatch.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_generator_dispatch.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


def test_supported_kinds_contains_all_expected():
    from llm_api.generators.dispatch import SUPPORTED_KINDS
    assert set(SUPPORTED_KINDS) == {"npc", "monster", "encounter", "chapter", "location"}


@pytest.mark.asyncio
async def test_generate_for_kind_npc():
    from llm_api.generators.dispatch import generate_for_kind
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A spy", title="Shadow")
    draft = await generate_for_kind(kind="npc", request=req, campaign="test-campaign")
    assert draft.title == "Shadow"


@pytest.mark.asyncio
async def test_generate_for_kind_monster():
    from llm_api.generators.dispatch import generate_for_kind
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A giant spider", title="Spider Queen")
    draft = await generate_for_kind(kind="monster", request=req, campaign="test-campaign")
    assert draft.title == "Spider Queen"


@pytest.mark.asyncio
async def test_generate_for_kind_unknown_raises_api_error():
    from llm_api.generators.dispatch import generate_for_kind
    from llm_api.models.requests import GenerateRequest
    from llm_api.services.errors import ApiError

    req = GenerateRequest(prompt="test")
    with pytest.raises(ApiError) as exc_info:
        await generate_for_kind(kind="unknown_kind", request=req, campaign="test-campaign")
    assert exc_info.value.code == "unsupported_kind"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_for_kind_all_supported_kinds():
    """Smoke test: every kind in SUPPORTED_KINDS must resolve without error."""
    from llm_api.generators.dispatch import generate_for_kind, SUPPORTED_KINDS
    from llm_api.models.requests import GenerateRequest

    for kind in SUPPORTED_KINDS:
        req = GenerateRequest(prompt=f"Test {kind}", title=f"Test {kind.title()}")
        draft = await generate_for_kind(kind=kind, request=req, campaign="test-campaign")
        assert draft is not None
```

**Step 2: Run tests against existing code**

```bash
cd services/llm_api && pytest tests/test_generator_dispatch.py -v
```
Expected: all PASS (guard rail before refactoring).

**Step 3: Rewrite `dispatch.py` with registry**

```python
"""Generator dispatch — routes a kind string to the correct generator function.

Adding a new generator requires only one change: add an entry to ``_REGISTRY``.
``SUPPORTED_KINDS`` is derived automatically from the registry keys.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.errors import ApiError

from llm_api.generators.npc import generate_npc
from llm_api.generators.monster import generate_monster
from llm_api.generators.encounter import generate_encounter
from llm_api.generators.chapter import generate_chapter
from llm_api.generators.location import generate_location

# Type alias for any generator function.
_GeneratorFn = Callable[..., Awaitable[GeneratedDraft]]

_REGISTRY: dict[str, _GeneratorFn] = {
    "npc": generate_npc,
    "monster": generate_monster,
    "encounter": generate_encounter,
    "chapter": generate_chapter,
    "location": generate_location,
}

# Derived from registry — no manual sync required.
SUPPORTED_KINDS: tuple[str, ...] = tuple(_REGISTRY.keys())


async def generate_for_kind(
    *, kind: str, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Dispatch a generation request to the appropriate generator.

    Args:
        kind: Resource kind string (e.g. ``"npc"``, ``"monster"``).
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        A :class:`GeneratedDraft` produced by the matched generator.

    Raises:
        ApiError: ``unsupported_kind`` (400) if ``kind`` is not in the registry.
    """
    generator = _REGISTRY.get(kind)
    if generator is None:
        raise ApiError(
            code="unsupported_kind",
            message=f"Unsupported kind: {kind}",
            status_code=400,
        )
    return await generator(request=request, campaign=campaign, provider_override=provider_override)
```

**Step 4: Run dispatch tests**

```bash
cd services/llm_api && pytest tests/test_generator_dispatch.py -v
```
Expected: all PASS.

**Step 5: Full suite check**

```bash
cd services/llm_api && pytest -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/generators/dispatch.py \
        services/llm_api/tests/test_generator_dispatch.py
git commit -m "refactor(generators): replace match block with data-driven registry in dispatch"
```

---

## Task 8: Update README documentation

**Files:**
- Modify: `services/llm_api/README.md` (or create if absent)

**Step 1: Locate existing README**

```bash
ls services/llm_api/README.md
```

**Step 2: Add / update the Generators section**

Add the following section to the README under a `## Generators` heading:

```markdown
## Generators

**Overview**

Each generator in `src/llm_api/generators/` produces a Jekyll-ready draft for
one D&D resource kind (NPC, monster, encounter, chapter, location). Generators
are self-contained modules that can be imported and tested independently.

**TL;DR**

| Kind | Generator | Draft class |
|------|-----------|-------------|
| `npc` | `generators/npc.py` | `NpcDraft` |
| `monster` | `generators/monster.py` | `MonsterDraft` |
| `encounter` | `generators/encounter.py` | `EncounterDraft` |
| `chapter` | `generators/chapter.py` | `ChapterDraft` |
| `location` | `generators/location.py` | `LocationDraft` |

**Developer View**

- All generators call `run_generation()` from `generators/base.py` — never
  import `pydantic_ai` internals directly.
- Structured logging via `structlog` follows `{kind}.generate.{start|mock|done}`
  event naming.
- Mock mode (`LLM_PROVIDER=mock` or `provider_override="mock"`) short-circuits
  before any LLM call. All unit tests use mock mode.
- To add a new generator: create `generators/{kind}.py`, add it to `_REGISTRY`
  in `generators/dispatch.py`. No other file needs changing.

**Running Tests**

```bash
cd services/llm_api
pip install -e ".[dev]"
pytest -v
```
```

**Step 3: Commit**

```bash
git add services/llm_api/README.md
git commit -m "docs(generators): document generator architecture and developer guide"
```

---

## Verification

After all tasks are complete, run the full test suite one final time:

```bash
cd services/llm_api && pytest -v --tb=short
```

All tests must PASS. No new warnings should be introduced. Line count per generator file should be *less* than before (duplication removed).
