from __future__ import annotations

from slugify import slugify

from llm_api.models.requests import GenerateRequest


def resolve_title_and_slug(*, request: GenerateRequest, fallback_title: str) -> tuple[str, str]:
    title = (request.title or "").strip() or fallback_title
    slug = (request.slug or "").strip()
    if not slug:
        slug = slugify(title)
    return title, slug
