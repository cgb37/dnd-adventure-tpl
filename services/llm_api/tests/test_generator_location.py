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
