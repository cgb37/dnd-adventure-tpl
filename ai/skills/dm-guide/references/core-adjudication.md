# Core Adjudication Reference

Quick rulings for the "how do I call this" moments that come up constantly
at the table — not a full rules reprint. If a question isn't covered here,
fall back to the SRD API client (see SKILL.md).

## Ability Checks & DCs

| DC | Difficulty  |
|----|-------------|
| 5  | Very easy   |
| 10 | Easy        |
| 15 | Medium      |
| 20 | Hard        |
| 25 | Very hard   |
| 30 | Nearly impossible |

A check succeeds if `d20 + ability modifier + proficiency bonus (if
proficient) >= DC`. Default to DC 15 for an unremarkable "can they do this"
moment; reserve DC 20+ for genuinely difficult, high-stakes attempts.

## Advantage & Disadvantage

- Roll two d20s, take the higher (advantage) or lower (disadvantage).
- Advantage and disadvantage never stack — any number of sources of each
  still cancels out to a single net advantage, disadvantage, or straight
  roll (one of each cancels to a flat roll).
- Common advantage sources: attacking a prone target in melee, attacking
  an unseen/distracted target, help from another creature (see below).
- Common disadvantage sources: attacking a prone target at range,
  attacking while restrained/prone, attacking at long range with a
  ranged weapon, attacking in melee while an enemy is adjacent to a
  ranged attacker.

## The Help Action

A creature can use its action to help another creature's ability check or
attack roll, granting advantage on the next such roll before the helper's
next turn — provided the helper is capable of actually assisting (e.g. not
helping pick a lock they don't have tools for).

## Conditions

| Condition   | Key effects |
|-------------|-------------|
| Blinded     | Auto-fails sight-based checks; attacks against it have advantage; its attacks have disadvantage. |
| Charmed     | Can't attack the charmer or target it with harmful abilities/magic. |
| Deafened    | Auto-fails hearing-based checks. |
| Frightened  | Disadvantage on ability checks/attacks while the source of fear is in sight; can't willingly move closer to it. |
| Grappled    | Speed becomes 0. Ends if the grappler is incapacitated, or if the grappled creature is moved out of the grappler's reach by an effect. |
| Incapacitated | Can't take actions or reactions. |
| Invisible   | Considered heavily obscured; attacks against it have disadvantage, its attacks have advantage. |
| Paralyzed   | Incapacitated, can't move/speak; auto-fails Str/Dex saves; attacks against it have advantage; any hit from within 5 ft. is a critical hit. |
| Petrified   | Transformed to stone; incapacitated, can't move/speak; unaware of surroundings; resistance to all damage; auto-fails Str/Dex saves; immune to poison/disease. |
| Poisoned    | Disadvantage on attack rolls and ability checks. |
| Prone       | Can only crawl unless it stands (costs half movement); disadvantage on attack rolls; attacks against it have advantage if attacker is within 5 ft., disadvantage otherwise. |
| Restrained  | Speed 0; disadvantage on attack rolls and Dex saves; attacks against it have advantage. |
| Stunned     | Incapacitated, can't move, can speak only falteringly; auto-fails Str/Dex saves; attacks against it have advantage. |
| Unconscious | Incapacitated, can't move/speak, unaware of surroundings; drops what it's holding, falls prone; auto-fails Str/Dex saves; attacks against it have advantage; any hit from within 5 ft. is a critical hit. |

## Cover

| Cover      | Effect |
|------------|--------|
| Half cover | +2 to AC and Dex saves. (At least half the body is blocked.) |
| Three-quarters cover | +5 to AC and Dex saves. (Only a small portion is exposed — e.g. an arrow slit.) |
| Total cover | Can't be targeted directly. |

## Resting

- **Short rest** (1 hour): spend Hit Dice to heal (roll the die + Con
  modifier per Hit Die spent, minimum 0).
- **Long rest** (8 hours, at least 1 hour of which is sleeping or light
  activity): regain all HP and up to half total Hit Dice (minimum 1).
  Regains most limited-use class features. A character needs at least 6
  hours of sleep/rest as part of a long rest; interrupting it with more
  than 1 hour of walking, fighting, or similarly strenuous activity
  restarts the clock.
- A creature can't benefit from more than one long rest in a 24-hour
  period, and needs at least 1 hit point at the start of a long rest to
  gain its benefits.

## Death Saves

- At 0 HP (and not killed outright), an unconscious creature has three
  death-save "lives." Each turn, roll a d20 with no modifiers:
  - 10 or higher: a success.
  - 9 or lower: a failure.
  - Natural 20: regain 1 HP and become conscious.
  - Natural 1: counts as two failures.
- Three successes: stabilize (unconscious, but no more rolls needed until
  healed or it takes damage). Three failures: the creature dies.
- Taking any damage while at 0 HP causes one death-save failure (two if
  the hit is a critical hit); taking damage equal to or exceeding the
  creature's max HP in one hit while at 0 HP causes instant death
  (massive damage).
- A creature that receives healing while at 0 HP regains consciousness
  with the healed HP total, wiping any accumulated successes/failures.
