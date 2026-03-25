from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")

EXAMPLES_DIR = (
    Path(__file__).resolve().parents[3]
    / "ai" / "skills" / "rpg-character-gen" / "assets" / "examples"
)


def test_player_character_validates_example():
    from llm_api.models.npc_types import PlayerCharacter

    data = json.loads((EXAMPLES_DIR / "character.json").read_text())
    pc = PlayerCharacter.model_validate(data)
    assert pc.character_type == "player_character"
    assert pc.identity.name == "Caelynn Amakiir"
    assert pc.identity.level == 5


def test_combat_npc_validates_example():
    from llm_api.models.npc_types import CombatNpc

    data = json.loads((EXAMPLES_DIR / "npc.json").read_text())
    npc = CombatNpc.model_validate(data)
    assert npc.character_type == "combat_npc"
    assert npc.identity.name == "Kareth Voss, the Gray Fang"
    assert npc.challenge.xp == 700


def test_roleplay_npc_validates_minimal():
    from llm_api.models.npc_types import RoleplayNpc

    data = {
        "character_type": "roleplay_npc",
        "identity": {
            "name": "Old Meg",
            "race": "Human",
            "occupation": "Herbalist",
            "alignment": "Neutral Good",
        },
        "personality": {
            "traits": ["Mumbles to her cat"],
            "ideals": ["Knowledge"],
            "bonds": ["Her garden"],
            "flaws": ["Paranoid about strangers"],
        },
        "appearance": {
            "description": "Hunched woman with wild grey hair",
        },
        "relationships": [
            {"name": "Mayor Harken", "relationship": "Supplier", "attitude": "Grudging respect"}
        ],
        "plot_hooks": [
            {"hook": "She saw something in the woods last night", "tier": "minor"}
        ],
    }
    npc = RoleplayNpc.model_validate(data)
    assert npc.identity.name == "Old Meg"
    assert len(npc.plot_hooks) == 1


def test_npc_type_literal_values():
    """Each model only accepts its own character_type value."""
    from llm_api.models.npc_types import PlayerCharacter

    with pytest.raises(Exception):
        PlayerCharacter.model_validate({"character_type": "combat_npc", "identity": {}})
