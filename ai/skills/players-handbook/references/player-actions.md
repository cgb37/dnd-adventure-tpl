# Player Actions Reference

Quick rulings for "what can I do on my turn" and "does this give me
advantage" questions from the player's seat — not a full rules reprint.
If a question isn't covered here, fall back to `dnd5eapi_client.py` (see
SKILL.md).

## Your Turn

On your turn you get one action, one move (up to your speed, which you
can split before/after your action), and one bonus action (only if a
feature or spell grants one) — in any order you like.

## Actions You Can Take

- **Attack** — make a melee or ranged attack.
- **Cast a Spell** — most spells with a casting time of "1 action."
- **Dash** — gain extra movement equal to your speed this turn.
- **Disengage** — your movement this turn doesn't provoke opportunity
  attacks.
- **Dodge** — until the start of your next turn, any attack roll against
  you has disadvantage if you can see the attacker, and you have
  advantage on Dexterity saving throws.
- **Help** — help another creature's ability check (they get advantage
  on their next check for that task) or help an ally's attack roll
  against a creature within 5 ft. of you (their next attack against that
  target has advantage), provided you're actually capable of assisting.
- **Hide** — make a Dexterity (Stealth) check to try to hide.
- **Ready** — pick a trigger and an action/movement to take when it
  happens; using it later takes your reaction.
- **Search** — make a Wisdom (Perception) or Intelligence
  (Investigation) check to find something.
- **Use an Object** — interact with a second object this turn beyond the
  one free interaction you already get (e.g. drawing a weapon,
  drinking a potion).

## Bonus Actions

You only have a bonus action if a specific class feature, spell, or
other effect grants one (e.g. a Rogue's Cunning Action, Two-Weapon
Fighting's off-hand attack, a spell that says "1 bonus action"). You get
at most one bonus action per turn no matter how many features would
grant one — pick which one to use.

## Reactions

You get one reaction per round, which refreshes at the start of your own
turn. You spend it on another creature's turn when its trigger occurs —
most commonly an opportunity attack (see below), or an action you
readied on your own prior turn.

## Opportunity Attacks

If a hostile creature you can see moves out of your reach (within 5 ft.,
or your weapon's reach) without using the Disengage action, you can use
your reaction to make one melee attack against it as it leaves. You
don't get one if the creature teleports, is forced to move (e.g.
shoved), or moves in a way that never leaves your reach.

## Ability Checks & Skills

A check succeeds if `d20 + ability modifier + proficiency bonus (if
you're proficient in the relevant skill) >= DC`. Your DM sets the DC;
typical DCs run from 5 (very easy) to 30 (nearly impossible), with 15 a
common "moderately hard" target.

## Advantage & Disadvantage

- Roll two d20s: take the higher for advantage, the lower for
  disadvantage.
- They never stack — any number of advantage sources plus any number of
  disadvantage sources still cancels down to a single net advantage,
  disadvantage, or (if they fully cancel) a flat roll.
- Ways you can gain advantage: an ally helps you, you attack a prone
  target in melee, you attack a target that can't see you.
- Ways you can end up with disadvantage: attacking a prone target at
  range, attacking while restrained or prone yourself, making a ranged
  attack while a hostile creature is within 5 ft. of you (unless a
  feature says otherwise), attacking at long range with a ranged weapon.
