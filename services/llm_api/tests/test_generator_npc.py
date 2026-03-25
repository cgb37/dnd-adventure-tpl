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


@pytest.mark.asyncio
async def test_generate_npc_mock_provider_override():
    """Provider override of 'mock' should resolve immediately without LLM call."""
    from llm_api.generators.npc import generate_npc
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A merchant", title="Bob")
    draft = await generate_npc(request=req, campaign="test-campaign", provider_override="mock")
    assert draft.slug == "bob"


@pytest.mark.asyncio
async def test_generate_npc_with_combat_type_mock(monkeypatch, tmp_path):
    """Mock mode with npc_type=combat_npc returns StructuredNpcDraft."""
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))

    from llm_api.services.vector_store import reset_client
    reset_client()

    from llm_api.generators.npc import generate_npc
    from llm_api.generators.npc_renderer import StructuredNpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(
        prompt="A goblin ambush leader",
        title="Snarg",
        constraints={"npc_type": "combat_npc"},
    )
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, StructuredNpcDraft)
    assert draft._npc_type == "combat_npc"


@pytest.mark.asyncio
async def test_generate_npc_with_roleplay_type_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))

    from llm_api.services.vector_store import reset_client
    reset_client()

    from llm_api.generators.npc import generate_npc
    from llm_api.generators.npc_renderer import StructuredNpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(
        prompt="A mysterious herbalist",
        title="Old Meg",
        constraints={"npc_type": "roleplay_npc"},
    )
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, StructuredNpcDraft)
    assert draft._npc_type == "roleplay_npc"


@pytest.mark.asyncio
async def test_generate_npc_without_type_falls_back_to_legacy():
    """No npc_type constraint → existing flat NPC behavior (backward compat)."""
    from llm_api.generators.npc import generate_npc, NpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A blacksmith", title="Tom")
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, NpcDraft)


@pytest.mark.asyncio
async def test_legacy_user_prompt_includes_json_example_and_field_names():
    """The legacy user_prompt must contain the expected output field names and a
    concrete JSON example so small models do not return function-call shapes."""
    from unittest.mock import patch

    from llm_api.generators.npc import NpcOutput, generate_npc
    from llm_api.models.requests import GenerateRequest

    captured: dict = {}

    async def _fake_run_generation(**kwargs):
        captured["user_prompt"] = kwargs["user_prompt"]
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
