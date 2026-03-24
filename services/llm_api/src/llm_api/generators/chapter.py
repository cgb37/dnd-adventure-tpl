"""Chapter generator — produces a D&D chapter draft for a Jekyll campaign site."""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D chapter draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


class ChapterOutput(BaseModel):
    """Structured LLM output for a chapter generation request."""

    overview: str = Field(min_length=1, max_length=12000)


class ChapterDraft(GeneratedDraft):
    """Jekyll-ready chapter draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, overview: str):
        self.title = title
        self.slug = slug
        self.markdown_body = overview

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the chapter layout."""
        return [
            "layout", "title", "category", "chapter", "episode", "scene",
            "jumbo", "thumb", "portrait", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this chapter draft.

        Chapter drafts are not automatically published; the promotion script
        will place them under ``_pages/chapters``.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name.

        Returns:
            A dict whose keys match the chapter Jekyll layout requirements.
        """
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


async def generate_chapter(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D chapter draft and return it as a :class:`ChapterDraft`.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        A :class:`ChapterDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if LLM exceeds usage limits.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Chapter")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("chapter.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("chapter.generate.mock")
        return ChapterDraft(title=title, slug=slug, overview="TBD")

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: overview (markdown)."
    )
    out: ChapterOutput = await run_generation(
        output_type=ChapterOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("chapter.generate.done", title=title, slug=slug)
    return ChapterDraft(title=title, slug=slug, overview=out.overview)
