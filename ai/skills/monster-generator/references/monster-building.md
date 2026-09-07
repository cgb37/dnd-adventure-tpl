# Monster Building Reference

Guidance for turning `scripts/monster_statblock.py`'s CR guidance into a
full stat block.

## Using the CR Guidance

`monster_statblock.py --cr <cr>` returns ranges for AC, HP, attack bonus,
and damage per round, plus the CR's proficiency bonus. These are the same
ranges as `../../rpg-character-gen/references/npc-stat-blocks.md`'s "CR
Estimation Guidelines" table:

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

Pick a value inside the range, not just the midpoint every time — low-AC,
high-HP "bruiser" and high-AC, low-HP "skirmisher" builds at the same CR
should feel different.

## Ability Scores

Pick six ability scores that fit the monster's concept (a golem needs high
STR/CON and near-zero DEX/CHA; a specter needs the reverse), then run each
through `monster_statblock.py --score <score>` for its modifier — never
hand-compute `(score - 10) // 2`.

## Type, Size, and Special Abilities by CR Band

- **CR 0-2**: mundane or lightly magical creatures. 0-1 special abilities,
  no spellcasting, no legendary actions.
- **CR 3-8**: distinct tactical identity — 1-2 special abilities (a
  recharge breath weapon, a fear aura, resistance/immunity to a damage
  type), spellcasting only for concept-appropriate creatures (a hag, not a
  wolf).
- **CR 9-16**: multiple special abilities, spellcasting common for
  intelligent creatures, reactions (parry, redirect) start appearing.
- **CR 17+**: legendary-tier — multiple special abilities plus
  spellcasting or a signature multi-part action are expected, not
  optional, to justify the CR against a full-strength high-level party.

## Actions and Damage

- Give at least one action whose `damage` list has more than one entry
  (e.g. piercing + poison) once CR reaches 2+ — a single flat damage type
  reads as a placeholder monster.
- `hit_bonus` should track the CR's attack-bonus range from the table
  above, not the raw ability modifier alone (assume proficiency is
  already factored in).
- Total expected damage per round across all actions (assuming all hit)
  should land inside `damage_per_round_range` for the CR.

## Treasure and Notes

`treasure` and `notes` are optional — include them only when the
narrative context calls for guarding something specific, otherwise omit
both keys rather than writing "none."
