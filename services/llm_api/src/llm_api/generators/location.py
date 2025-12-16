from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import UsageLimitExceeded, UsageLimits

from llm_api.generators.base import resolve_title_and_slug
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.providers.factory import build_agent
from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


class LocationOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=12000)
    tags: list[str] = Field(default_factory=list)


class LocationDraft(GeneratedDraft):
    def __init__(self, *, title: str, slug: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        return [
            "layout",
            "title",
            "permalink",
            "category",
            "chapter",
            "episode",
            "scene",
            "jumbo",
            "thumb",
            "portrait",
            "tags",
            "search",
            "excerpt_separator",
            "id",
            "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str):
        return {
            "layout": "location",
            "title": self.title,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/locations/:slug",
            "category": "location",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/location-thumb.png",
            "portrait": "/assets/images/placeholders/location-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


SYSTEM_PROMPT = (
    "You generate D&D location draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


async def generate_location(*, request: GenerateRequest, campaign: str) -> GeneratedDraft:
    settings = Settings()
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Location")

    if settings.llm_provider == "mock":
        return LocationDraft(title=title, slug=slug, summary="TBD", tags=[])

    agent = build_agent(output_type=LocationOutput, system_prompt=SYSTEM_PROMPT)
    try:
        result = await agent.run(
            f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
            "Return: summary (markdown), tags (list).",
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

    out: LocationOutput = result.output
    return LocationDraft(title=title, slug=slug, summary=out.summary, tags=out.tags)
