from __future__ import annotations

import os

import pytest

from llm_api.models.requests import GenerateRequest
from llm_api.services.ids import content_id


@pytest.mark.asyncio
async def test_generated_npc_includes_required_yaml_keys(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_API_KEY", "dev-key")

    from llm_api.generators.npc import generate_npc

    gen = await generate_npc(request=GenerateRequest(prompt="make an npc"), campaign="test-campaign")
    draft_id = content_id(kind="npc", campaign="test-campaign", slug=gen.slug)
    fm = gen.frontmatter_yaml(draft_id=draft_id, campaign="test-campaign")

    for k in gen.required_yaml_keys():
        assert k in fm


@pytest.mark.asyncio
async def test_generated_monster_includes_required_yaml_keys(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_API_KEY", "dev-key")

    from llm_api.generators.monster import generate_monster

    gen = await generate_monster(request=GenerateRequest(prompt="make a monster"), campaign="test-campaign")
    draft_id = content_id(kind="monster", campaign="test-campaign", slug=gen.slug)
    fm = gen.frontmatter_yaml(draft_id=draft_id, campaign="test-campaign")

    for k in gen.required_yaml_keys():
        assert k in fm
