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
