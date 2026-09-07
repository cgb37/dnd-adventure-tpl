from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from write_draft import (
    DraftWriteError,
    compute_draft_id,
    find_repo_root,
    get_active_campaign,
    render_frontmatter,
    write_draft,
)


def test_render_frontmatter_handles_strings_lists_bools():
    yaml_text = render_frontmatter({
        "layout": "encounter",
        "title": "Goblin Ambush",
        "search": True,
        "tags": ["goblins", "ambush"],
    })
    assert "layout: encounter" in yaml_text
    assert "search: true" in yaml_text
    assert "tags:\n  - goblins\n  - ambush" in yaml_text


def test_render_frontmatter_handles_empty_list():
    yaml_text = render_frontmatter({"tags": []})
    assert "tags: []" in yaml_text


def test_render_frontmatter_quotes_numeric_looking_strings():
    yaml_text = render_frontmatter({"chapter": "01", "episode": "02"})
    assert 'chapter: "01"' in yaml_text
    assert 'episode: "02"' in yaml_text


def test_render_frontmatter_quotes_yaml_bool_and_null_lookalikes():
    yaml_text = render_frontmatter({"a": "yes", "b": "null", "c": "true"})
    assert 'a: "yes"' in yaml_text
    assert 'b: "null"' in yaml_text
    assert 'c: "true"' in yaml_text


def test_render_frontmatter_quotes_leading_indicator_chars():
    yaml_text = render_frontmatter({"title": "*The Wailing Deep*"})
    assert 'title: "*The Wailing Deep*"' in yaml_text


def test_render_frontmatter_does_not_quote_ordinary_hyphen_prefixed_words():
    # PyYAML's safe_dump only treats a leading "-" as ambiguous when the string IS "-"
    # or starts with "- " (the block-sequence-entry form) - an ordinary word that merely
    # starts with a hyphen, like "-foo", is emitted unquoted.
    yaml_text = render_frontmatter({"k": "-foo", "j": "-1a", "m": "-yes"})
    assert "k: -foo" in yaml_text
    assert "j: -1a" in yaml_text
    assert "m: -yes" in yaml_text


def test_render_frontmatter_does_not_quote_none_string():
    # "none" (any case) is not a YAML 1.1 null lookalike - only null/Null/NULL/~/"" are.
    yaml_text = render_frontmatter({"k": "none", "j": "None", "m": "NONE"})
    assert "k: none" in yaml_text
    assert "j: None" in yaml_text
    assert "m: NONE" in yaml_text


def test_render_frontmatter_quotes_standalone_or_leading_hyphen_space():
    # These really are YAML-ambiguous: a bare "-" or "- " prefix reads as a block
    # sequence entry marker.
    yaml_text = render_frontmatter({"k": "-", "j": "- foo"})
    assert 'k: "-"' in yaml_text
    assert 'j: "- foo"' in yaml_text


def test_render_frontmatter_handles_nested_dict():
    yaml_text = render_frontmatter({
        "ac": {"value": 17, "type": "natural armor"},
    })
    assert yaml_text == "ac:\n  value: 17\n  type: natural armor\n"
    parsed = yaml.safe_load(yaml_text)
    assert parsed["ac"] == {"value": 17, "type": "natural armor"}


def test_render_frontmatter_handles_two_level_nested_dict():
    yaml_text = render_frontmatter({
        "abilities": {
            "strength": {"score": 15, "modifier": "+2"},
            "dexterity": {"score": 12, "modifier": "+1"},
        },
    })
    expected = (
        "abilities:\n"
        "  strength:\n"
        '    score: 15\n'
        '    modifier: "+2"\n'
        "  dexterity:\n"
        "    score: 12\n"
        '    modifier: "+1"\n'
    )
    assert yaml_text == expected
    parsed = yaml.safe_load(yaml_text)
    assert parsed["abilities"]["strength"]["modifier"] == "+2"
    assert parsed["abilities"]["dexterity"]["score"] == 12


def test_render_frontmatter_handles_list_of_flat_dicts():
    yaml_text = render_frontmatter({
        "saving_throws": [{"name": "dexterity", "modifier": "+3"}],
    })
    expected = "saving_throws:\n  - name: dexterity\n    modifier: \"+3\"\n"
    assert yaml_text == expected
    parsed = yaml.safe_load(yaml_text)
    assert parsed["saving_throws"] == [{"name": "dexterity", "modifier": "+3"}]


def test_render_frontmatter_handles_list_of_dicts_with_nested_list_of_dicts():
    yaml_text = render_frontmatter({
        "actions": [
            {
                "name": "Bite",
                "type": "Melee Weapon Attack",
                "hit_bonus": 4,
                "damage": [{"type": "piercing", "dice": "1d10 + 2", "avg": 7}],
            }
        ],
    })
    parsed = yaml.safe_load(yaml_text)
    assert parsed["actions"][0]["name"] == "Bite"
    assert parsed["actions"][0]["hit_bonus"] == 4
    assert parsed["actions"][0]["damage"][0]["type"] == "piercing"
    assert parsed["actions"][0]["damage"][0]["avg"] == 7


