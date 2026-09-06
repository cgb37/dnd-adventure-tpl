# Encounter Building Reference

Guidance for spending the XP budget from `scripts/encounter_budget.py` on an
actual, story-appropriate encounter.

## Using the Budget

`encounter_budget.py` gives you `total_xp_budget` (the raw XP threshold for
the requested difficulty) and `cr_to_xp` (XP value per monster by challenge
rating). Multiple monsters fight harder together than their raw XP suggests,
so apply this multiplier to the *sum* of selected monsters' XP before
comparing it against `total_xp_budget`:

| Number of monsters | Multiplier |
|---|---|
| 1 | x1 |
| 2 | x1.5 |
| 3-6 | x2 |
| 7-10 | x2.5 |
| 11-14 | x3 |
| 15+ | x4 |

Example: budget is 2000 XP. Four CR-2 monsters (450 XP each = 1800 XP raw)
at the "3-6 monsters" tier (x2) have an effective XP of 3600 — too hard.
Two CR-2 monsters (900 XP raw, x1.5 = 1350 effective) fits comfortably
under budget with room for a third weaker monster or an environmental
hazard.

If the party is smaller than 3 or larger than 5, shift the effective
multiplier one tier easier (small party) or harder (large party) than the
table above suggests — this compensates for action economy swinging more or
less in the party's favor.

## Selecting Monsters

1. Prefer named monsters from `../../rpg-character-gen/references/npc-stat-blocks.md`'s
   CR table when one fits the story.
2. When nothing fits, invent a creature: use that same reference's
   "CR Estimation Guidelines" table to keep HP/AC/attack/damage plausible
   for the target CR, and use `cr_to_xp` (from `encounter_budget.py`'s
   output) for its XP cost.
3. Reskinning (renaming, changing damage type, swapping a weapon for
   claws) doesn't change CR. Meaningfully changing AC or damage output
   does — recheck against the CR Estimation Guidelines table if you do.

## Monster Roles

Give each monster (or group) a tactical role so the fight reads as
designed, not random:

- **Brute** — high HP/damage, low tactics. Anchors the fight.
- **Skirmisher** — mobile, hit-and-run, forces the party to spread out.
- **Controller** — battlefield control (restraints, area denial, terrain
  manipulation), makes positioning matter.
- **Artillery** — high damage at range, low HP, a priority target.
- **Support** — buffs/heals other monsters, a secondary priority target.

A good encounter usually mixes 2-3 roles rather than N copies of one
monster.

## Fitting the Story

- Ground the setting and the "why" of this fight in whatever context the
  user gave you — a random encounter reads worse than one tied to the
  location, faction, or plot thread already in play.
- Give the environment at least one feature that matters tactically
  (cover, difficult terrain, a hazard, something breakable) rather than a
  flat empty room.
- Tactical notes should describe how the fight actually plays out —
  when weaker monsters flee, when a controller uses its signature ability,
  what changes if the party splits up — not just a list of stats.
