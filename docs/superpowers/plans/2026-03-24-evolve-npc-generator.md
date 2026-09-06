# Evolve NPC Generator — Structured JSON, Vector DB, Editable NPCs

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolve the existing `npc.py` generator to produce predictable, structured JSON for three NPC types (player_character, combat_npc, roleplay_npc), persist them in ChromaDB for future MCP access, output YAML frontmatter + Markdown for Jekyll, and support editing NPCs over time.

**Architecture:** The NPC generator grows from a flat (name, summary, tags) output to rich structured JSON defined by standalone JSON schemas. ChromaDB stores the canonical JSON alongside vector embeddings for semantic search. The existing Jekyll draft pipeline is preserved — structured JSON is rendered into YAML frontmatter + Markdown body. A new `npc_type` frontmatter key distinguishes the three types while reusing the existing `npc` layout. Editability is achieved via a PUT endpoint that updates ChromaDB, re-renders the Jekyll draft, and bumps a version counter.

**Tech Stack:** Python 3.12, FastAPI, pydantic 2.x, chromadb, pydantic-ai, structlog, pytest, pytest-asyncio

**Design Decisions (confirmed with user):**
- Vector DB: ChromaDB (simple, local, swappable later)
- Canonical data: ChromaDB is source of truth (JSON stored as metadata)
- Editability: Both directions — API edits re-render Markdown; future Markdown→JSON sync is out of scope for v1
- Dice roller: Port into `llm_api` as a Python module
- Schemas: Standalone JSON schema files → Pydantic models generated from them
- Jekyll layouts: Reuse existing `npc` layout; add `npc_type` key to frontmatter
- Reference data: Summarized/trimmed, embedded selectively per NPC type

---

## File Map

| Purpose | Path |
|---------|------|
| JSON schemas | `services/llm_api/src/llm_api/generators/schemas/player_character.json` |
| | `services/llm_api/src/llm_api/generators/schemas/combat_npc.json` |
| | `services/llm_api/src/llm_api/generators/schemas/roleplay_npc.json` |
| Pydantic models (from schemas) | `services/llm_api/src/llm_api/models/npc_types.py` |
| Dice roller module | `services/llm_api/src/llm_api/services/dice_roller.py` |
| Reference summaries | `services/llm_api/src/llm_api/generators/references/races_brief.md` |
| | `services/llm_api/src/llm_api/generators/references/classes_brief.md` |
| | `services/llm_api/src/llm_api/generators/references/npc_combat_brief.md` |
| | `services/llm_api/src/llm_api/generators/references/npc_roleplay_brief.md` |
| ChromaDB service | `services/llm_api/src/llm_api/services/vector_store.py` |
| Evolved NPC generator | `services/llm_api/src/llm_api/generators/npc.py` (modify) |
| NPC renderer (JSON → Jekyll) | `services/llm_api/src/llm_api/generators/npc_renderer.py` |
| Dispatch | `services/llm_api/src/llm_api/generators/dispatch.py` (modify) |
| Generate route | `services/llm_api/src/llm_api/routes/generate.py` (modify) |
| NPC edit route | `services/llm_api/src/llm_api/routes/npc.py` |
| Config | `services/llm_api/src/llm_api/services/config.py` (modify) |
| Tests | `services/llm_api/tests/test_dice_roller.py` |
| | `services/llm_api/tests/test_npc_types.py` |
| | `services/llm_api/tests/test_vector_store.py` |
| | `services/llm_api/tests/test_generator_npc.py` (modify) |
| | `services/llm_api/tests/test_npc_renderer.py` |
| | `services/llm_api/tests/test_npc_route.py` |

---

## Task 1: Add `chromadb` dependency

**Files:**
- Modify: `services/llm_api/pyproject.toml`

**Step 1: Add chromadb to dependencies**

In `pyproject.toml`, add `"chromadb>=0.5"` to the `dependencies` list and `"datamodel-code-generator>=0.26"` to `[project.optional-dependencies] dev`.

```toml
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "pydantic-ai>=0.0.49",
  "httpx>=0.27",
  "pyyaml>=6.0",
  "python-slugify>=8.0",
  "structlog>=24.4",
  "chromadb>=0.5",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "httpx>=0.27",
  "ruff>=0.6",
  "datamodel-code-generator>=0.26",
]
```

**Step 2: Install**

Run: `cd services/llm_api && pip install -e ".[dev]"`
Expected: Successful install with chromadb and datamodel-code-generator

**Step 3: Commit**

```bash
git add services/llm_api/pyproject.toml
git commit -m "feat(deps): add chromadb and datamodel-code-generator"
```

---

## Task 2: Create JSON schemas for three NPC types

These are the standalone schema files that define the canonical shape of each NPC type. Pydantic models will be generated from these in Task 3.

**Files:**
- Create: `services/llm_api/src/llm_api/generators/schemas/player_character.json`
- Create: `services/llm_api/src/llm_api/generators/schemas/combat_npc.json`
- Create: `services/llm_api/src/llm_api/generators/schemas/roleplay_npc.json`

**Step 1: Create `player_character.json`**