def test_render_frontmatter_handles_multiline_string_as_block_scalar():
    yaml_text = render_frontmatter({
        "challenges": {
            "traps": "- Rune Trap: DC 14 Str save\n- Pit: 2d6 falling damage",
        }
    })
    expected = (
        "challenges:\n"
        "  traps: |\n"
        "    - Rune Trap: DC 14 Str save\n"
        "    - Pit: 2d6 falling damage\n"
    )
    assert yaml_text == expected
    parsed = yaml.safe_load(yaml_text)
    # YAML "|" block scalars use clip chomping: a single trailing newline is
    # always kept on load, even though the source string had none.
    assert parsed["challenges"]["traps"] == (
        "- Rune Trap: DC 14 Str save\n- Pit: 2d6 falling damage\n"
    )


def test_render_frontmatter_full_monster_payload_round_trips():
    frontmatter = {
        "layout": "monster",
        "title": "Green Dragon Wyrmling",
        "permalink": "/monsters/:slug",
        "category": "monster",
        "chapter": "01",
        "episode": "01",
        "scene": "01",
        "jumbo": "",
        "thumb": "monster-thumb.png",
        "portrait": "monster-portrait.png",
        "tags": ["dragon", "forest"],
        "search": True,
        "excerpt_separator": "",
        "name": "Green Dragon Wyrmling",
        "description": "A young cunning dragon.",
        "type": "Dragon",
        "size": "Medium",
        "ac": {"value": 17, "type": "natural armor"},
        "hp": "38 (7d8 + 7)",
        "hp_dice": "7d8",
        "speed": "30 ft., fly 60 ft.",
        "abilities": {
            "strength": {"score": 15, "modifier": "+2"},
            "dexterity": {"score": 12, "modifier": "+1"},
            "constitution": {"score": 13, "modifier": "+1"},
            "intelligence": {"score": 14, "modifier": "+2"},
            "wisdom": {"score": 11, "modifier": "+0"},
            "charisma": {"score": 13, "modifier": "+1"},
        },
        "saving_throws": [
            {"name": "dexterity", "modifier": "+3"},
            {"name": "constitution", "modifier": "+3"},
        ],
        "skills": "Perception +4, Stealth +3",
        "senses": "blindsight 10 ft., darkvision 60 ft.",
        "languages": ["Draconic"],
        "challenge": 3,
        "challenge_xp": 700,
        "special_abilities": [
            {"name": "Enchanting Breath", "description": "A cone of enchanting gas."}
        ],
        "actions": [
            {
                "name": "Bite",
                "type": "Melee Weapon Attack",
                "hit_bonus": 4,
                "reach": "5 ft.",
                "target": "one target",
                "damage": [
                    {"type": "piercing", "dice": "1d10 + 2", "avg": 7},
                    {"type": "poison", "dice": "1d6", "avg": 3},
                ],
            }
        ],
        "reactions": [{"name": "Parry", "description": "Adds 2 to AC."}],
        "treasure": "1d6 x 10 gp",
        "notes": "The Rune Stone has magical properties.",
    }
    yaml_text = render_frontmatter(frontmatter)
    parsed = yaml.safe_load(yaml_text)
    assert parsed["abilities"]["strength"]["modifier"] == "+2"
    assert parsed["actions"][0]["damage"][0]["type"] == "piercing"
    assert parsed["actions"][0]["damage"][1]["avg"] == 3
    assert parsed["saving_throws"][1]["name"] == "constitution"
    assert parsed["challenge"] == 3
    assert parsed["challenge_xp"] == 700
    assert parsed["special_abilities"][0]["name"] == "Enchanting Breath"
    assert parsed["reactions"][0]["description"] == "Adds 2 to AC."
    assert parsed["tags"] == ["dragon", "forest"]


