"""NPC generator — produces D&D NPC drafts for a Jekyll campaign site.

Supports two modes:
- **Legacy** (no npc_type constraint): flat name/summary/tags output.
- **Structured** (npc_type in constraints): rich JSON matching the
  player_character, combat_npc, or roleplay_npc schemas, stored in ChromaDB.

The public entry point is :func:`generate_npc`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.generators.npc_renderer import render_npc_draft, StructuredNpcDraft  # noqa: F401
from llm_api.models.generated import GeneratedDraft
from llm_api.models.npc_types import (
    CombatNpc,
    NPC_TYPE_NAMES,
    PlayerCharacter,
    RoleplayNpc,
)
from llm_api.models.requests import GenerateRequest
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_REFERENCES_DIR = Path(__file__).parent / "references"

_SYSTEM_PROMPT = (
    "You generate D&D NPC draft content for a Jekyll campaign site. "
    "Return concise, usable text. Do NOT include YAML frontmatter."
)

# Maps npc_type → (output Pydantic model, reference files, system prompt suffix)
_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "player_character": {
        "model": PlayerCharacter,
        "references": ["races_brief.md", "classes_brief.md"],
        "system_suffix": "Generate a complete D&D 5e player character as structured JSON.",
    },
    "combat_npc": {
        "model": CombatNpc,
        "references": ["npc_combat_brief.md"],
        "system_suffix": "Generate a D&D 5e combat NPC stat block as structured JSON.",
    },
    "roleplay_npc": {
        "model": RoleplayNpc,
        "references": ["npc_roleplay_brief.md"],
        "system_suffix": (
            "Generate a D&D 5e roleplay NPC with personality, secrets, "
            "and plot hooks as structured JSON."
        ),
    },
}


def _load_references(filenames: list[str]) -> str:
    """Load and concatenate reference files for prompt embedding."""
    parts: list[str] = []
    for fname in filenames:
        path = _REFERENCES_DIR / fname
        if path.exists():
            parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


# ── Legacy (flat) mode ───────────────────────────────────────────────────────


class NpcOutput(BaseModel):
    """Structured LLM output for a legacy NPC generation request."""

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


# ── Mock factories for structured mode ──────────────────────────────────────


def _mock_combat_npc(title: str) -> CombatNpc:
    return CombatNpc.model_validate({
        "character_type": "combat_npc",
        "identity": {"name": title, "creature_type": "Medium humanoid", "role": "TBD"},
        "challenge": {"rating": "1", "xp": 200},
        "combat": {
            "armor_class": {"value": 12, "source": "leather armor"},
            "hit_points": {"value": 11, "formula": "2d8+2"},
            "speed": "30 ft.",
        },
        "ability_scores": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
        "actions": [{"name": "Shortsword", "description": "+2 to hit, 1d6 piercing"}],
    })


def _mock_roleplay_npc(title: str) -> RoleplayNpc:
    return RoleplayNpc.model_validate({
        "character_type": "roleplay_npc",
        "identity": {"name": title, "race": "Human", "occupation": "Commoner", "alignment": "N"},
        "personality": {"traits": ["TBD"], "ideals": ["TBD"], "bonds": ["TBD"], "flaws": ["TBD"]},
        "appearance": {"description": "TBD"},
        "relationships": [],
        "plot_hooks": [{"hook": "TBD", "tier": "minor"}],
    })


def _mock_player_character(title: str) -> PlayerCharacter:
    return PlayerCharacter.model_validate({
        "character_type": "player_character",
        "identity": {
            "name": title, "race": "Human", "class": "Fighter", "level": 1,
            "background": "Soldier", "alignment": "N",
        },
        "ability_scores": {
            "method": "standard_array",
            "final_scores": {"str": 15, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 8},
            "modifiers": {"str": 2, "dex": 2, "con": 1, "int": 1, "wis": 0, "cha": -1},
        },
        "combat": {
            "armor_class": {"value": 16, "source": "chain mail"},
            "hit_points": {"max": 12, "formula": "1d10+2"},
            "speed": "30 ft.",
            "proficiency_bonus": 2,
        },
        "proficiencies": {"armor": ["all"], "weapons": ["simple", "martial"]},
        "features": [],
        "equipment": [{"name": "Longsword", "quantity": 1}],
        "personality": {"traits": ["TBD"], "ideals": ["TBD"], "bonds": ["TBD"], "flaws": ["TBD"]},
    })


_MOCK_FACTORIES = {
    "player_character": _mock_player_character,
    "combat_npc": _mock_combat_npc,
    "roleplay_npc": _mock_roleplay_npc,
}


# ── Public entry point ───────────────────────────────────────────────────────


async def generate_npc(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D NPC draft.

    If ``request.constraints`` contains ``npc_type`` (one of
    ``player_character``, ``combat_npc``, ``roleplay_npc``), the generator
    produces structured JSON, stores it in ChromaDB, and renders it as a
    Jekyll draft. Otherwise it falls back to the legacy flat output.

    Args:
        request: The validated generation request.
        campaign: Name of the active campaign.
        provider_override: Optional provider name override.

    Returns:
        A :class:`GeneratedDraft` — either :class:`NpcDraft` (legacy) or
        :class:`StructuredNpcDraft` (structured).
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New NPC")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    npc_type = (request.constraints or {}).get("npc_type")

    # ── Legacy path ──────────────────────────────────────────────────────────
    if npc_type not in NPC_TYPE_NAMES:
        log.info("npc.generate.start", title=title, provider=provider, mode="legacy")
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
        log.info("npc.generate.done", title=title, slug=slug, mode="legacy")
        return NpcDraft(title=title, slug=slug, name=out.name, summary=out.summary, tags=out.tags)

    # ── Structured path ──────────────────────────────────────────────────────
    log.info(
        "npc.generate.start", title=title, provider=provider,
        mode="structured", npc_type=npc_type,
    )
    config = _TYPE_CONFIG[npc_type]

    if provider == "mock":
        log.debug("npc.generate.mock", npc_type=npc_type)
        npc_model = _MOCK_FACTORIES[npc_type](title)
    else:
        reference_text = _load_references(config["references"])
        system_prompt = f"{_SYSTEM_PROMPT}\n\n{config['system_suffix']}\n\n{reference_text}"
        user_prompt = (
            f"Campaign: {campaign}\n\nUser prompt: {request.prompt}\n\n"
            f"Generate a {npc_type.replace('_', ' ')} named '{title}'."
        )
        npc_model = await run_generation(
            output_type=config["model"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            provider=provider,
            settings=settings,
        )

    # Store in ChromaDB
    from llm_api.services.vector_store import store_npc
    from llm_api.services.ids import content_id

    npc_id = str(content_id(kind="npc", campaign=campaign, slug=slug))
    npc_data = npc_model.model_dump(by_alias=True)
    store_npc(npc_id=npc_id, campaign=campaign, npc_data=npc_data)

    # Render to Jekyll draft
    draft = render_npc_draft(npc=npc_model, title=title, slug=slug)
    log.info("npc.generate.done", title=title, slug=slug, npc_type=npc_type)
    return draft