Derive from the skill's example at `ai/skills/rpg-character-gen/assets/examples/character.json`. The schema must capture the full structure: identity, ability_scores, combat, proficiencies, features, equipment, spellcasting, personality.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "player_character",
  "title": "PlayerCharacter",
  "description": "A D&D 5e player character with full sheet data.",
  "type": "object",
  "required": ["character_type", "identity", "ability_scores", "combat", "proficiencies", "features", "equipment", "personality"],
  "properties": {
    "character_type": { "const": "player_character" },
    "identity": {
      "type": "object",
      "required": ["name", "race", "class", "level", "background", "alignment"],
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 100 },
        "race": { "type": "string" },
        "subrace": { "type": ["string", "null"] },
        "class": { "type": "string" },
        "subclass": { "type": ["string", "null"] },
        "level": { "type": "integer", "minimum": 1, "maximum": 20 },
        "background": { "type": "string" },
        "alignment": { "type": "string" },
        "xp": { "type": "integer", "minimum": 0 }
      }
    },
    "ability_scores": {
      "type": "object",
      "required": ["method", "final_scores", "modifiers"],
      "properties": {
        "method": { "type": "string", "enum": ["roll", "standard_array", "point_buy"] },
        "base_scores": { "$ref": "#/$defs/ability_block" },
        "racial_bonuses": { "$ref": "#/$defs/ability_block" },
        "asi_bonuses": { "$ref": "#/$defs/ability_block" },
        "final_scores": { "$ref": "#/$defs/ability_block" },
        "modifiers": { "$ref": "#/$defs/ability_block" }
      }
    },
    "combat": {
      "type": "object",
      "required": ["armor_class", "hit_points", "speed", "proficiency_bonus"],
      "properties": {
        "armor_class": {
          "type": "object",
          "properties": {
            "value": { "type": "integer" },
            "source": { "type": "string" }
          }
        },
        "hit_points": {
          "type": "object",
          "properties": {
            "max": { "type": "integer" },
            "formula": { "type": "string" }
          }
        },
        "hit_dice": {
          "type": "object",
          "properties": {
            "total": { "type": "string" },
            "remaining": { "type": "string" }
          }
        },
        "speed": { "type": "string" },
        "initiative": { "type": "integer" },
        "proficiency_bonus": { "type": "integer" }
      }
    },
    "proficiencies": {
      "type": "object",
      "properties": {
        "armor": { "type": "array", "items": { "type": "string" } },
        "weapons": { "type": "array", "items": { "type": "string" } },
        "tools": { "type": "array", "items": { "type": "string" } },
        "saving_throws": { "type": "array", "items": { "type": "string" } },
        "skills": { "type": "array", "items": { "type": "string" } },
        "languages": { "type": "array", "items": { "type": "string" } }
      }
    },
    "features": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "source", "description"],
        "properties": {
          "name": { "type": "string" },
          "source": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "equipment": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "quantity"],
        "properties": {
          "name": { "type": "string" },
          "quantity": { "type": "integer", "minimum": 1 },
          "properties": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "spellcasting": {
      "type": ["object", "null"],
      "properties": {
        "ability": { "type": "string" },
        "spell_save_dc": { "type": "integer" },
        "spell_attack_bonus": { "type": "integer" },
        "cantrips": { "type": "array", "items": { "type": "string" } },
        "spell_slots": { "type": "object", "additionalProperties": { "type": "integer" } },
        "spells_known": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "level": { "type": "integer" },
              "description": { "type": "string" }
            }
          }
        }
      }
    },
    "personality": {
      "type": "object",
      "required": ["traits", "ideals", "bonds", "flaws"],
      "properties": {
        "traits": { "type": "array", "items": { "type": "string" } },
        "ideals": { "type": "array", "items": { "type": "string" } },
        "bonds": { "type": "array", "items": { "type": "string" } },
        "flaws": { "type": "array", "items": { "type": "string" } },
        "backstory_hook": { "type": "string" }
      }
    }
  },
  "$defs": {
    "ability_block": {
      "type": "object",
      "required": ["str", "dex", "con", "int", "wis", "cha"],
      "properties": {
        "str": { "type": "integer" },
        "dex": { "type": "integer" },
        "con": { "type": "integer" },
        "int": { "type": "integer" },
        "wis": { "type": "integer" },
        "cha": { "type": "integer" }
      }
    }
  }
}
```

**Step 2: Create `combat_npc.json`**

Derive from `ai/skills/rpg-character-gen/assets/examples/npc.json`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "combat_npc",
  "title": "CombatNpc",
  "description": "A D&D 5e combat NPC with full stat block.",
  "type": "object",
  "required": ["character_type", "identity", "challenge", "combat", "ability_scores", "actions"],
  "properties": {
    "character_type": { "const": "combat_npc" },
    "identity": {
      "type": "object",
      "required": ["name", "creature_type", "role"],
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 100 },
        "creature_type": { "type": "string" },
        "role": { "type": "string" }
      }
    },
    "challenge": {
      "type": "object",
      "required": ["rating", "xp"],
      "properties": {
        "rating": { "type": "string" },
        "xp": { "type": "integer", "minimum": 0 }
      }
    },
    "combat": {
      "type": "object",
      "required": ["armor_class", "hit_points", "speed"],
      "properties": {
        "armor_class": {
          "type": "object",
          "properties": {
            "value": { "type": "integer" },
            "source": { "type": "string" }
          }
        },
        "hit_points": {
          "type": "object",
          "properties": {
            "value": { "type": "integer" },
            "formula": { "type": "string" }
          }
        },
        "speed": { "type": "string" }
      }
    },
    "ability_scores": { "$ref": "#/$defs/ability_block" },
    "defenses": {
      "type": "object",
      "properties": {
        "saving_throws": { "type": "array", "items": { "type": "string" } },
        "skills": { "type": "array", "items": { "type": "string" } },
        "damage_resistances": { "type": "array", "items": { "type": "string" } },
        "damage_immunities": { "type": "array", "items": { "type": "string" } },
        "condition_immunities": { "type": "array", "items": { "type": "string" } }
      }
    },
    "senses": { "type": "string" },
    "languages": { "type": "string" },
    "traits": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "description"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "description"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "reactions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "description"],
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "spellcasting": {
      "type": ["object", "null"],
      "properties": {
        "ability": { "type": "string" },
        "spell_save_dc": { "type": "integer" },
        "spell_attack_bonus": { "type": "integer" },
        "spells": { "type": "array", "items": { "type": "string" } }
      }
    },
    "tactical_notes": { "type": "string" }
  },
  "$defs": {
    "ability_block": {
      "type": "object",
      "required": ["str", "dex", "con", "int", "wis", "cha"],
      "properties": {
        "str": { "type": "integer" },
        "dex": { "type": "integer" },
        "con": { "type": "integer" },
        "int": { "type": "integer" },
        "wis": { "type": "integer" },
        "cha": { "type": "integer" }
      }
    }
  }
}
```

