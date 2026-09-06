# Combat Mechanics Reference

Turn structure and action-economy rulings for running combat smoothly.
For picking/scaling monsters against an XP budget, see the
`encounter-generator` skill's `references/encounter-building.md` instead —
this file covers turn-by-turn mechanics, not encounter design.

## Turn Order

1. Everyone rolls initiative (`d20 + Dex modifier`) at the start of
   combat; ties are broken by the DM's judgment (highest Dex modifier is
   a reasonable default tiebreaker).
2. Turns proceed from highest initiative to lowest, looping each round.
3. On your turn you may take one action, one move (up to your speed,
   which can be split before/after the action), and one bonus action (if
   a feature grants one) — in any order.

## Actions, Bonus Actions, Reactions

- **Action**: Attack, Cast a Spell (most spells), Dash (double effective
  movement this turn), Disengage (movement doesn't provoke opportunity
  attacks this turn), Dodge (attacks against you have disadvantage, you
  have advantage on Dex saves, until your next turn), Help, Hide, Ready
  (prepare an action to trigger on a stated condition, using your
  reaction when it triggers), Search, Use an Object.
- **Bonus action**: Only usable if a specific feature/spell grants one
  (e.g. Two-Weapon Fighting's off-hand attack, a Rogue's Cunning Action).
  You get at most one bonus action per turn, regardless of how many
  features would grant one.
- **Reaction**: One per round (refreshes at the start of your turn),
  usable on another creature's turn when its trigger occurs (most
  commonly an opportunity attack, or a readied action).

## Opportunity Attacks

Triggered when a hostile creature you can see moves out of your reach
(within 5 ft., or your weapon's reach) without using the Disengage
action. You may use your reaction to make one melee attack against it as
it leaves. Teleportation, being forced to move (e.g. shoved), and moves
that don't leave your reach (e.g. moving within your reach) don't
provoke it.

## Multiattack

A "Multiattack" action lets a creature make more than one attack on its
turn as a single action (as opposed to a player character's Extra Attack
feature, which is its own separate class feature). Each attack in a
Multiattack is resolved separately (separate to-hit roll, separate
damage).

## Ranged Attacks in Melee

Making a ranged attack (weapon or spell) while a hostile creature is
within 5 ft. of you imposes disadvantage on the attack roll, unless you
have a feature that says otherwise (e.g. a Fighting Style).

## Mounted Combat

- A rider can control a mount if it's trained for combat, using the
  mount's own movement and actions as normal for a mount (see below);
  an independent (untrained) mount acts on its own initiative and the
  rider can't direct its movement or actions.
- The rider chooses whether attacks target the rider or the mount when
  both are viable targets, unless an attacker specifically targets one.
- If the mount is knocked prone, the rider must succeed on a DC 10 Dex
  save or be dismounted, landing prone in an unoccupied space within 5
  ft.; on a failed save while not dismounted, the rider still falls
  prone with the mount if it doesn't otherwise avoid the fall.
- Mounting or dismounting costs movement equal to half your speed, and
  can't be done if you have no movement left.
