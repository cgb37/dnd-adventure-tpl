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
