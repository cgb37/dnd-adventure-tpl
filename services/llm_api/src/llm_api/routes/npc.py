"""NPC CRUD and search routes.

Provides GET, PUT, and search endpoints for NPCs stored in ChromaDB.
The PUT endpoint updates the ChromaDB record and re-renders the Jekyll draft.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from llm_api.generators.npc_renderer import render_npc_draft
from llm_api.models.npc_types import CombatNpc, NPC_TYPE_NAMES, PlayerCharacter, RoleplayNpc
from llm_api.services.drafts import write_draft
from llm_api.services.errors import ApiError
from llm_api.services.responses import ok
from llm_api.services.security import require_api_key
from llm_api.services.vector_store import get_npc, search_npcs, update_npc

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/npcs", tags=["npcs"])

_TYPE_MAP: dict[str, type] = {
    "player_character": PlayerCharacter,
    "combat_npc": CombatNpc,
    "roleplay_npc": RoleplayNpc,
}


@router.get("/search", dependencies=[Depends(require_api_key)])
async def search(
    q: str = Query(min_length=1),
    campaign: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> JSONResponse:
    """Semantic search for NPCs by text query."""
    results = search_npcs(query=q, campaign=campaign, limit=limit)
    return JSONResponse(status_code=200, content={"data": results})


@router.get("/{npc_id}", dependencies=[Depends(require_api_key)])
async def get_npc_by_id(npc_id: str) -> JSONResponse:
    """Retrieve an NPC by its ID."""
    npc_data = get_npc(npc_id=npc_id)
    if npc_data is None:
        raise ApiError(
            code="npc_not_found",
            message=f"NPC {npc_id!r} not found",
            status_code=404,
        )
    return ok(npc_data)


class UpdateNpcRequest(BaseModel):
    npc_data: dict[str, Any]
    campaign: str
    title: str
    slug: str


@router.put("/{npc_id}", dependencies=[Depends(require_api_key)])
async def update_npc_by_id(npc_id: str, req: UpdateNpcRequest) -> JSONResponse:
    """Update an NPC in ChromaDB and re-render its Jekyll draft."""
    existing = get_npc(npc_id=npc_id)
    if existing is None:
        raise ApiError(
            code="npc_not_found",
            message=f"NPC {npc_id!r} not found",
            status_code=404,
        )

    update_npc(npc_id=npc_id, npc_data=req.npc_data)
    log.info("npc.update", npc_id=npc_id, slug=req.slug)

    # Re-render Jekyll draft when the NPC type is recognised
    npc_type = req.npc_data.get("character_type")
    if npc_type in NPC_TYPE_NAMES:
        npc_model = _TYPE_MAP[npc_type].model_validate(req.npc_data)
        draft = render_npc_draft(npc=npc_model, title=req.title, slug=req.slug)
        try:
            draft_id = uuid.UUID(npc_id)
        except ValueError:
            draft_id = uuid.uuid5(uuid.NAMESPACE_URL, npc_id)
        write_draft(
            kind="npc",
            campaign=req.campaign,
            slug=req.slug,
            title=req.title,
            yaml_frontmatter=draft.frontmatter_yaml(draft_id=draft_id, campaign=req.campaign),
            markdown_body=draft.markdown_body,
        )

    name = req.npc_data.get("identity", {}).get("name", req.title)
    return ok({"npc_id": npc_id, "name": name, "updated": True})
