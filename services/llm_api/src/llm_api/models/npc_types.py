"""Pydantic models for the three NPC types.

Generated from the JSON schemas in ``generators/schemas/`` and hand-tuned.
Each model uses a ``Literal`` character_type so they can be discriminated
in a tagged union.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


# ── Shared ──────────────────────────────────────────────────────────────────


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


# ── Player Character ─────────────────────────────────────────────────────────


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


# ── Combat NPC ───────────────────────────────────────────────────────────────


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


# ── Roleplay NPC ─────────────────────────────────────────────────────────────


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


# ── Discriminated union ──────────────────────────────────────────────────────

NpcUnion = Annotated[
    Union[PlayerCharacter, CombatNpc, RoleplayNpc],
    Field(discriminator="character_type"),
]

NPC_TYPE_NAMES: tuple[str, ...] = ("player_character", "combat_npc", "roleplay_npc")