def test_render_frontmatter_full_location_payload_round_trips():
    frontmatter = {
        "layout": "location",
        "title": "Whispering Woods",
        "permalink": "/locations/:slug",
        "category": "location",
        "chapter": "01",
        "episode": "01",
        "scene": "01",
        "jumbo": "",
        "thumb": "location-thumb.png",
        "portrait": "location-portrait.png",
        "tags": ["forest", "magic"],
        "search": True,
        "excerpt_separator": "",
        "name": "Whispering Woods",
        "type": "Enchanted Forest",
        "description": "A dense, mist-shrouded forest.",
        "challenges": {
            "traps": "- Mystic Vines: DC 14 Str save\n- Illusory Pitfalls: 2d6 falling",
            "ambushes": "- Enchanted Beasts: phase spiders ambush",
            "puzzles": "- Elemental Runes: align the stones",
            "hazards": "- Magical Mists: DC 13 Wis save",
        },
        "secrets": ["A hidden grove grants visions."],
        "plot_hooks": ["Einar seeks Maelis the Arcane."],
        "npcs": [
            {"name": "Maelis the Arcane", "description": "A reclusive wizard."},
            {"name": "The Guardian Spirit", "description": "A spectral protector."},
        ],
        "environmental_features": ["Ancient Trees", "Glowing Fungi"],
        "additional_notes": "Tailor this location to fit the campaign.",
    }
    yaml_text = render_frontmatter(frontmatter)
    parsed = yaml.safe_load(yaml_text)
    # YAML "|" block scalars use clip chomping: a single trailing newline is
    # always kept on load, even though the source strings had none.
    assert parsed["challenges"]["traps"] == (
        "- Mystic Vines: DC 14 Str save\n- Illusory Pitfalls: 2d6 falling\n"
    )
    # "hazards" is a single-line string (no "\n"), so it's a plain quoted
    # scalar, not a block scalar - no trailing newline is added.
    assert parsed["challenges"]["hazards"] == "- Magical Mists: DC 13 Wis save"
    assert parsed["npcs"][0]["name"] == "Maelis the Arcane"
    assert parsed["npcs"][1]["description"] == "A spectral protector."
    assert parsed["secrets"] == ["A hidden grove grants visions."]
    assert parsed["plot_hooks"] == ["Einar seeks Maelis the Arcane."]
    assert parsed["environmental_features"] == ["Ancient Trees", "Glowing Fungi"]
    assert parsed["additional_notes"] == "Tailor this location to fit the campaign."


def test_compute_draft_id_is_deterministic():
    first = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    second = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    assert first == second


def test_compute_draft_id_matches_known_namespace():
    # Same formula as services/llm_api/src/llm_api/services/ids.py::content_id().
    namespace = uuid.UUID("c9b4f65f-2d5a-4e62-9e04-8b6ea6c60b41")
    expected = uuid.uuid5(namespace, "encounter:test-campaign:goblin-ambush")
    actual = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    assert actual == expected


def test_get_active_campaign_missing_file_raises(tmp_path: Path):
    with pytest.raises(DraftWriteError) as exc_info:
        get_active_campaign(tmp_path)
    assert exc_info.value.code == "no_active_campaign"


def test_get_active_campaign_empty_file_raises(tmp_path: Path):
    (tmp_path / ".active-campaign").write_text("   \n", encoding="utf-8")
    with pytest.raises(DraftWriteError) as exc_info:
        get_active_campaign(tmp_path)
    assert exc_info.value.code == "no_active_campaign"


def test_get_active_campaign_reads_file(tmp_path: Path):
    (tmp_path / ".active-campaign").write_text("my-campaign\n", encoding="utf-8")
    assert get_active_campaign(tmp_path) == "my-campaign"


def test_write_draft_writes_frontmatter_and_body(tmp_path: Path):
    path = write_draft(
        repo_root=tmp_path,
        kind="encounter",
        campaign="test-campaign",
        slug="goblin-ambush",
        title="Goblin Ambush",
        frontmatter={"layout": "encounter", "title": "Goblin Ambush", "tags": ["goblins"]},
        body="A pack of goblins lies in wait.",
    )
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "layout: encounter" in text
    assert "# Goblin Ambush" in text
    assert "A pack of goblins lies in wait." in text
    assert path == tmp_path / "campaigns" / "test-campaign" / "_drafts" / "encounter" / "goblin-ambush.md"


def test_find_repo_root_walks_up_to_git_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == tmp_path


def test_find_repo_root_raises_when_not_found(tmp_path: Path):
    with pytest.raises(DraftWriteError) as exc_info:
        find_repo_root(tmp_path)
    assert exc_info.value.code == "repo_root_not_found"


def test_cli_end_to_end(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".active-campaign").write_text("test-campaign\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    script = Path(__file__).resolve().parents[1] / "write_draft.py"
    payload = {
        "kind": "encounter",
        "slug": "goblin-ambush",
        "title": "Goblin Ambush",
        "frontmatter": {"layout": "encounter", "title": "Goblin Ambush", "tags": []},
        "body": "Body text.",
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert out["path"] == "campaigns/test-campaign/_drafts/encounter/goblin-ambush.md"
    assert (tmp_path / out["path"]).exists()


def test_cli_no_active_campaign_exits_nonzero(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)

    script = Path(__file__).resolve().parents[1] / "write_draft.py"
    payload = {
        "kind": "encounter",
        "slug": "goblin-ambush",
        "title": "Goblin Ambush",
        "frontmatter": {},
        "body": "Body.",
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "no_active_campaign"
