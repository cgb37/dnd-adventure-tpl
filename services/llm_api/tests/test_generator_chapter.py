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
