---
name: rpg-character-gen
description: Generate D&D 5e player characters, combat NPCs, and roleplay NPCs as structured JSON for campaign software. Use this skill whenever someone asks to create, build, or generate a character, NPC, stat block, party member, villain, shopkeeper, quest giver, or any other persona for a tabletop RPG — even if they don't say "D&D" or "5e" explicitly. Also trigger when someone asks for a random encounter NPC, a villain with stats, a quick tavern patron, or needs to populate a town or dungeon with people. If the request involves any kind of RPG character or NPC creation, this is the skill to use.
---

# RPG Character & NPC Generator

Generate player characters and NPCs for D&D 5e (2014 SRD rules) as structured JSON, ready for import into campaign software.

## What This Skill Produces

Three types of output, depending on what's requested:

1. **Player Characters** — Full character sheets with ability scores, class features, equipment, spells, and personality
2. **Combat NPCs** — Stat blocks with CR, actions, and tactical notes for encounters
3. **Roleplay NPCs** — Personality-driven characters with motivations, speech patterns, secrets, and plot hooks

All output is **nested JSON** designed for software consumption. Each output type has its own schema (see Output Schemas below).

## Workflow

### Step 1: Determine What's Needed

Ask the user (if not already clear):
- **Type**: Player character, combat NPC, or roleplay NPC?
- **Level/CR**: What level (PCs) or challenge rating (NPCs)?
- **Constraints**: Any specific race, class, theme, or role in the story?
- **Quantity**: One character or a batch?

If the user gives a vague request like "make me a rogue," assume a level 1 player character and fill in reasonable defaults. Better to produce something useful quickly than ask too many questions.

### Step 2: Generate Ability Scores

For player characters, use the bundled dice roller script:

```bash
# Roll 4d6 drop lowest (default — the fun way)
python <skill-path>/scripts/dice_roller.py roll

# Standard Array (consistent and balanced)
python <skill-path>/scripts/dice_roller.py standard

# Point Buy (for optimizers)
python <skill-path>/scripts/dice_roller.py pointbuy --scores 15 14 13 12 10 8
```

The script outputs JSON with scores, modifiers, and totals. Use the `--seed` flag if the user wants reproducible results.

Default to **rolling** unless the user specifies otherwise — it's more exciting and fits the spirit of D&D. If the user asked for a dice roll approach, always use the roll method.

For NPCs, don't use the roller. Assign ability scores directly based on the NPC's role and the reference stat blocks.

### Step 3: Build the Character

Consult the reference files based on what you're building:

| Building... | Read this reference |
|-------------|-------------------|
| Any PC | `references/races-summary.md` and `references/classes-summary.md` |
| Combat NPC | `references/npc-stat-blocks.md` |
| Roleplay NPC | `references/npc-roleplay.md` |
| Combat + Roleplay NPC | Both NPC references |

These references contain condensed SRD data — race traits, class features by level, NPC stat block templates, CR guidelines, personality frameworks, and speech patterns.

#### For Player Characters

1. **Race**: Apply racial ASIs and traits from races-summary.md
2. **Class**: Look up hit die, proficiencies, saving throws, and features for the character's level from classes-summary.md
3. **Ability Scores**: Assign the rolled/chosen scores to abilities. Place the highest score in the class's primary ability (see the class table). Apply racial ASIs on top.
4. **HP**: Level 1 = hit die max + Con modifier. Higher levels = add (average roll + Con mod) per level.
5. **AC**: Calculate from armor + Dex modifier (or class features like Unarmored Defense)
6. **Skills**: Choose from the class skill list (number varies by class)
7. **Equipment**: Assign starting equipment based on class
8. **Spells**: If a caster, select appropriate cantrips and prepared/known spells for the character's level
9. **Background**: Choose a fitting background with 2 skill proficiencies, languages, and equipment
10. **Personality**: Add personality traits, ideals, bonds, and flaws

#### For Combat NPCs

1. Pick a base stat block from npc-stat-blocks.md that matches the desired CR
2. Customize: swap armor, weapons, spells, or add racial traits
3. Recalculate CR if AC or damage changed significantly (use the CR estimation table)
4. Add a brief description and tactical notes

#### For Roleplay NPCs

1. Follow the 5-element personality framework in npc-roleplay.md: Motivation, Personality Traits, Physical Feature, Secret, Relationship to Party
2. Choose a complexity tier matching narrative importance (Background, Recurring, or Major)
3. Give them a distinct speech pattern
4. For Major NPCs, also generate a combat stat block

### Step 4: Output as JSON

Use the appropriate schema below. Save the JSON to a file if the user requests it, or output it directly.

## Output Schemas

### Player Character