**Step 3: Create `roleplay_npc.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "roleplay_npc",
  "title": "RoleplayNpc",
  "description": "A D&D 5e roleplay-focused NPC with personality, secrets, and plot hooks.",
  "type": "object",
  "required": ["character_type", "identity", "personality", "appearance", "relationships", "plot_hooks"],
  "properties": {
    "character_type": { "const": "roleplay_npc" },
    "identity": {
      "type": "object",
      "required": ["name", "race", "occupation", "alignment"],
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 100 },
        "race": { "type": "string" },
        "occupation": { "type": "string" },
        "alignment": { "type": "string" },
        "age": { "type": "string" },
        "location": { "type": "string" }
      }
    },
    "personality": {
      "type": "object",
      "required": ["traits", "ideals", "bonds", "flaws"],
      "properties": {
        "traits": { "type": "array", "items": { "type": "string" } },
        "ideals": { "type": "array", "items": { "type": "string" } },
        "bonds": { "type": "array", "items": { "type": "string" } },
        "flaws": { "type": "array", "items": { "type": "string" } },
        "mannerisms": { "type": "string" },
        "speech_pattern": { "type": "string" },
        "motivation": { "type": "string" }
      }
    },
    "appearance": {
      "type": "object",
      "properties": {
        "description": { "type": "string" },
        "distinguishing_features": { "type": "array", "items": { "type": "string" } },
        "typical_attire": { "type": "string" }
      }
    },
    "secrets": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["secret", "impact"],
        "properties": {
          "secret": { "type": "string" },
          "impact": { "type": "string" },
          "known_by": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "relationships": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "relationship", "attitude"],
        "properties": {
          "name": { "type": "string" },
          "relationship": { "type": "string" },
          "attitude": { "type": "string" }
        }
      }
    },
    "plot_hooks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["hook", "tier"],
        "properties": {
          "hook": { "type": "string" },
          "tier": { "type": "string", "enum": ["minor", "major", "campaign"] }
        }
      }
    },
    "stat_block": {
      "type": ["object", "null"],
      "description": "Optional abbreviated stat block for major roleplay NPCs who might see combat.",
      "properties": {
        "armor_class": { "type": "integer" },
        "hit_points": { "type": "integer" },
        "challenge_rating": { "type": "string" },
        "notable_abilities": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

**Step 4: Verify schemas are valid JSON**

Run: `cd services/llm_api && python -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('src/llm_api/generators/schemas').glob('*.json')]; print('All schemas valid')"`
Expected: `All schemas valid`

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/generators/schemas/
git commit -m "feat(schemas): add JSON schemas for player_character, combat_npc, roleplay_npc"
```

---

## Task 3: Generate Pydantic models from JSON schemas

Use `datamodel-code-generator` to generate Pydantic models, then hand-tune the result.

**Files:**
- Create: `services/llm_api/src/llm_api/models/npc_types.py`
- Test: `services/llm_api/tests/test_npc_types.py`

**Step 1: Write the failing test**

```python
# services/llm_api/tests/test_npc_types.py
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")

