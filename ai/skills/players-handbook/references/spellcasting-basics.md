# Spellcasting Basics Reference

Quick rulings for "can I cast this" and "how does this spell mechanic
work" questions from the player's seat. If a question isn't covered
here (e.g. what a specific spell does), fall back to
`dnd5eapi_client.py` (see SKILL.md) to look up that spell.

## Spell Slots

Casting a leveled spell (not a cantrip) uses one spell slot of that
spell's level or higher — casting it using a higher-level slot generally
makes the spell more powerful ("upcasting"), per that spell's own
description. Cantrips (level 0 spells) never use a slot and can be cast
at will. Spell slots are expended when you cast the spell, and are
regained on a long rest (some class features regain some slots on a
short rest instead — check your class features).

## Casting Time

- **1 action**: the most common casting time — uses your action for the
  turn, same as any other action.
- **1 bonus action**: uses your bonus action instead, leaving your
  action free for something else (e.g. an attack, if a feature allows
  it).
- **1 reaction**: cast in response to a trigger the spell specifies
  (e.g. Shield), using your reaction for the round.
- **Longer casting times** (e.g. 1 minute, 10 minutes): you must spend
  the entire time casting, generally in a safe/uninterrupted setting,
  or the casting fails and the slot is wasted.

You can only cast one spell with a casting time other than a reaction
per turn — with one exception: if you cast a spell using a bonus
action, you can still cast a cantrip with a casting time of 1 action
that same turn (but not another leveled spell). Outside that exception,
casting a second "1 action" or "1 bonus action" spell in the same turn
isn't allowed.

## Components

A spell's description lists which of these it needs; missing a required
component (without a substitute like a spellcasting focus, where
allowed) means you can't cast it:

- **V (Verbal)**: you must be able to speak. Being silenced blocks this.
- **S (Somatic)**: you need a free hand to gesture. Both hands full
  (e.g. a two-handed weapon and no spellcasting focus) blocks this.
- **M (Material)**: you need the specified material(s), consumed if the
  spell says so — otherwise a spellcasting focus or component pouch
  substitutes for any material component that has no listed cost and
  isn't consumed.

## Concentration

Spells marked "Concentration" require you to actively concentrate to
keep their effect running:

- You can only concentrate on one such spell at a time — casting a
  second concentration spell ends the first one immediately.
- Taking damage while concentrating forces a Constitution saving throw
  (DC 10, or half the damage taken if higher) to maintain it.
- Being incapacitated, or reduced to 0 HP, ends concentration
  automatically.
- Concentration also ends if you willingly stop it, or (per most such
  spells) if you're no longer able to see/reach the target/area as the
  spell requires.

## Ritual Casting

A spell tagged "Ritual" can be cast without expending a spell slot by
taking 10 extra minutes beyond its normal casting time — but only if you
have that spell prepared/known specifically as available for ritual
casting (check your class's ritual-casting rules) and it's actually
tagged as a ritual spell.

## Spell Attack Rolls & Save DCs

- **Spell attack roll**: `d20 + spellcasting ability modifier +
  proficiency bonus`, compared against the target's AC, same as a
  weapon attack roll.
- **Spell save DC**: `8 + spellcasting ability modifier + proficiency
  bonus` — the target rolls against this DC for any saving throw the
  spell calls for.

## Known vs. Prepared Casters

- **Known casters** (e.g. Sorcerer, Bard, Warlock) can cast any spell
  on their fixed "known spells" list without changing it between casts.
- **Prepared casters** (e.g. Cleric, Druid, Wizard) choose a subset of
  their available spells to have "prepared" — usually re-chosen after a
  long rest — and can only cast spells currently prepared (cantrips are
  always available regardless of preparation).