```json
{
  "character_type": "player_character",
  "identity": {
    "name": "Character Name",
    "race": "Race",
    "subrace": "Subrace or null",
    "class": "Class",
    "subclass": "Subclass or null",
    "level": 1,
    "background": "Background Name",
    "alignment": "Neutral Good",
    "xp": 0
  },
  "ability_scores": {
    "method": "roll | standard_array | point_buy",
    "base_scores": { "str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0 },
    "racial_bonuses": { "str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0 },
    "final_scores": { "str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0 },
    "modifiers": { "str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0 }
  },
  "combat": {
    "armor_class": { "value": 0, "source": "armor type" },
    "hit_points": { "max": 0, "formula": "description of calculation" },
    "hit_dice": { "total": "1d8", "remaining": "1d8" },
    "speed": "30 ft.",
    "initiative": 0,
    "proficiency_bonus": 2
  },
  "proficiencies": {
    "armor": [],
    "weapons": [],
    "tools": [],
    "saving_throws": [],
    "skills": [],
    "languages": []
  },
  "features": [
    { "name": "Feature Name", "source": "Race/Class/Background", "description": "What it does" }
  ],
  "equipment": [
    { "name": "Item", "quantity": 1, "properties": [] }
  ],
  "spellcasting": {
    "ability": "Wisdom",
    "spell_save_dc": 0,
    "spell_attack_bonus": 0,
    "cantrips": [],
    "spell_slots": { "1st": 0, "2nd": 0 },
    "prepared_spells": []
  },
  "personality": {
    "traits": ["Personality trait"],
    "ideals": ["Ideal"],
    "bonds": ["Bond"],
    "flaws": ["Flaw"],
    "backstory_hook": "Brief backstory seed"
  }
}
```

### Combat NPC

```json
{
  "character_type": "combat_npc",
  "identity": {
    "name": "NPC Name",
    "creature_type": "Medium humanoid (race), alignment",
    "role": "What role this NPC plays in the encounter"
  },
  "challenge": {
    "rating": "CR value",
    "xp": 0
  },
  "combat": {
    "armor_class": { "value": 0, "source": "armor type" },
    "hit_points": { "value": 0, "formula": "XdY + Z" },
    "speed": "30 ft."
  },
  "ability_scores": {
    "str": 10, "dex": 10, "con": 10,
    "int": 10, "wis": 10, "cha": 10
  },
  "defenses": {
    "saving_throws": [],
    "skills": [],
    "damage_resistances": [],
    "damage_immunities": [],
    "condition_immunities": []
  },
  "senses": "passive Perception 10",
  "languages": "Common",
  "traits": [
    { "name": "Trait", "description": "Effect" }
  ],
  "actions": [
    {
      "name": "Attack Name",
      "description": "Full attack description with to-hit, reach, damage"
    }
  ],
  "reactions": [],
  "spellcasting": null,
  "tactical_notes": "How this NPC fights and what makes the encounter interesting"
}
```

### Roleplay NPC

```json
{
  "character_type": "roleplay_npc",
  "identity": {
    "name": "NPC Name",
    "race": "Race",
    "occupation": "What they do",
    "location": "Where they're found",
    "complexity_tier": "background | recurring | major"
  },
  "personality": {
    "motivation_primary": "What drives them most",
    "motivation_secondary": "Secondary want or need",
    "traits": ["2-3 personality traits"],
    "speech_pattern": "Description of how they talk, with example dialogue",
    "quirk": "Memorable behavioral quirk"
  },
  "appearance": {
    "distinguishing_feature": "The one thing players will remember",
    "brief_description": "2-3 sentence physical description"
  },
  "secrets": [
    { "secret": "Hidden information", "discovery_method": "How players might learn this" }
  ],
  "relationships": {
    "party_role": "quest_giver | ally | obstacle | information_source | comic_relief | moral_challenge",
    "connections": [
      { "name": "Other NPC", "relationship": "How they're connected" }
    ]
  },
  "plot_hooks": [
    "Potential adventure hook involving this NPC"
  ],
  "stat_block": null
}
```

For **Major roleplay NPCs**, populate the `stat_block` field with a combat NPC object so the NPC can serve double duty.

## Generating Batches

When asked to create multiple characters (e.g., "populate this tavern" or "make a party of 4"):

1. Generate each character individually following the full workflow
2. Ensure variety — don't repeat races, classes, or personality types within a batch unless it makes narrative sense
3. Output as a JSON array
4. For town/location populations, mix complexity tiers: mostly background NPCs, a few recurring, maybe one major

## Tips for Good Output

- **Mechanical accuracy matters.** Double-check HP calculations, spell slot counts, and proficiency bonuses against the reference tables. Campaign software will display these numbers directly to players, so errors break immersion and trust.
- **Personality should be specific, not generic.** "Brave and kind" tells a DM nothing. "Laughs too loud at her own jokes and once punched a duke for insulting her horse" gives them something to work with at the table.
- **Ability score assignment should make sense.** A wizard's highest score goes in Intelligence. A barbarian's goes in Strength. Don't get creative with primary stats — save the creativity for personality and backstory.
- **Name characters thoughtfully.** Match names to the character's race and setting. A dwarf named "Thistlewick Sparkleberry" breaks tone unless the campaign is comedic.
