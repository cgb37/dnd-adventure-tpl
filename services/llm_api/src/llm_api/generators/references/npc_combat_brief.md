<!-- Trimmed from ai/skills/rpg-character-gen/references/ for LLM prompt embedding -->

# Combat NPC Reference — Brief

## CR / HP / AC Guidelines

| CR | Prof | Approx AC | Approx HP | Attack Bonus | Damage/Round |
|---:|-----:|----------:|----------:|-------------:|-------------:|
| 0 | +2 | 10–12 | 1–6 | +2–3 | 0–1 |
| 1/8 | +2 | 12–13 | 7–12 | +3 | 2–5 |
| 1/4 | +2 | 13 | 13–20 | +3–4 | 4–6 |
| 1/2 | +2 | 13 | 20–35 | +3–4 | 6–8 |
| 1 | +2 | 13–14 | 36–49 | +3–5 | 9–14 |
| 2 | +2 | 13–14 | 50–70 | +3–5 | 15–20 |
| 3 | +2 | 13–15 | 71–85 | +4–6 | 21–26 |
| 5 | +3 | 15–17 | 101–115 | +6–8 | 33–38 |
| 8 | +3 | 16–17 | 146–160 | +7–9 | 51–56 |
| 12 | +4 | 17–18 | 206–220 | +8–10 | 69–74 |

## Common SRD Stat Block Archetypes

| NPC | CR | HP | AC | Notable |
|-----|---:|---:|---:|---------|
| Commoner | 0 | 4 | 10 | All 10s |
| Bandit | 1/8 | 11 | 12 | Scimitar, crossbow |
| Guard | 1/8 | 11 | 16 | Chain + shield |
| Scout | 1/2 | 16 | 13 | Keen Senses, Multiattack |
| Spy | 1 | 27 | 12 | Sneak Attack 2d6, Cunning Action |
| Bandit Captain | 2 | 65 | 15 | Multiattack ×3, Parry |
| Veteran | 3 | 58 | 17 | Multiattack ×2 |
| Gladiator | 5 | 112 | 16 | Multiattack ×3, Brute |
| Mage | 6 | 40 | 12 | 9th-level wizard spells |
| Assassin | 8 | 78 | 15 | Assassinate, Sneak Attack 4d6 |
| Archmage | 12 | 99 | 12 | Magic Resistance, 18th-level wizard |

## Output Structure (combat_npc JSON)
Required: `character_type`, `identity` (name, creature_type, role), `challenge` (rating, xp), `combat` (armor_class, hit_points, speed), `ability_scores` (str/dex/con/int/wis/cha), `actions` (name, description).
Optional: `defenses`, `senses`, `languages`, `traits`, `reactions`, `spellcasting`, `tactical_notes`.
