"""NPC generator — produces a D&D NPC draft for a Jekyll campaign site.

The public entry point is :func:`generate_npc`.  In ``mock`` mode it
short-circuits immediately with placeholder content so tests and local
development work without an LLM API key.
"""
from __future__ import annotations

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.models.generated import GeneratedDraft
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = (
    "You generate D&D NPC draft content for a Jekyll campaign site. "
    "Return concise, usable text. Do NOT include YAML frontmatter."
)


class NpcOutput(BaseModel):
    """Structured LLM output for an NPC generation request."""

    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list)


class NpcDraft(GeneratedDraft):
    """Jekyll-ready NPC draft with YAML front-matter and Markdown body."""

    def __init__(self, *, title: str, slug: str, name: str, summary: str, tags: list[str]):
        self.title = title
        self.slug = slug
        self.markdown_body = summary
        self._name = name
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        """Return the list of YAML front-matter keys expected by the NPC layout."""
        return [
            "layout", "title", "name", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        """Build the YAML front-matter dict for this NPC draft.

        Args:
            draft_id: UUID assigned by the drafts service.
            campaign: Active campaign name (used for campaign-specific paths).

        Returns:
            A dict whose keys match the NPC Jekyll layout requirements.
        """
        return {
            "layout": "npc",
            "title": self.title,
            "name": self._name,
            "slug": self.slug,
            "id": str(draft_id),
            "permalink": "/npcs/:slug",
            "category": "npc",
            "chapter": "01",
            "episode": "01",
            "scene": "01",
            "jumbo": "",
            "thumb": "/assets/images/placeholders/npc-thumb.png",
            "portrait": "/assets/images/placeholders/npc-portrait.png",
            "tags": self._tags,
            "search": True,
            "excerpt_separator": "",
        }


async def generate_npc(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D NPC draft and return it as an :class:`NpcDraft`.

    In ``mock`` mode (``LLM_PROVIDER=mock`` or ``provider_override="mock"``)
    the function returns immediately with placeholder content — no API call is
    made.

    Args:
        request: The validated generation request containing the user prompt,
                 optional title, and optional slug.
        campaign: Name of the active campaign (injected into the LLM prompt
                  for context).
        provider_override: Optional provider name from the request header.
                           Falls back to the ``LLM_PROVIDER`` env var.

    Returns:
        An :class:`NpcDraft` ready to be serialised and written to disk.

    Raises:
        ApiError: ``usage_limit_exceeded`` (507) if the LLM exceeds configured
                  request or token limits.
    """
    # Settings are instantiated fresh per call so env-var changes in tests
    # are picked up without restarting the server.
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New NPC")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    log.info("npc.generate.start", title=title, provider=provider)

    if provider == "mock":
        log.debug("npc.generate.mock")
        return NpcDraft(title=title, slug=slug, name=title, summary="TBD", tags=[])

    user_prompt = (
        f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
        "Return: name (full), summary (markdown), tags (list)."
    )
    out: NpcOutput = await run_generation(
        output_type=NpcOutput,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        provider=provider,
        settings=settings,
    )

    log.info("npc.generate.done", title=title, slug=slug)
    return NpcDraft(title=title, slug=slug, name=out.name, summary=out.summary, tags=out.tags)
