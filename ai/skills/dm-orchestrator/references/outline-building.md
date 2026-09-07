# Outline Building Guidance

Guidance for turning a premise + scope into a chapter/episode/scene outline.
This is judgement, not arithmetic — use it the way `encounter-building.md`
is used for encounter design: as grounding, not a rigid formula.

## Sizing from scope

Map the user's stated scope to a structure. As a starting point:

| Scope phrase | Chapters | Episodes/chapter | Scenes/episode |
|---|---|---|---|
| "short" / "one-shot" | 1 | 1-2 | 2-3 |
| "3 chapters, short" | 3 | 2 | 2-3 |
| "a full campaign" / unspecified length | 4-6 | 2-3 | 3-4 |

These are starting points, not caps — adjust for how much the premise
itself implies (a premise naming three distinct locations probably wants
at least three episodes to visit them).

## Pacing

- **Plant early, pay off late.** Every thread in `threads` should be
  introduced in the first third of the outline and either advance or
  resolve by the final chapter. An outline with threads that never move is
  a worse outline than a shorter one where every thread matters.
- **Escalate.** Later chapters should raise stakes relative to earlier
  ones — a bigger threat, a more personal cost, a harder choice. Don't
  repeat the same shape of scene (e.g. "another ambush") without variation
  in tone or consequence.
- **Vary `needs`.** Don't tag every scene `[encounter]`. A good outline
  mixes exploration/investigation scenes (`[location]`), combat
  (`[encounter]`), reward moments (`[magic]`), and monster-forward scenes
  where a specific creature drives the plot (`[monster]`). A scene can need
  more than one — e.g. `[location, encounter]` for a fight that happens in
  a place worth describing in its own right.

## Tagging `needs` from a premise

Infer tags from what the scene's one-line premise actually implies:

- Combat, ambush, "fight," "guarded by," "attacks" → `encounter`
- A place to explore, arrive at, or describe (a room, ruin, town, road) →
  `location`
- A specific named or important creature drives the scene (a boss, a
  unique monster, a CR-notable threat introduced by name) → `monster`
- A reward, artifact, or magic item is found or given → `magic`

A scene with no clear generator need (a pure roleplay/dialogue beat, e.g.
"the party negotiates with the mayor") can have `needs: []` — not every
scene requires generated content.

**Write such a scene with `status: filled` from the start**, not
`status: planned`. There is nothing for the fill workflow to generate, so
nothing will ever flip it out of `planned`; leaving it `planned` would park
"fill in the next part" on a scene that can never complete, and the
campaign could never advance past it.

## Level appropriateness

Read the resolved party level (from `party_state.py`) before designing the
outline. Scenes tagged `encounter` or `monster` should assume a party at
roughly that level for the first chapter, escalating by no more than 2-3
levels by the outline's final chapter, consistent with the CR/level
judgement already used by `encounter-generator` and `monster-generator`.
Don't hand off a level-1-appropriate premise to a level-12 party's outline
without acknowledging the mismatch.
