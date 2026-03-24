"""Encounter generator — produces a D&D encounter draft for a Jekyll campaign site."""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D encounter draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


class EncounterOutput(BaseModel):
    """Structured LLM output for an encounter generation request."""

    summary: str = Field(min_length=1, max_length=8000)
    tags: list[str] = Field(default_factory=list)


class EncounterDraft(GeneratedDraft):
    """Jekyll-ready encounter draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the encounter layout."""
        return [
            "layout", "title", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this encounter draft.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name.

        Returns:
            A dict whose keys match the encounter Jekyll layout requirements.
        """
        return {
            "layout": "encounter",
            "title": self.title,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/encounters/:slug",
            "category": "encounter",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/encounter-thumb.png",
            "portrait": "/assets/images/placeholders/encounter-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


async def generate_encounter(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D encounter draft and return it as an :class:`EncounterDraft`.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        An :class:`EncounterDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if LLM exceeds usage limits.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Encounter")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("encounter.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("encounter.generate.mock")
        return EncounterDraft(title=title, slug=slug, summary="TBD", tags=[])

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: summary (markdown), tags (list)."
    )
    out: EncounterOutput = await run_generation(
        output_type=EncounterOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("encounter.generate.done", title=title, slug=slug)
    return EncounterDraft(title=title, slug=slug, summary=out.summary, tags=out.tags)
