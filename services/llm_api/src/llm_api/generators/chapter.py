from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import UsageLimitExceeded, UsageLimits

from llm_api.generators.base import resolve_title_and_slug
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.providers.factory import build_agent
from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


class ChapterOutput(BaseModel):
    overview: str = Field(min_length=1, max_length=12000)


class ChapterDraft(GeneratedDraft):
    def __init__(self, *, title: str, slug: str, overview: str):
        self.title = title
        self.slug = slug
        self.markdown_body = overview

    def required_yaml_keys(self) -> list[str]:
        return [
            "layout",
            "title",
            "category",
            "chapter",
            "episode",
            "scene",
            "jumbo",
            "thumb",
            "portrait",
            "search",
            "excerpt_separator",
            "id",
            "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str):
        # Chapter drafts are not automatically published; promotion script will place them under _pages/chapters.
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


SYSTEM_PROMPT = (
    "You generate D&D chapter draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


async def generate_chapter(*, request: GenerateRequest, campaign: str) -> GeneratedDraft:
    settings = Settings()
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Chapter")

    if settings.llm_provider == "mock":
        return ChapterDraft(title=title, slug=slug, overview="TBD")

    agent = build_agent(output_type=ChapterOutput, system_prompt=SYSTEM_PROMPT)
    try:
        result = await agent.run(
            f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n" "Return: overview (markdown).",
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

    out: ChapterOutput = result.output
    return ChapterDraft(title=title, slug=slug, overview=out.overview)
