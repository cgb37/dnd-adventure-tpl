"""Monster generator — produces a D&D monster draft for a Jekyll campaign site."""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D monster draft content for a Jekyll campaign site. "
    "Return markdown body only; do not include YAML."
)


class MonsterOutput(BaseModel):
    """Structured LLM output for a monster generation request."""

    summary: str = Field(min_length=1, max_length=6000)
    tags: list[str] = Field(default_factory=list)


class MonsterDraft(GeneratedDraft):
    """Jekyll-ready monster draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the monster layout."""
        return [
            "layout", "title", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this monster draft.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name.

        Returns:
            A dict whose keys match the monster Jekyll layout requirements.
        """
        return {
            "layout": "monster",
            "title": self.title,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/monsters/:slug",
            "category": "monster",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/monster-thumb.png",
            "portrait": "/assets/images/placeholders/monster-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


async def generate_monster(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D monster draft and return it as a :class:`MonsterDraft`.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name from the request header.

    Returns:
        A :class:`MonsterDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if LLM exceeds usage limits.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New Monster")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("monster.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("monster.generate.mock")
        return MonsterDraft(title=title, slug=slug, summary="TBD", tags=[])

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: summary (markdown), tags (list)."
    )
    out: MonsterOutput = await run_generation(
        output_type=MonsterOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("monster.generate.done", title=title, slug=slug)
    return MonsterDraft(title=title, slug=slug, summary=out.summary, tags=out.tags)
