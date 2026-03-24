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
