"""ChromaDB-backed vector store for NPC data.

Stores the full NPC JSON as metadata alongside a text embedding derived
from the NPC's name, role/occupation, and key traits. This enables
semantic search for future MCP access.
"""
from __future__ import annotations

import json
from typing import Any

import chromadb
import structlog

from llm_api.services.active_campaign import get_repo_root
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = Settings()  # pyright: ignore[reportCallIssue]
        root = get_repo_root()
        path = root / settings.chromadb_path
        _client = chromadb.PersistentClient(path=str(path))
        log.info("vector_store.init", path=str(path))
    return _client


def _get_collection() -> chromadb.Collection:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    return _get_client().get_or_create_collection(name=settings.chromadb_collection)


def _build_document(npc_data: dict[str, Any]) -> str:
    """Build a searchable text document from NPC data for embedding."""
    parts: list[str] = []
    identity = npc_data.get("identity", {})
    parts.append(identity.get("name", ""))
    for field in ("role", "occupation", "creature_type"):
        if val := identity.get(field):
            parts.append(val)
    parts.append(npc_data.get("character_type", ""))

    # Personality traits if present
    personality = npc_data.get("personality", {})
    for trait_list in ("traits", "ideals", "bonds", "flaws"):
        for item in personality.get(trait_list, []):
            parts.append(item)

    # Tactical notes if present
    if notes := npc_data.get("tactical_notes"):
        parts.append(notes)

    return " | ".join(p for p in parts if p)


def store_npc(
    *,
    npc_id: str,
    campaign: str,
    npc_data: dict[str, Any],
) -> str:
    """Store an NPC in ChromaDB.

    Args:
        npc_id: Unique identifier for this NPC.
        campaign: Campaign name (stored as metadata for filtering).
        npc_data: Full NPC JSON matching one of the NPC type schemas.

    Returns:
        The npc_id.
    """
    collection = _get_collection()
    document = _build_document(npc_data)

    collection.upsert(
        ids=[npc_id],
        documents=[document],
        metadatas=[{
            "campaign": campaign,
            "character_type": npc_data.get("character_type", ""),
            "name": npc_data.get("identity", {}).get("name", ""),
            "npc_json": json.dumps(npc_data),
        }],
    )
    log.info("vector_store.stored", npc_id=npc_id, campaign=campaign)
    return npc_id


def get_npc(*, npc_id: str) -> dict[str, Any] | None:
    """Retrieve an NPC by ID. Returns the parsed JSON or None."""
    collection = _get_collection()
    result = collection.get(ids=[npc_id])
    if not result["ids"]:
        return None
    metadata = result["metadatas"][0]  # type: ignore[index]
    return json.loads(metadata["npc_json"])


def update_npc(*, npc_id: str, npc_data: dict[str, Any]) -> None:
    """Update an existing NPC's data in ChromaDB.

    Args:
        npc_id: ID of the NPC to update.
        npc_data: Updated NPC JSON.

    Raises:
        ValueError: If the NPC does not exist.
    """
    collection = _get_collection()
    # Retrieve existing metadata to preserve campaign
    existing = collection.get(ids=[npc_id])
    if not existing["ids"]:
        raise ValueError(f"NPC {npc_id} not found")
    campaign = existing["metadatas"][0]["campaign"]  # type: ignore[index]

    document = _build_document(npc_data)
    collection.update(
        ids=[npc_id],
        documents=[document],
        metadatas=[{
            "campaign": campaign,
            "character_type": npc_data.get("character_type", ""),
            "name": npc_data.get("identity", {}).get("name", ""),
            "npc_json": json.dumps(npc_data),
        }],
    )
    log.info("vector_store.updated", npc_id=npc_id)


def search_npcs(
    *,
    query: str,
    campaign: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Semantic search for NPCs by text query.

    Args:
        query: Natural-language search query.
        campaign: Filter results to this campaign.
        limit: Max results to return.

    Returns:
        List of NPC data dicts, ordered by relevance.
    """
    collection = _get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={"campaign": campaign},
    )
    npcs: list[dict[str, Any]] = []
    for metadata in (results["metadatas"] or [[]])[0]:
        npcs.append(json.loads(metadata["npc_json"]))
    return npcs


def reset_client() -> None:
    """Reset the global client. Used in tests."""
    global _client
    _client = None
