from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.fixture(autouse=True)
def reset_chroma_client():
    """Reset the global ChromaDB client between tests."""
    yield
    from llm_api.services import vector_store
    vector_store.reset_client()


@pytest.fixture
def tmp_chroma(monkeypatch, tmp_path):
    """Point ChromaDB at a temp directory."""
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))
    return tmp_path / "chroma"


def test_store_and_retrieve_npc(tmp_chroma):
    from llm_api.services.vector_store import store_npc, get_npc

    npc_data = {
        "character_type": "combat_npc",
        "identity": {"name": "Test Goblin", "creature_type": "Small humanoid", "role": "Ambusher"},
        "challenge": {"rating": "1/4", "xp": 50},
        "combat": {
            "armor_class": {"value": 12, "source": "leather"},
            "hit_points": {"value": 7, "formula": "2d6"},
            "speed": "30 ft.",
        },
        "ability_scores": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
        "actions": [{"name": "Scimitar", "description": "+4 to hit, 1d6+2 slashing"}],
    }
    npc_id = store_npc(
        npc_id="test-id-1",
        campaign="test-campaign",
        npc_data=npc_data,
    )
    assert npc_id == "test-id-1"

    retrieved = get_npc(npc_id="test-id-1")
    assert retrieved is not None
    assert retrieved["identity"]["name"] == "Test Goblin"


def test_get_missing_npc_returns_none(tmp_chroma):
    from llm_api.services.vector_store import get_npc

    assert get_npc(npc_id="nonexistent") is None


def test_update_npc(tmp_chroma):
    from llm_api.services.vector_store import store_npc, get_npc, update_npc

    npc_data = {
        "character_type": "roleplay_npc",
        "identity": {"name": "Old Meg", "race": "Human", "occupation": "Herbalist", "alignment": "NG"},
        "personality": {"traits": ["Quiet"], "ideals": ["Peace"], "bonds": ["Garden"], "flaws": ["Shy"]},
        "appearance": {"description": "Old woman"},
        "relationships": [],
        "plot_hooks": [{"hook": "Knows a secret", "tier": "minor"}],
    }
    store_npc(npc_id="meg-1", campaign="test-campaign", npc_data=npc_data)

    npc_data["identity"]["name"] = "Old Meg the Wise"
    update_npc(npc_id="meg-1", npc_data=npc_data)

    retrieved = get_npc(npc_id="meg-1")
    assert retrieved["identity"]["name"] == "Old Meg the Wise"


def test_search_npcs_by_text(tmp_chroma):
    from llm_api.services.vector_store import store_npc, search_npcs

    store_npc(
        npc_id="goblin-1",
        campaign="test-campaign",
        npc_data={
            "character_type": "combat_npc",
            "identity": {"name": "Sneaky Goblin", "creature_type": "Goblin", "role": "Scout"},
            "challenge": {"rating": "1/4", "xp": 50},
            "combat": {
                "armor_class": {"value": 12, "source": "leather"},
                "hit_points": {"value": 7, "formula": "2d6"},
                "speed": "30 ft.",
            },
            "ability_scores": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8},
            "actions": [{"name": "Dagger", "description": "+4 to hit"}],
        },
    )
    results = search_npcs(query="goblin scout", campaign="test-campaign", limit=5)
    assert len(results) >= 1
    assert results[0]["identity"]["name"] == "Sneaky Goblin"