EXAMPLES_DIR = (
    Path(__file__).resolve().parents[4]
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
```

**Step 2: Run tests to verify they fail**

Run: `cd services/llm_api && python -m pytest tests/test_npc_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'llm_api.models.npc_types'`

**Step 3: Generate Pydantic models**

Run: `cd services/llm_api && datamodel-codegen --input src/llm_api/generators/schemas/player_character.json --output /tmp/pc.py --output-model-type pydantic_v2.BaseModel`

Use the generated output as a starting point, then create the hand-tuned `npc_types.py` that combines all three types. The key is that each model must:
- Accept the example JSON from the skill
- Use `Literal` for `character_type` to discriminate the union
- Mark optional fields appropriately

Create `services/llm_api/src/llm_api/models/npc_types.py`:

```python
"""Pydantic models for the three NPC types.

Generated from the JSON schemas in ``generators/schemas/`` and hand-tuned.
Each model uses a ``Literal`` character_type so they can be discriminated
in a tagged union.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────

class AbilityBlock(BaseModel):
    str_: int = Field(alias="str")
    dex: int
    con: int
    int_: int = Field(alias="int")
    wis: int
    cha: int

    model_config = {"populate_by_name": True}


class NamedDescription(BaseModel):
    name: str
    description: str


class NamedSourceDescription(BaseModel):
    name: str
    source: str
    description: str


class ArmorClass(BaseModel):
    value: int
    source: str = ""


class SpellInfo(BaseModel):
    name: str
    level: int
    description: str = ""


# ── Player Character ────────────────────────────────────────────────

class PcIdentity(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    race: str
    subrace: str | None = None
    class_: str = Field(alias="class")
    subclass: str | None = None
    level: int = Field(ge=1, le=20)
    background: str
    alignment: str
    xp: int = Field(default=0, ge=0)

    model_config = {"populate_by_name": True}


class PcAbilityScores(BaseModel):
    method: Literal["roll", "standard_array", "point_buy"]
    base_scores: AbilityBlock | None = None
    racial_bonuses: AbilityBlock | None = None
    asi_bonuses: AbilityBlock | None = None
    final_scores: AbilityBlock
    modifiers: AbilityBlock


class PcHitPoints(BaseModel):
    max: int
    formula: str = ""


class PcHitDice(BaseModel):
    total: str
    remaining: str


class PcCombat(BaseModel):
    armor_class: ArmorClass
    hit_points: PcHitPoints
    hit_dice: PcHitDice | None = None
    speed: str
    initiative: int = 0
    proficiency_bonus: int


class PcProficiencies(BaseModel):
    armor: list[str] = Field(default_factory=list)
    weapons: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    saving_throws: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class PcEquipment(BaseModel):
    name: str
    quantity: int = 1
    properties: list[str] = Field(default_factory=list)


class PcSpellcasting(BaseModel):
    ability: str
    spell_save_dc: int
    spell_attack_bonus: int
    cantrips: list[str] = Field(default_factory=list)
    spell_slots: dict[str, int] = Field(default_factory=dict)
    spells_known: list[SpellInfo] = Field(default_factory=list)


class PcPersonality(BaseModel):
    traits: list[str]
    ideals: list[str]
    bonds: list[str]
    flaws: list[str]
    backstory_hook: str = ""


class PlayerCharacter(BaseModel):
    character_type: Literal["player_character"] = "player_character"
    identity: PcIdentity
    ability_scores: PcAbilityScores
    combat: PcCombat
    proficiencies: PcProficiencies
    features: list[NamedSourceDescription] = Field(default_factory=list)
    equipment: list[PcEquipment] = Field(default_factory=list)
    spellcasting: PcSpellcasting | None = None
    personality: PcPersonality


# ── Combat NPC ──────────────────────────────────────────────────────

class CombatIdentity(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    creature_type: str
    role: str


class ChallengeRating(BaseModel):
    rating: str
    xp: int = Field(ge=0)


class CombatHitPoints(BaseModel):
    value: int
    formula: str = ""


class CombatStats(BaseModel):
    armor_class: ArmorClass
    hit_points: CombatHitPoints
    speed: str


class CombatDefenses(BaseModel):
    saving_throws: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    damage_resistances: list[str] = Field(default_factory=list)
    damage_immunities: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)


class CombatSpellcasting(BaseModel):
    ability: str
    spell_save_dc: int
    spell_attack_bonus: int
    spells: list[str] = Field(default_factory=list)


class CombatNpc(BaseModel):
    character_type: Literal["combat_npc"] = "combat_npc"
    identity: CombatIdentity
    challenge: ChallengeRating
    combat: CombatStats
    ability_scores: AbilityBlock
    defenses: CombatDefenses = Field(default_factory=CombatDefenses)
    senses: str = ""
    languages: str = ""
    traits: list[NamedDescription] = Field(default_factory=list)
    actions: list[NamedDescription]
    reactions: list[NamedDescription] = Field(default_factory=list)
    spellcasting: CombatSpellcasting | None = None
    tactical_notes: str = ""


# ── Roleplay NPC ────────────────────────────────────────────────────

class RoleplayIdentity(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    race: str
    occupation: str
    alignment: str
    age: str = ""
    location: str = ""


class RoleplayPersonality(BaseModel):
    traits: list[str]
    ideals: list[str]
    bonds: list[str]
    flaws: list[str]
    mannerisms: str = ""
    speech_pattern: str = ""
    motivation: str = ""


class Appearance(BaseModel):
    description: str = ""
    distinguishing_features: list[str] = Field(default_factory=list)
    typical_attire: str = ""


class Secret(BaseModel):
    secret: str
    impact: str
    known_by: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    name: str
    relationship: str
    attitude: str


class PlotHook(BaseModel):
    hook: str
    tier: Literal["minor", "major", "campaign"]


class RoleplayStatBlock(BaseModel):
    armor_class: int = 10
    hit_points: int = 1
    challenge_rating: str = "0"
    notable_abilities: list[str] = Field(default_factory=list)


class RoleplayNpc(BaseModel):
    character_type: Literal["roleplay_npc"] = "roleplay_npc"
    identity: RoleplayIdentity
    personality: RoleplayPersonality
    appearance: Appearance = Field(default_factory=Appearance)
    secrets: list[Secret] = Field(default_factory=list)
    relationships: list[Relationship]
    plot_hooks: list[PlotHook]
    stat_block: RoleplayStatBlock | None = None


# ── Discriminated union ─────────────────────────────────────────────

NpcUnion = Annotated[
    Union[PlayerCharacter, CombatNpc, RoleplayNpc],
    Field(discriminator="character_type"),
]

NPC_TYPE_NAMES: tuple[str, ...] = ("player_character", "combat_npc", "roleplay_npc")
```

**Step 4: Run tests to verify they pass**

Run: `cd services/llm_api && python -m pytest tests/test_npc_types.py -v`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/models/npc_types.py services/llm_api/tests/test_npc_types.py
git commit -m "feat(models): add Pydantic models for player_character, combat_npc, roleplay_npc"
```

---

## Task 4: Port dice roller into `llm_api`

**Files:**
- Create: `services/llm_api/src/llm_api/services/dice_roller.py`
- Test: `services/llm_api/tests/test_dice_roller.py`

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_dice_roller.py
from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


def test_rolled_returns_six_scores():
    from llm_api.services.dice_roller import generate_rolled

    result = generate_rolled(seed=42)
    assert len(result["scores"]) == 6
    assert all(3 <= s <= 18 for s in result["scores"])
    assert len(result["modifiers"]) == 6


def test_standard_array_returns_fixed_scores():
    from llm_api.services.dice_roller import generate_standard_array

    result = generate_standard_array()
    assert result["scores"] == [15, 14, 13, 12, 10, 8]
    assert len(result["modifiers"]) == 6


def test_point_buy_valid():
    from llm_api.services.dice_roller import generate_point_buy

    scores = [15, 14, 13, 12, 10, 8]  # standard array = 27 points
    result = generate_point_buy(scores)
    assert result["total_points"] == 27
    assert result["valid"] is True


def test_point_buy_over_budget():
    from llm_api.services.dice_roller import generate_point_buy

    scores = [15, 15, 15, 15, 15, 15]
    result = generate_point_buy(scores)
    assert result["valid"] is False


def test_point_buy_score_out_of_range():
    from llm_api.services.dice_roller import generate_point_buy

    with pytest.raises(ValueError, match="8.*15"):
        generate_point_buy([7, 14, 13, 12, 10, 8])


def test_rolled_seed_reproducible():
    from llm_api.services.dice_roller import generate_rolled

    a = generate_rolled(seed=99)
    b = generate_rolled(seed=99)
    assert a["scores"] == b["scores"]
```

**Step 2: Run tests to verify they fail**

Run: `cd services/llm_api && python -m pytest tests/test_dice_roller.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

Port from `ai/skills/rpg-character-gen/scripts/dice_roller.py`, adapting to a library API (no CLI, no argparse).

```python
"""Dice roller for D&D 5e ability score generation.

Ported from ai/skills/rpg-character-gen/scripts/dice_roller.py.
Three methods: roll (4d6 drop lowest), standard array, point buy.
"""
from __future__ import annotations

import random

STANDARD_ARRAY: list[int] = [15, 14, 13, 12, 10, 8]

# Point-buy cost table (score → cost). Scores 8–15 only.
_POINT_COSTS: dict[int, int] = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9,
}
_POINT_BUY_BUDGET = 27


def _modifier(score: int) -> int:
    return (score - 10) // 2


def generate_rolled(*, seed: int | None = None) -> dict:
    """Roll 4d6-drop-lowest for six ability scores.

    Args:
        seed: Optional RNG seed for reproducibility.

    Returns:
        Dict with ``scores`` (sorted descending), ``modifiers``, ``total``, ``average``.
    """
    rng = random.Random(seed)
    scores: list[int] = []
    for _ in range(6):
        rolls = sorted([rng.randint(1, 6) for _ in range(4)])
        scores.append(sum(rolls[1:]))  # drop lowest
    scores.sort(reverse=True)
    modifiers = [_modifier(s) for s in scores]
    return {
        "scores": scores,
        "modifiers": modifiers,
        "total": sum(scores),
        "average": round(sum(scores) / 6, 1),
    }


def generate_standard_array() -> dict:
    """Return the standard array [15, 14, 13, 12, 10, 8]."""
    scores = list(STANDARD_ARRAY)
    return {
        "scores": scores,
        "modifiers": [_modifier(s) for s in scores],
    }


def generate_point_buy(scores: list[int]) -> dict:
    """Validate and cost a set of six point-buy ability scores.

    Args:
        scores: Exactly 6 scores, each between 8 and 15 inclusive.

    Returns:
        Dict with ``scores``, ``modifiers``, ``costs``, ``total_points``, ``valid``.

    Raises:
        ValueError: If any score is outside 8–15 or count != 6.
    """
    if len(scores) != 6:
        raise ValueError(f"Expected 6 scores, got {len(scores)}")
    for s in scores:
        if s < 8 or s > 15:
            raise ValueError(f"Point-buy scores must be 8–15, got {s}")

    costs = [_POINT_COSTS[s] for s in scores]
    total = sum(costs)
    return {
        "scores": scores,
        "modifiers": [_modifier(s) for s in scores],
        "costs": costs,
        "total_points": total,
        "valid": total <= _POINT_BUY_BUDGET,
    }
```

**Step 4: Run tests to verify they pass**

Run: `cd services/llm_api && python -m pytest tests/test_dice_roller.py -v`
Expected: 6 tests PASS

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/services/dice_roller.py services/llm_api/tests/test_dice_roller.py
git commit -m "feat(dice-roller): port ability score generation into llm_api"
```

---

## Task 5: Create trimmed reference summaries

Extract condensed versions of the skill's reference files for embedding in LLM prompts. These are static text files, not code — no tests needed.

**Files:**
- Create: `services/llm_api/src/llm_api/generators/references/races_brief.md`
- Create: `services/llm_api/src/llm_api/generators/references/classes_brief.md`
- Create: `services/llm_api/src/llm_api/generators/references/npc_combat_brief.md`
- Create: `services/llm_api/src/llm_api/generators/references/npc_roleplay_brief.md`

**Step 1: Create trimmed references**

Read the full reference files from `ai/skills/rpg-character-gen/references/` and distill each to ~200-400 words. Focus on:
- `races_brief.md` — Race names, ASI bonuses, key traits (one line per race). Used for `player_character` prompts.
- `classes_brief.md` — Class names, hit die, primary ability, key features by tier. Used for `player_character` prompts.
- `npc_combat_brief.md` — CR/HP/AC guidelines, common stat block patterns. Used for `combat_npc` prompts.
- `npc_roleplay_brief.md` — Personality frameworks, motivation templates. Used for `roleplay_npc` prompts.

Each file should start with a comment: `<!-- Trimmed from ai/skills/rpg-character-gen/references/ for LLM prompt embedding -->`.

**Step 2: Verify files exist and are reasonable size**

Run: `wc -w services/llm_api/src/llm_api/generators/references/*.md`
Expected: Each file between 100–500 words

**Step 3: Commit**

```bash
git add services/llm_api/src/llm_api/generators/references/
git commit -m "feat(references): add trimmed reference summaries for NPC generation prompts"
```

---

## Task 6: ChromaDB vector store service

**Files:**
- Create: `services/llm_api/src/llm_api/services/vector_store.py`
- Modify: `services/llm_api/src/llm_api/services/config.py`
- Test: `services/llm_api/tests/test_vector_store.py`

**Step 1: Add config settings for ChromaDB**

Add to `Settings` in `config.py`:

```python
# ChromaDB
chromadb_path: str = ".chromadb"  # relative to repo root
chromadb_collection: str = "npcs"
```

**Step 2: Write the failing tests**

```python
# services/llm_api/tests/test_vector_store.py
from __future__ import annotations

import json
import os
import tempfile

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


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
```

**Step 3: Run tests to verify they fail**

Run: `cd services/llm_api && python -m pytest tests/test_vector_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 4: Write the implementation**

```python
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

from llm_api.services import active_campaign
from llm_api.services.config import Settings

log = structlog.get_logger(__name__)

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = Settings()  # pyright: ignore[reportCallIssue]
        root = active_campaign.get_repo_root()
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
    """Update an existing NPC's data in ChromaDB."""
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
```

**Step 5: Run tests to verify they pass**

Run: `cd services/llm_api && python -m pytest tests/test_vector_store.py -v`
Expected: 4 tests PASS

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/services/vector_store.py services/llm_api/tests/test_vector_store.py services/llm_api/src/llm_api/services/config.py
git commit -m "feat(vector-store): add ChromaDB service for NPC storage and search"
```

---

## Task 7: NPC renderer — convert structured JSON to Jekyll Markdown

This module takes a typed NPC model and produces the YAML frontmatter dict and Markdown body for Jekyll rendering.

**Files:**
- Create: `services/llm_api/src/llm_api/generators/npc_renderer.py`
- Test: `services/llm_api/tests/test_npc_renderer.py`

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_npc_renderer.py
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")

EXAMPLES_DIR = (
    Path(__file__).resolve().parents[4]
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
```

**Step 2: Run tests to verify they fail**

Run: `cd services/llm_api && python -m pytest tests/test_npc_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
"""Render typed NPC models into Jekyll-compatible drafts.

Takes a validated NPC Pydantic model (any of the three types) and produces
a GeneratedDraft with YAML frontmatter and Markdown body suitable for the
existing ``npc`` Jekyll layout.
"""
from __future__ import annotations

from llm_api.models.generated import GeneratedDraft
from llm_api.models.npc_types import (
    CombatNpc,
    PlayerCharacter,
    RoleplayNpc,
)


class StructuredNpcDraft(GeneratedDraft):
    """Jekyll-ready NPC draft produced from structured NPC data."""

    def __init__(
        self,
        *,
        title: str,
        slug: str,
        npc_type: str,
        name: str,
        tags: list[str],
        markdown_body: str,
    ):
        self.title = title
        self.slug = slug
        self.markdown_body = markdown_body
        self._npc_type = npc_type
        self._name = name
        self._tags = tags

    def required_yaml_keys(self) -> list[str]:
        return [
            "layout", "title", "name", "npc_type", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
        return {
            "layout": "npc",
            "title": self.title,
            "name": self._name,
            "npc_type": self._npc_type,
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


def render_npc_draft(
    *,
    npc: PlayerCharacter | CombatNpc | RoleplayNpc,
    title: str,
    slug: str,
) -> StructuredNpcDraft:
    """Render any NPC type into a StructuredNpcDraft."""
    match npc:
        case PlayerCharacter():
            body = _render_player_character(npc)
            name = npc.identity.name
            tags = [npc.identity.race, npc.identity.class_, f"Level {npc.identity.level}"]
        case CombatNpc():
            body = _render_combat_npc(npc)
            name = npc.identity.name
            tags = [npc.identity.creature_type, f"CR {npc.challenge.rating}"]
        case RoleplayNpc():
            body = _render_roleplay_npc(npc)
            name = npc.identity.name
            tags = [npc.identity.race, npc.identity.occupation]

    return StructuredNpcDraft(
        title=title,
        slug=slug,
        npc_type=npc.character_type,
        name=name,
        tags=tags,
        markdown_body=body,
    )


# ── Renderers ───────────────────────────────────────────────────────


def _render_player_character(pc: PlayerCharacter) -> str:
    lines: list[str] = []
    ident = pc.identity

    lines.append(f"**{ident.name}** — Level {ident.level} {ident.race} {ident.class_}")
    if ident.subclass:
        lines[-1] += f" ({ident.subclass})"
    lines.append(f"**Background:** {ident.background} | **Alignment:** {ident.alignment}")
    lines.append("")

    # Ability scores
    lines.append("## Ability Scores")
    fs = pc.ability_scores.final_scores
    mods = pc.ability_scores.modifiers
    lines.append(
        f"| STR | DEX | CON | INT | WIS | CHA |\n"
        f"|-----|-----|-----|-----|-----|-----|\n"
        f"| {fs.str_} ({mods.str_:+d}) | {fs.dex} ({mods.dex:+d}) "
        f"| {fs.con} ({mods.con:+d}) | {fs.int_} ({mods.int_:+d}) "
        f"| {fs.wis} ({mods.wis:+d}) | {fs.cha} ({mods.cha:+d}) |"
    )
    lines.append("")

    # Combat
    lines.append("## Combat")
    lines.append(f"- **AC:** {pc.combat.armor_class.value} ({pc.combat.armor_class.source})")
    lines.append(f"- **HP:** {pc.combat.hit_points.max}")
    lines.append(f"- **Speed:** {pc.combat.speed}")
    lines.append(f"- **Proficiency Bonus:** +{pc.combat.proficiency_bonus}")
    lines.append("")

    # Features
    if pc.features:
        lines.append("## Features")
        for feat in pc.features:
            lines.append(f"- **{feat.name}** ({feat.source}): {feat.description}")
        lines.append("")

    # Equipment
    if pc.equipment:
        lines.append("## Equipment")
        for item in pc.equipment:
            props = ", ".join(item.properties) if item.properties else ""
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            lines.append(f"- {item.name}{qty}" + (f" ({props})" if props else ""))
        lines.append("")

    # Spellcasting
    if pc.spellcasting:
        sc = pc.spellcasting
        lines.append("## Spellcasting")
        lines.append(f"**{sc.ability}** — DC {sc.spell_save_dc}, +{sc.spell_attack_bonus} to hit")
        if sc.cantrips:
            lines.append(f"**Cantrips:** {', '.join(sc.cantrips)}")
        if sc.spell_slots:
            slots = ", ".join(f"{k}: {v}" for k, v in sc.spell_slots.items())
            lines.append(f"**Spell Slots:** {slots}")
        for spell in sc.spells_known:
            lines.append(f"- **{spell.name}** (Level {spell.level}): {spell.description}")
        lines.append("")

    # Personality
    lines.append("## Personality")
    for trait in pc.personality.traits:
        lines.append(f"- {trait}")
    if pc.personality.backstory_hook:
        lines.append(f"\n**Backstory:** {pc.personality.backstory_hook}")

    return "\n".join(lines)


def _render_combat_npc(npc: CombatNpc) -> str:
    lines: list[str] = []
    ident = npc.identity

    lines.append(f"**{ident.name}**")
    lines.append(f"*{ident.creature_type}*")
    lines.append(f"*{ident.role}*")
    lines.append("")
    lines.append(f"**Challenge {npc.challenge.rating}** ({npc.challenge.xp} XP)")
    lines.append("")

    # Combat stats
    lines.append(f"- **AC:** {npc.combat.armor_class.value} ({npc.combat.armor_class.source})")
    lines.append(f"- **HP:** {npc.combat.hit_points.value} ({npc.combat.hit_points.formula})")
    lines.append(f"- **Speed:** {npc.combat.speed}")
    lines.append("")

    # Ability scores
    ab = npc.ability_scores
    lines.append("## Ability Scores")
    lines.append(
        f"| STR | DEX | CON | INT | WIS | CHA |\n"
        f"|-----|-----|-----|-----|-----|-----|\n"
        f"| {ab.str_} | {ab.dex} | {ab.con} | {ab.int_} | {ab.wis} | {ab.cha} |"
    )
    lines.append("")

    # Traits
    if npc.traits:
        lines.append("## Traits")
        for trait in npc.traits:
            lines.append(f"**{trait.name}.** {trait.description}")
            lines.append("")

    # Actions
    lines.append("## Actions")
    for action in npc.actions:
        lines.append(f"**{action.name}.** {action.description}")
        lines.append("")

    # Reactions
    if npc.reactions:
        lines.append("## Reactions")
        for reaction in npc.reactions:
            lines.append(f"**{reaction.name}.** {reaction.description}")
            lines.append("")

    # Tactical notes
    if npc.tactical_notes:
        lines.append("## Tactical Notes")
        lines.append(npc.tactical_notes)

    return "\n".join(lines)


def _render_roleplay_npc(npc: RoleplayNpc) -> str:
    lines: list[str] = []
    ident = npc.identity

    lines.append(f"**{ident.name}** — {ident.race} {ident.occupation}")
    lines.append(f"**Alignment:** {ident.alignment}")
    if ident.age:
        lines.append(f"**Age:** {ident.age}")
    if ident.location:
        lines.append(f"**Location:** {ident.location}")
    lines.append("")

    # Appearance
    if npc.appearance.description:
        lines.append("## Appearance")
        lines.append(npc.appearance.description)
        if npc.appearance.distinguishing_features:
            for feat in npc.appearance.distinguishing_features:
                lines.append(f"- {feat}")
        lines.append("")

    # Personality
    lines.append("## Personality")
    for trait in npc.personality.traits:
        lines.append(f"- {trait}")
    if npc.personality.mannerisms:
        lines.append(f"**Mannerisms:** {npc.personality.mannerisms}")
    if npc.personality.speech_pattern:
        lines.append(f"**Speech:** {npc.personality.speech_pattern}")
    if npc.personality.motivation:
        lines.append(f"**Motivation:** {npc.personality.motivation}")
    lines.append("")

    # Secrets
    if npc.secrets:
        lines.append("## Secrets")
        for secret in npc.secrets:
            lines.append(f"- **{secret.secret}** — Impact: {secret.impact}")
        lines.append("")

    # Relationships
    if npc.relationships:
        lines.append("## Relationships")
        for rel in npc.relationships:
            lines.append(f"- **{rel.name}** ({rel.relationship}) — {rel.attitude}")
        lines.append("")

    # Plot hooks
    if npc.plot_hooks:
        lines.append("## Plot Hooks")
        for hook in npc.plot_hooks:
            lines.append(f"- [{hook.tier.upper()}] {hook.hook}")
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `cd services/llm_api && python -m pytest tests/test_npc_renderer.py -v`
Expected: 5 tests PASS

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/generators/npc_renderer.py services/llm_api/tests/test_npc_renderer.py
git commit -m "feat(npc-renderer): convert structured NPC models to Jekyll Markdown drafts"
```

---

## Task 8: Evolve the NPC generator

Modify `npc.py` to accept an `npc_type` constraint, use the appropriate Pydantic output model, embed trimmed reference data in the prompt, store results in ChromaDB, and produce a `StructuredNpcDraft`.

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/npc.py`
- Modify: `services/llm_api/tests/test_generator_npc.py`

**Step 1: Write the failing tests**

Add new tests to the existing test file:

```python
# Append to services/llm_api/tests/test_generator_npc.py

@pytest.mark.asyncio
async def test_generate_npc_with_combat_type_mock(monkeypatch, tmp_path):
    """Mock mode with npc_type=combat_npc returns StructuredNpcDraft."""
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))

    from llm_api.services.vector_store import reset_client
    reset_client()

    from llm_api.generators.npc import generate_npc
    from llm_api.generators.npc_renderer import StructuredNpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(
        prompt="A goblin ambush leader",
        title="Snarg",
        constraints={"npc_type": "combat_npc"},
    )
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, StructuredNpcDraft)
    assert draft._npc_type == "combat_npc"


@pytest.mark.asyncio
async def test_generate_npc_with_roleplay_type_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path / "chroma"))

    from llm_api.services.vector_store import reset_client
    reset_client()

    from llm_api.generators.npc import generate_npc
    from llm_api.generators.npc_renderer import StructuredNpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(
        prompt="A mysterious herbalist",
        title="Old Meg",
        constraints={"npc_type": "roleplay_npc"},
    )
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, StructuredNpcDraft)
    assert draft._npc_type == "roleplay_npc"


@pytest.mark.asyncio
async def test_generate_npc_without_type_falls_back_to_legacy():
    """No npc_type constraint → existing flat NPC behavior (backward compat)."""
    from llm_api.generators.npc import generate_npc
    from llm_api.generators.npc import NpcDraft
    from llm_api.models.requests import GenerateRequest

    req = GenerateRequest(prompt="A blacksmith", title="Tom")
    draft = await generate_npc(request=req, campaign="test-campaign")
    assert isinstance(draft, NpcDraft)
```

**Step 2: Run tests to verify the new tests fail**

Run: `cd services/llm_api && python -m pytest tests/test_generator_npc.py -v`
Expected: New tests FAIL, existing tests still PASS

**Step 3: Modify `npc.py`**

Keep the existing `NpcDraft` and `NpcOutput` for backward compatibility. Add a new code path when `constraints.npc_type` is set.

The key changes to `generate_npc()`:
1. Check `request.constraints` for `npc_type`
2. If present, use the appropriate structured output model (`PlayerCharacter`, `CombatNpc`, `RoleplayNpc`)
3. Build a richer system prompt that includes the trimmed reference data for that type
4. In mock mode, return a mock structured NPC
5. Store the result in ChromaDB
6. Render via `npc_renderer.render_npc_draft()`
7. If no `npc_type`, fall back to existing flat behavior

```python
"""NPC generator — produces D&D NPC drafts for a Jekyll campaign site.

Supports two modes:
- **Legacy** (no npc_type constraint): flat name/summary/tags output.
- **Structured** (npc_type in constraints): rich JSON matching the
  player_character, combat_npc, or roleplay_npc schemas.

The public entry point is :func:`generate_npc`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from llm_api.generators.base import resolve_title_and_slug, run_generation
from llm_api.generators.npc_renderer import render_npc_draft, StructuredNpcDraft
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

# Maps npc_type → (output Pydantic model, reference files to embed)
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
        "system_suffix": "Generate a D&D 5e roleplay NPC with personality, secrets, and plot hooks as structured JSON.",
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


# ── Legacy (flat) mode ──────────────────────────────────────────────

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
        return [
            "layout", "title", "name", "permalink", "category",
            "chapter", "episode", "scene", "jumbo", "thumb", "portrait",
            "tags", "search", "excerpt_separator", "id", "slug",
        ]

    def frontmatter_yaml(self, *, draft_id, campaign: str) -> dict:
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


# ── Mock data for structured mode ──────────────────────────────────

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


# ── Public entry point ──────────────────────────────────────────────

async def generate_npc(
    *, request: GenerateRequest, campaign: str, provider_override: str | None = None
) -> GeneratedDraft:
    """Generate a D&D NPC draft.

    If ``request.constraints`` contains ``npc_type`` (one of
    ``player_character``, ``combat_npc``, ``roleplay_npc``), the generator
    produces structured JSON, stores it in ChromaDB, and renders it as a
    Jekyll draft. Otherwise it falls back to the legacy flat output.
    """
    settings = Settings()  # pyright: ignore[reportCallIssue]
    title, slug = resolve_title_and_slug(request=request, fallback_title="New NPC")
    provider = (provider_override or settings.llm_provider or "").strip().lower()

    npc_type = (request.constraints or {}).get("npc_type")

    # ── Legacy path ─────────────────────────────────────────────
    if npc_type not in NPC_TYPE_NAMES:
        log.info("npc.generate.start", title=title, provider=provider, mode="legacy")
        if provider == "mock":
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
        return NpcDraft(title=title, slug=slug, name=out.name, summary=out.summary, tags=out.tags)

    # ── Structured path ─────────────────────────────────────────
    log.info("npc.generate.start", title=title, provider=provider, mode="structured", npc_type=npc_type)
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
```

**Step 4: Run all NPC tests**

Run: `cd services/llm_api && python -m pytest tests/test_generator_npc.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/generators/npc.py services/llm_api/tests/test_generator_npc.py
git commit -m "feat(npc): evolve generator to support structured NPC types with ChromaDB storage"
```

---

## Task 9: Add NPC edit/update API route

**Files:**
- Create: `services/llm_api/src/llm_api/routes/npc.py`
- Modify: `services/llm_api/src/llm_api/app.py` (register new router)
- Test: `services/llm_api/tests/test_npc_route.py`

**Step 1: Write the failing tests**

```python
# services/llm_api/tests/test_npc_route.py
from __future__ import annotations

import json
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
    return TestClient(app)


def test_get_npc_not_found(client):
    resp = client.get("/v1/npcs/nonexistent")
    assert resp.status_code == 404


def test_put_npc_creates_and_updates(client, tmp_chroma, monkeypatch):
    monkeypatch.setattr(
        "llm_api.services.active_campaign.get_repo_root",
        lambda: tmp_chroma,
    )

    # First, store an NPC via the vector store directly
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

    # Update via PUT
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
```

**Step 2: Run tests to verify they fail**

Run: `cd services/llm_api && python -m pytest tests/test_npc_route.py -v`
Expected: FAIL

**Step 3: Write the route**

```python
"""NPC CRUD and search routes.

Provides GET, PUT, and search endpoints for NPCs stored in ChromaDB.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from llm_api.services.security import require_api_key
from llm_api.services.vector_store import get_npc, update_npc, search_npcs
from llm_api.services.drafts import write_draft
from llm_api.services.errors import ApiError
from llm_api.services.responses import ok
from llm_api.models.npc_types import NPC_TYPE_NAMES, CombatNpc, PlayerCharacter, RoleplayNpc
from llm_api.generators.npc_renderer import render_npc_draft

router = APIRouter(prefix="/npcs", tags=["npcs"])


@router.get("/{npc_id}", dependencies=[Depends(require_api_key)])
async def get_npc_by_id(npc_id: str):
    """Retrieve an NPC by its ID."""
    npc_data = get_npc(npc_id=npc_id)
    if npc_data is None:
        raise ApiError(code="npc_not_found", message=f"NPC {npc_id} not found", status_code=404)
    return ok(npc_data)


class UpdateNpcRequest(BaseModel):
    npc_data: dict[str, Any]
    campaign: str
    title: str
    slug: str


@router.put("/{npc_id}", dependencies=[Depends(require_api_key)])
async def update_npc_by_id(npc_id: str, req: UpdateNpcRequest):
    """Update an NPC and re-render its Jekyll draft."""
    existing = get_npc(npc_id=npc_id)
    if existing is None:
        raise ApiError(code="npc_not_found", message=f"NPC {npc_id} not found", status_code=404)

    update_npc(npc_id=npc_id, npc_data=req.npc_data)

    # Re-render Jekyll draft
    npc_type = req.npc_data.get("character_type")
    if npc_type in NPC_TYPE_NAMES:
        type_map = {
            "player_character": PlayerCharacter,
            "combat_npc": CombatNpc,
            "roleplay_npc": RoleplayNpc,
        }
        npc_model = type_map[npc_type].model_validate(req.npc_data)
        draft = render_npc_draft(npc=npc_model, title=req.title, slug=req.slug)

        import uuid
        draft_id = uuid.UUID(npc_id) if len(npc_id) == 36 else uuid.uuid5(uuid.NAMESPACE_URL, npc_id)
        write_draft(
            kind="npc",
            campaign=req.campaign,
            slug=req.slug,
            title=req.title,
            yaml_frontmatter=draft.frontmatter_yaml(draft_id=draft_id, campaign=req.campaign),
            markdown_body=draft.markdown_body,
        )

    return ok({
        "npc_id": npc_id,
        "name": req.npc_data.get("identity", {}).get("name", req.title),
        "updated": True,
    })


@router.get("/search", dependencies=[Depends(require_api_key)])
async def search(
    q: str = Query(min_length=1),
    campaign: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Semantic search for NPCs."""
    results = search_npcs(query=q, campaign=campaign, limit=limit)
    return ok(results)
```

**Step 4: Register the router in `app.py`**

Add after the existing router includes:

```python
from llm_api.routes.npc import router as npc_router
# ...
app.include_router(npc_router, prefix="/v1")
```

**Step 5: Run tests**

Run: `cd services/llm_api && python -m pytest tests/test_npc_route.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add services/llm_api/src/llm_api/routes/npc.py services/llm_api/src/llm_api/app.py services/llm_api/tests/test_npc_route.py
git commit -m "feat(api): add NPC GET, PUT, and search endpoints"
```

---

## Task 10: Run full test suite and lint

**Step 1: Run all tests**

Run: `cd services/llm_api && python -m pytest -v`
Expected: All tests PASS

**Step 2: Run linter**

Run: `cd services/llm_api && ruff check src/ tests/`
Expected: No errors (fix any that appear)

**Step 3: Run formatter**

Run: `cd services/llm_api && ruff format --check src/ tests/`
Expected: No formatting issues

**Step 4: Commit any fixes**

```bash
git add -u
git commit -m "chore: lint and format fixes"
```

---

## Task 11: Update dispatch and meta route

Add the new NPC subtypes to the meta endpoint so the chatbot UI can display them.

**Files:**
- Modify: `services/llm_api/src/llm_api/generators/dispatch.py`
- Modify: `services/llm_api/src/llm_api/routes/meta.py` (if it lists supported kinds)

**Step 1: Update dispatch**

The `npc` kind in dispatch already routes to `generate_npc`, which now handles both legacy and structured modes internally via `constraints.npc_type`. No change needed to dispatch itself.

Verify: `cd services/llm_api && python -m pytest tests/ -k dispatch -v`

**Step 2: Update meta endpoint** (if applicable)

Check if `routes/meta.py` exposes `SUPPORTED_KINDS` or generator metadata. If so, add `npc_types` to the response.

**Step 3: Commit**

```bash
git add -u
git commit -m "feat(meta): expose NPC type information in meta endpoint"
```

---

## Summary

| Task | What | New Files | Tests |
|------|------|-----------|-------|
| 1 | Add chromadb dependency | — | — |
| 2 | JSON schemas (3 NPC types) | 3 schema files | — |
| 3 | Pydantic models from schemas | `npc_types.py` | 4 tests |
| 4 | Port dice roller | `dice_roller.py` | 6 tests |
| 5 | Trimmed reference summaries | 4 `.md` files | — |
| 6 | ChromaDB vector store service | `vector_store.py` | 4 tests |
| 7 | NPC renderer (JSON → Jekyll) | `npc_renderer.py` | 5 tests |
| 8 | Evolve NPC generator | modify `npc.py` | 3 new tests |
| 9 | NPC edit/search API routes | `routes/npc.py` | 3 tests |
| 10 | Full test suite + lint | — | — |
| 11 | Update dispatch/meta | — | — |

**Total: ~11 commits, ~25 new tests, backward compatible with existing NPC generation.**
