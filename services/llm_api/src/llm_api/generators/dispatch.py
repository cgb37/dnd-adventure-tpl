from __future__ import annotations

from llm_api.models.requests import GenerateRequest
from llm_api.models.generated import GeneratedDraft
from llm_api.services.errors import ApiError

from llm_api.generators.npc import generate_npc
from llm_api.generators.monster import generate_monster
from llm_api.generators.encounter import generate_encounter
from llm_api.generators.chapter import generate_chapter
from llm_api.generators.location import generate_location


SUPPORTED_KINDS: tuple[str, ...] = (
    "npc",
    "monster",
    "encounter",
    "chapter",
    "location",
)


async def generate_for_kind(
    *, kind: str, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    match kind:
        case "npc":
            return await generate_npc(request=request, campaign=campaign, provider_override=provider_override)
        case "monster":
            return await generate_monster(request=request, campaign=campaign, provider_override=provider_override)
        case "encounter":
            return await generate_encounter(request=request, campaign=campaign, provider_override=provider_override)
        case "chapter":
            return await generate_chapter(request=request, campaign=campaign, provider_override=provider_override)
        case "location":
            return await generate_location(request=request, campaign=campaign, provider_override=provider_override)
        case _:
            raise ApiError(
                code="unsupported_kind",
                message=f"Unsupported kind: {kind}",
                status_code=400,
            )
