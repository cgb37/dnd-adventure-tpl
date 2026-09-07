# Location Building Reference

Guidance for scaling challenge severity and tying a location to the active
campaign's story.

## Scaling Challenges to Party Level

Traps, hazards, and puzzle DCs should track roughly with the party's
level, the same way `encounter-generator`'s XP budget tracks with level.
Use these bands as a starting point — judgment calls, not a DMG table:

| Party Level | Trap/Hazard DC | Trap/Hazard Damage | Puzzle Difficulty |
|---|---|---|---|
| 1-4 | 10-13 | 1d6-2d6 | Straightforward, 1-2 steps |
| 5-10 | 13-16 | 2d6-4d10 | Multi-step, may need a specific skill or spell |
| 11-16 | 16-19 | 4d10-6d10 | Requires piecing together clues from multiple sources |
| 17-20 | 19-22 | 6d10-10d10 | Layered, may require a specific combination of actions |

Ambushes should reference
`../../encounter-generator/references/encounter-building.md`'s monster-role
and CR guidance if the ambush is meant to be run as a real combat
encounter, rather than inventing separate monster balance rules here.

## Structuring Challenges

Each `challenges` category (`traps`, `ambushes`, `puzzles`, `hazards`) is a
list of one-line entries, each `Name: what happens and how to
resist/avoid it (DC, damage, or skill check where relevant)`. Two or three
entries per populated category is enough — don't pad. Skip a category
entirely if nothing in this location warrants it (not every location
needs a puzzle).

## Tying the Location to the Story

- Ground `secrets` and `plot_hooks` in whatever campaign context the user
  already gave — a faction, an NPC, an ongoing plot thread. A secret that
  doesn't connect to anything is a dead end for the DM.
- `npcs` should be characters the party can actually meet here, not a
  worldbuilding aside — give each one a reason to be present and a reason
  to matter to the plot hooks above.
- `environmental_features` should describe things the party can use,
  trigger, or be affected by (cover, an updraft, unstable footing, a
  resource to loot) rather than pure scenery.
- `additional_notes` is where you tell the DM how to adapt this location
  on the fly — what to change if the party goes off-script, what to leave
  vague on purpose.
