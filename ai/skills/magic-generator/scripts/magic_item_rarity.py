#!/usr/bin/env python3
"""
Compute D&D 5e magic item rarity guidance (DMG "Magic Item Rarity by
Character Level") for a target party level, or look up attunement/level
norms for an explicitly chosen rarity.

Deterministic lookup only - magic-generator uses this so Claude never
guesses whether a rarity is level-appropriate. See
references/magic-item-building.md for property-budget guidance once a
rarity is chosen.

Usage:
  python3 magic_item_rarity.py --party-level 8
  python3 magic_item_rarity.py --rarity rare

Output (--party-level): JSON {"party_level", "eligible_rarities": [...],
  "recommended_rarity", "typically_requires_attunement": {rarity: bool, ...}}
Output (--rarity): JSON {"rarity", "minimum_level", "typically_requires_attunement"}
On invalid input: JSON {"error": {"code", "message"}}, exit code 1.
"""
from __future__ import annotations

import argparse
import json

# DMG "Magic Item Rarity by Character Level" minimum levels, and whether
# attunement is typical (not universal - varies per item) at that rarity.
RARITY_ORDER: list[str] = ["common", "uncommon", "rare", "very rare", "legendary"]
RARITY_MINIMUM_LEVEL: dict[str, int] = {
    "common": 1, "uncommon": 1, "rare": 5, "very rare": 11, "legendary": 17,
}
RARITY_TYPICALLY_REQUIRES_ATTUNEMENT: dict[str, bool] = {
    "common": False, "uncommon": False, "rare": True, "very rare": True, "legendary": True,
}


class RarityError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def rarity_for_level(party_level: int) -> dict:
    if party_level < 1 or party_level > 20:
        raise RarityError("invalid_level", f"Party level must be 1-20, got {party_level}")

    eligible = [r for r in RARITY_ORDER if RARITY_MINIMUM_LEVEL[r] <= party_level]
    return {
        "party_level": party_level,
        "eligible_rarities": eligible,
        "recommended_rarity": eligible[-1],
        "typically_requires_attunement": {r: RARITY_TYPICALLY_REQUIRES_ATTUNEMENT[r] for r in eligible},
    }


def rarity_details(rarity: str) -> dict:
    key = rarity.strip().lower()
    if key not in RARITY_MINIMUM_LEVEL:
        raise RarityError("invalid_rarity", f"Rarity must be one of {RARITY_ORDER}, got {rarity!r}")
    return {
        "rarity": key,
        "minimum_level": RARITY_MINIMUM_LEVEL[key],
        "typically_requires_attunement": RARITY_TYPICALLY_REQUIRES_ATTUNEMENT[key],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--party-level", type=int)
    parser.add_argument("--rarity")
    args = parser.parse_args()

    if args.party_level is None and args.rarity is None:
        print(json.dumps({"error": {"code": "missing_input", "message": "Provide --party-level or --rarity"}}))
        return 1

    try:
        if args.rarity is not None:
            result = rarity_details(args.rarity)
        else:
            result = rarity_for_level(args.party_level)
    except RarityError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
