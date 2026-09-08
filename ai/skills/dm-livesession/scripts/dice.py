#!/usr/bin/env python3
"""
General dice-notation roller ("1d20+3", "2d6", "1d8-2") for ad-hoc DM
co-pilot rolls (initiative, damage, skill checks) during a live session.

Distinct from shared/dice_roller.py, which only generates D&D 5e ability
scores (4d6-drop-lowest / standard array / point buy) and has no general
NdM+K notation support - that module is not reused here because it cannot
do this job.

CLI usage:
  python3 dice.py "1d20+3"
  python3 dice.py "2d6" --seed 42

Output (success): {"notation": "1d20+3", "rolls": [14], "modifier": 3, "total": 17}
Output (invalid notation): {"error": {"code": "invalid_dice_notation", "message": "..."}},
  exit code 1 - never guesses at a malformed request.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from typing import Any

_NOTATION_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


class DiceNotationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def roll(notation: str, rng: random.Random) -> dict[str, Any]:
    """Roll a single dice-notation expression like '2d6+3'.

    Raises DiceNotationError on anything that isn't `count`d`sides`
    optionally followed by a +/- modifier (e.g. 'd20', '1d6x2', 'banana'
    all raise), or on a structurally nonsensical count/sides (0 dice, a
    1-sided die, more than 100 dice) - never guesses at what was meant.
    """
    match = _NOTATION_RE.match(notation.strip().replace(" ", ""))
    if not match:
        raise DiceNotationError(
            f"'{notation}' is not valid dice notation (expected e.g. '1d20+3', '2d6')"
        )
    count_text, sides_text, modifier_text = match.groups()
    count = int(count_text)
    sides = int(sides_text)
    modifier = int(modifier_text) if modifier_text else 0
    if count < 1 or count > 100:
        raise DiceNotationError(f"dice count must be 1-100, got {count}")
    if sides < 2:
        raise DiceNotationError(f"dice sides must be 2 or more, got {sides}")
    rolls = [rng.randint(1, sides) for _ in range(count)]
    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": sum(rolls) + modifier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notation", help="Dice notation, e.g. '1d20+3'")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible rolls")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    try:
        result = roll(args.notation, rng)
    except DiceNotationError as exc:
        print(json.dumps({"error": {"code": "invalid_dice_notation", "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
