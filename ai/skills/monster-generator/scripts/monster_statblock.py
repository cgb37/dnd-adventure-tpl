#!/usr/bin/env python3
"""
Compute D&D 5e stat-block guidance (AC/HP/attack/damage ranges, proficiency
bonus) for a target challenge rating, plus an ability-score-to-modifier
helper.

Deterministic lookup only - monster-generator uses this so Claude never
eyeballs whether a stat block is plausible for its CR. Values mirror
../../rpg-character-gen/references/npc-stat-blocks.md's "CR Estimation
Guidelines" table exactly; see references/monster-building.md for how to
turn these ranges into a full stat block.

Usage:
  python3 monster_statblock.py --cr 5
  python3 monster_statblock.py --score 16

Output (--cr): JSON {"cr", "proficiency_bonus", "ac_range": [lo, hi],
  "hp_range": [lo, hi], "attack_bonus_range": [lo, hi],
  "damage_per_round_range": [lo, hi]}
Output (--score): JSON {"score", "modifier"}
On invalid input: JSON {"error": {"code", "message"}}, exit code 1.
"""
from __future__ import annotations

import argparse
import json

# CR Estimation Guidelines, exactly matching
# ../../rpg-character-gen/references/npc-stat-blocks.md.
CR_GUIDELINES: dict[str, dict[str, object]] = {
    "0": {"proficiency_bonus": 2, "ac_range": [10, 12], "hp_range": [1, 6], "attack_bonus_range": [2, 3], "damage_per_round_range": [0, 1]},
    "1/8": {"proficiency_bonus": 2, "ac_range": [12, 13], "hp_range": [7, 12], "attack_bonus_range": [3, 3], "damage_per_round_range": [2, 5]},
    "1/4": {"proficiency_bonus": 2, "ac_range": [13, 13], "hp_range": [13, 20], "attack_bonus_range": [3, 4], "damage_per_round_range": [4, 6]},
    "1/2": {"proficiency_bonus": 2, "ac_range": [13, 13], "hp_range": [20, 35], "attack_bonus_range": [3, 4], "damage_per_round_range": [6, 8]},
    "1": {"proficiency_bonus": 2, "ac_range": [13, 14], "hp_range": [36, 49], "attack_bonus_range": [3, 5], "damage_per_round_range": [9, 14]},
    "2": {"proficiency_bonus": 2, "ac_range": [13, 14], "hp_range": [50, 70], "attack_bonus_range": [3, 5], "damage_per_round_range": [15, 20]},
    "3": {"proficiency_bonus": 2, "ac_range": [13, 15], "hp_range": [71, 85], "attack_bonus_range": [4, 6], "damage_per_round_range": [21, 26]},
    "5": {"proficiency_bonus": 3, "ac_range": [15, 17], "hp_range": [101, 115], "attack_bonus_range": [6, 8], "damage_per_round_range": [33, 38]},
    "8": {"proficiency_bonus": 3, "ac_range": [16, 17], "hp_range": [146, 160], "attack_bonus_range": [7, 9], "damage_per_round_range": [51, 56]},
    "12": {"proficiency_bonus": 4, "ac_range": [17, 18], "hp_range": [206, 220], "attack_bonus_range": [8, 10], "damage_per_round_range": [69, 74]},
    "17": {"proficiency_bonus": 6, "ac_range": [19, 20], "hp_range": [281, 310], "attack_bonus_range": [10, 12], "damage_per_round_range": [93, 98]},
    "20": {"proficiency_bonus": 6, "ac_range": [19, 21], "hp_range": [341, 400], "attack_bonus_range": [10, 13], "damage_per_round_range": [111, 116]},
}


class StatblockError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _cr_sort_key(cr: str) -> float:
    if "/" in cr:
        num, den = cr.split("/")
        return int(num) / int(den)
    return float(cr)


def cr_guidelines(cr: str) -> dict:
    if cr not in CR_GUIDELINES:
        valid = sorted(CR_GUIDELINES, key=_cr_sort_key)
        raise StatblockError("invalid_cr", f"CR must be one of {valid}, got {cr!r}")
    return {"cr": cr, **CR_GUIDELINES[cr]}


def score_to_modifier(score: int) -> str:
    if score < 1 or score > 30:
        raise StatblockError("invalid_score", f"Ability score must be 1-30, got {score}")
    modifier = (score - 10) // 2
    return f"+{modifier}" if modifier >= 0 else str(modifier)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cr", help="Challenge rating, e.g. 5 or 1/4")
    parser.add_argument("--score", type=int, help="Ability score to convert to a modifier")
    args = parser.parse_args()

    if args.cr is None and args.score is None:
        print(json.dumps({"error": {"code": "missing_input", "message": "Provide --cr or --score"}}))
        return 1

    try:
        if args.cr is not None:
            result = cr_guidelines(args.cr)
        else:
            result = {"score": args.score, "modifier": score_to_modifier(args.score)}
    except StatblockError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
