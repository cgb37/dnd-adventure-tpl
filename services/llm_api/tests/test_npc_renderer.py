from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")

EXAMPLES_DIR = (
    Path(__file__).resolve().parents[3]
    / "ai" / "skills" / "rpg-character-gen" / "assets" / "examples"
)


def test_combat_npc_renders_frontmatter():
    from llm_api.generators.npc_renderer import render_npc_draft
    from llm_api.models.npc_types import CombatNpc

    data = json.loads((EXAMPLES_DIR / "npc.json").read_text())
    npc = CombatNpc.model_validate(data)
    draft = render_npc_draft(npc=npc, title="Kareth Voss", slug="kareth-voss")

    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test")
    assert fm["layout"] == "npc"
    assert fm["npc_type"] == "combat_npc"
    assert fm["name"] == "Kareth Voss, the Gray Fang"
    assert "npc_type" in draft.required_yaml_keys()


def test_combat_npc_renders_markdown_body():
    from llm_api.generators.npc_renderer import render_npc_draft
    from llm_api.models.npc_types import CombatNpc

    data = json.loads((EXAMPLES_DIR / "npc.json").read_text())
    npc = CombatNpc.model_validate(data)
    draft = render_npc_draft(npc=npc, title="Kareth Voss", slug="kareth-voss")

    body = draft.markdown_body
    assert "CR 3" in body or "Challenge" in body
    assert "Kareth Voss" in body
    assert "Longsword" in body


def test_player_character_renders_frontmatter():
    from llm_api.generators.npc_renderer import render_npc_draft
    from llm_api.models.npc_types import PlayerCharacter

    data = json.loads((EXAMPLES_DIR / "character.json").read_text())
    pc = PlayerCharacter.model_validate(data)
    draft = render_npc_draft(npc=pc, title="Caelynn Amakiir", slug="caelynn-amakiir")

    fm = draft.frontmatter_yaml(draft_id=uuid.uuid4(), campaign="test")
    assert fm["npc_type"] == "player_character"
    assert fm["name"] == "Caelynn Amakiir"


def test_player_character_renders_spells():
    from llm_api.generators.npc_renderer import render_npc_draft
    from llm_api.models.npc_types import PlayerCharacter

    data = json.loads((EXAMPLES_DIR / "character.json").read_text())
    pc = PlayerCharacter.model_validate(data)
    draft = render_npc_draft(npc=pc, title="Caelynn", slug="caelynn")

    assert "Healing Word" in draft.markdown_body
    assert "Vicious Mockery" in draft.markdown_body


def test_roleplay_npc_renders_plot_hooks():
    from llm_api.generators.npc_renderer import render_npc_draft
    from llm_api.models.npc_types import RoleplayNpc

    npc = RoleplayNpc.model_validate({
        "character_type": "roleplay_npc",
        "identity": {"name": "Old Meg", "race": "Human", "occupation": "Herbalist", "alignment": "NG"},
        "personality": {"traits": ["Mumbles"], "ideals": ["Peace"], "bonds": ["Garden"], "flaws": ["Shy"]},
        "appearance": {"description": "Hunched woman"},
        "relationships": [{"name": "Mayor", "relationship": "Client", "attitude": "Wary"}],
        "plot_hooks": [{"hook": "Saw something in the woods", "tier": "minor"}],
    })
    draft = render_npc_draft(npc=npc, title="Old Meg", slug="old-meg")

    assert "Plot Hooks" in draft.markdown_body
    assert "Saw something in the woods" in draft.markdown_body
