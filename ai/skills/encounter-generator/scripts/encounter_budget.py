#!/usr/bin/env python3
"""
Compute a D&D 5e encounter XP budget from party level, size, and desired difficulty.

Deterministic arithmetic only - the encounter-generator skill uses this budget,
plus the cr_to_xp table below, to pick/reskin monsters. See
references/encounter-building.md for how to spend the budget (multi-monster
multiplier guidance, terrain, tactics).

Usage:
  python3 encounter_budget.py --level 5 --party-size 4 --difficulty medium

Output: JSON {"party_level", "party_size", "difficulty", "per_character_xp",
              "total_xp_budget", "cr_to_xp"}
On invalid input: JSON {"error": {"code", "message"}}, exit code 1.
"""
from __future__ import annotations

import argparse
import json

# XP thresholds per character, by level and difficulty (D&D 5e Basic Rules).
XP_THRESHOLDS: dict[int, dict[str, int]] = {
    1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
    2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
    3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
    4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
    5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
    6: {"easy": 300, "medium": 600, "hard": 900, "deadly": 1400},
    7: {"easy": 350, "medium": 750, "hard": 1100, "deadly": 1700},
    8: {"easy": 450, "medium": 900, "hard": 1400, "deadly": 2100},
    9: {"easy": 550, "medium": 1100, "hard": 1600, "deadly": 2400},
    10: {"easy": 600, "medium": 1200, "hard": 1900, "deadly": 2800},
    11: {"easy": 800, "medium": 1600, "hard": 2400, "deadly": 3600},
    12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
    13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
    14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
    15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
    16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
    17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
    18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
    19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
    20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12000},
}

# XP value per monster, by challenge rating (D&D 5e Basic Rules).
CR_TO_XP: dict[str, int] = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
    "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900,
    "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
}

DIFFICULTIES = ("easy", "medium", "hard", "deadly")


class BudgetError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def compute_budget(*, level: int, party_size: int, difficulty: str) -> dict:
    if level not in XP_THRESHOLDS:
        raise BudgetError("invalid_level", f"Level must be 1-20, got {level}")
    if difficulty not in DIFFICULTIES:
        raise BudgetError(
            "invalid_difficulty", f"Difficulty must be one of {DIFFICULTIES}, got {difficulty!r}"
        )
    if party_size < 1:
        raise BudgetError("invalid_party_size", f"Party size must be >= 1, got {party_size}")

    per_character_xp = XP_THRESHOLDS[level][difficulty]
    return {
        "party_level": level,
        "party_size": party_size,
        "difficulty": difficulty,
        "per_character_xp": per_character_xp,
        "total_xp_budget": per_character_xp * party_size,
        "cr_to_xp": CR_TO_XP,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", type=int, required=True)
    parser.add_argument("--party-size", type=int, required=True)
    parser.add_argument("--difficulty", required=True)
    args = parser.parse_args()

    try:
        result = compute_budget(level=args.level, party_size=args.party_size, difficulty=args.difficulty)
    except BudgetError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
