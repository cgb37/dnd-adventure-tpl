# SRD NPC Stat Block Reference

Use this reference when generating combat-ready NPCs. These are the standard NPC stat blocks from the 5e SRD, organized by Challenge Rating.

## NPC Stat Blocks by CR

| NPC | CR | HP | AC | Key Abilities |
|-----|---:|---:|---:|---------------|
| Commoner | 0 | 4 (1d8) | 10 | All 10s |
| Acolyte | 1/4 | 9 (2d8) | 10 | Wis 14; 1st-level cleric spells |
| Bandit | 1/8 | 11 (2d8+2) | 12 | Scimitar, light crossbow |
| Cultist | 1/8 | 9 (2d8) | 12 | Dark Devotion |
| Guard | 1/8 | 11 (2d8+2) | 16 | Chain shirt + shield |
| Noble | 1/8 | 9 (2d8) | 15 | Breastplate; Parry reaction |
| Tribal Warrior | 1/8 | 11 (2d8+2) | 12 | Pack Tactics |
| Bandit Captain | 2 | 65 (10d8+20) | 15 | Multiattack (3), Parry |
| Berserker | 2 | 67 (9d8+27) | 13 | Reckless |
| Cult Fanatic | 2 | 33 (6d8+6) | 13 | Dark Devotion; 3rd-level cleric spells |
| Druid | 2 | 27 (5d8+5) | 11 | 4th-level spellcaster; Wild Shape |
| Priest | 2 | 27 (5d8+5) | 13 | 5th-level cleric spells |
| Scout | 1/2 | 16 (3d8+3) | 13 | Keen Hearing/Sight; Multiattack |
| Spy | 1 | 27 (6d8) | 12 | Sneak Attack 2d6; Cunning Action |
| Thug | 1/2 | 32 (5d8+10) | 11 | Pack Tactics; Multiattack |
| Veteran | 3 | 58 (9d8+18) | 17 | Multiattack (longsword ×2 + shortsword) |
| Knight | 3 | 52 (8d8+16) | 18 | Brave, Leadership; Parry |
| Mage | 6 | 40 (9d8) | 12 | 9th-level wizard spells |
| Gladiator | 5 | 112 (15d8+45) | 16 | Multiattack (3), Brave, Brute; Parry + Shield Bash |
| Assassin | 8 | 78 (12d8+24) | 15 | Assassinate, Evasion, Sneak Attack 4d6; poison |
| Archmage | 12 | 99 (18d8+18) | 12/15 | 18th-level wizard; Magic Resistance |

## Stat Block Template (JSON format)

When generating an NPC stat block, use this structure:

```json
{
  "name": "NPC Name",
  "type": "Medium humanoid (race), alignment",
  "challenge_rating": "CR value",
  "xp": 0,
  "armor_class": { "value": 10, "source": "armor type" },
  "hit_points": { "value": 0, "formula": "XdY + Z" },
  "speed": "30 ft.",
  "ability_scores": {
    "str": 10, "dex": 10, "con": 10,
    "int": 10, "wis": 10, "cha": 10
  },
  "saving_throws": [],
  "skills": [],
  "damage_resistances": [],
  "damage_immunities": [],
  "condition_immunities": [],
  "senses": "passive Perception 10",
  "languages": "Common",
  "traits": [
    { "name": "Trait Name", "description": "Trait effect" }
  ],
  "actions": [
    {
      "name": "Attack Name",
      "type": "melee_weapon | ranged_weapon | spell",
      "attack_bonus": 0,
      "reach_range": "5 ft.",
      "damage": "XdY + Z",
      "damage_type": "slashing"
    }
  ],
  "reactions": [],
  "spellcasting": null
}
```

## CR Estimation Guidelines

| CR | Prof Bonus | Approx AC | Approx HP | Approx Attack | Approx Damage/Round |
|---:|----------:|----------:|----------:|--------------:|--------------------:|
| 0 | +2 | 10-12 | 1-6 | +2-3 | 0-1 |
| 1/8 | +2 | 12-13 | 7-12 | +3 | 2-5 |
| 1/4 | +2 | 13 | 13-20 | +3-4 | 4-6 |
| 1/2 | +2 | 13 | 20-35 | +3-4 | 6-8 |
| 1 | +2 | 13-14 | 36-49 | +3-5 | 9-14 |
| 2 | +2 | 13-14 | 50-70 | +3-5 | 15-20 |
| 3 | +2 | 13-15 | 71-85 | +4-6 | 21-26 |
| 5 | +3 | 15-17 | 101-115 | +6-8 | 33-38 |
| 8 | +3 | 16-17 | 146-160 | +7-9 | 51-56 |
| 12 | +4 | 17-18 | 206-220 | +8-10 | 69-74 |
| 17 | +6 | 19-20 | 281-310 | +10-12 | 93-98 |
| 20 | +6 | 19-21 | 341-400 | +10-13 | 111-116 |

## Customization Options

- **Racial Traits**: Add race features without changing CR
- **Spell Swaps**: Replace spells with same-level alternatives (same CR)
- **Armor/Weapon Swaps**: May change CR if AC or damage shift significantly
- **Magic Items**: Powerful damage items can raise effective CR
