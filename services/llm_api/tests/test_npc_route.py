from __future__ import annotations

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("RELAX_AUTH_ON_LOCALHOST", "true")


@pytest.fixture
def tmp_chroma(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))
    from llm_api.services.vector_store import reset_client
    reset_client()
    return tmp_path


@pytest.fixture
def client(tmp_chroma):
    from fastapi.testclient import TestClient
    from llm_api.app import create_app

    app = create_app()
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_get_npc_not_found(client):
    resp = client.get("/v1/npcs/nonexistent")
    assert resp.status_code == 404


def test_put_npc_creates_and_updates(client, tmp_chroma, monkeypatch):
    monkeypatch.setattr(
        "llm_api.services.active_campaign.get_repo_root",
        lambda: tmp_chroma,
    )

    from llm_api.services.vector_store import store_npc

    npc_data = {
        "character_type": "roleplay_npc",
        "identity": {"name": "Old Meg", "race": "Human", "occupation": "Herbalist", "alignment": "NG"},
        "personality": {"traits": ["Quiet"], "ideals": ["Peace"], "bonds": ["Garden"], "flaws": ["Shy"]},
        "appearance": {"description": "Hunched woman"},
        "relationships": [],
        "plot_hooks": [{"hook": "Knows a secret", "tier": "minor"}],
    }
    store_npc(npc_id="meg-1", campaign="test", npc_data=npc_data)

    npc_data["identity"]["name"] = "Old Meg the Wise"
    resp = client.put(
        "/v1/npcs/meg-1",
        json={"npc_data": npc_data, "campaign": "test", "title": "Old Meg", "slug": "old-meg"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Old Meg the Wise"


def test_search_npcs(client, tmp_chroma):
    from llm_api.services.vector_store import store_npc

    store_npc(npc_id="gob-1", campaign="test", npc_data={
        "character_type": "combat_npc",
        "identity": {"name": "Sneaky Goblin", "creature_type": "Goblin", "role": "Scout"},
    })
    resp = client.get("/v1/npcs/search", params={"q": "goblin", "campaign": "test"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1
