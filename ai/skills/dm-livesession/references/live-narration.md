# Live Narration Guidance

Judgement guidance for narrating a player-mode scene turn-by-turn, the way
`references/outline-building.md` grounds `dm-orchestrator`'s outline
design. Used only in Workflow 1 (Player Session) - the DM co-pilot
workflow narrates nothing; it answers queries directly.

## The one rule everything else serves

Never narrate, hint at, or answer a question about anything beyond
`session.yml`'s `current_position`. Not a future scene's title, not its
premise, not which NPCs appear in it, not how many scenes remain in the
chapter. If a player asks something that would require peeking ahead
("are we near the end of this chapter?"), answer only in terms of what
they've already experienced ("you don't know yet - you'll find out as you
go"), never with real numbers from the outline.

## Turning generated content into narration

The current beat's generated draft(s) (location/encounter/monster/magic,
per its `needs`) are structured reference material, not narration text.
Read them for facts - what's in the room, what the creature's stat block
implies about how it fights, what the item does - then narrate in second
person, present tense, as a DM speaking to a player: sensory detail first,
mechanical facts folded in only as the fiction reveals them (a monster's
resistance is discovered through a blow that does less than expected, not
announced as a stat line).

## Story hooks

A hook is planted, not delivered as a summary. If a scene's `needs`
included content whose thread ties to something in `campaign.yml`'s
`threads`, surface it through action or dialogue the player can choose to
pursue or ignore - a nervous glance, a half-finished sentence, an object
that doesn't belong. Never say "this seems important" out loud; let the
detail's placement do that work.

## Puzzles

Give the puzzle's shape and its stakes up front, then let solutions come
from the player's stated actions - never solve it for them, and never
reject a creative approach the puzzle's premise doesn't actually rule out.
When a player is stuck, escalate hints gradually across turns (a stronger
sensory detail, then an NPC's suggestion, then a direct clue) rather than
either stonewalling or handing over the answer on the first ask.

## NPC agendas and unreliable narration

`campaign.yml`'s `npcs` entries carry only `role` and `disposition` -
there is no persisted `agenda` field, deliberately (see the design spec).
Infer an NPC's motive live, each time they appear, from those two fields
plus the current scene's premise, and stay consistent with what you
inferred earlier in the same session (check `session.yml`'s `event_log`
for how this NPC was already played before contradicting yourself).

An NPC can be an unreliable narrator - stating something false or
incomplete because of their own agenda, not because you're hiding
information from the player. The player should always be able to tell
*that* an NPC said something (verifiable, actionable), even when *what*
they said turns out to be wrong. Never have the narration itself (as
opposed to a character within it) state something false - the fourth wall
between "the DM's factual description" and "what this liar just claimed"
must stay intact.

## Off-script play

When a player does something the outline didn't anticipate, improvise the
immediate consequence using the same principles above (hooks, NPC
consistency, no future-beat leakage) - the outline being silent on this
exact action is not license to describe something that spoils a later
beat instead. Do not tell the player they've gone "off script." Resolve
the moment in-world and let the story continue; `SKILL.md` handles when
(and whether) `session.yml` advances as a result.
