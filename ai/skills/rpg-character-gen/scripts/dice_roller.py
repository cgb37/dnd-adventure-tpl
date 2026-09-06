#!/usr/bin/env python3
"""
D&D 5e Ability Score Generator

Supports three methods:
  - roll:     4d6 drop lowest, six times
  - standard: Standard Array (15, 14, 13, 12, 10, 8)
  - pointbuy: Point Buy with 27 points (scores 8-15)

Usage:
  python dice_roller.py [method]
  python dice_roller.py roll
  python dice_roller.py standard
  python dice_roller.py pointbuy --scores 15 14 13 12 10 8

Output: JSON object with the six ability scores and metadata.
"""

import argparse
import json
import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    """Make the repo-root ``shared`` package importable.

    This script is invoked directly (``python dice_roller.py ...``), not
    as part of an installed package, so it walks up from its own location
    to find the repo root (the ``shared/`` directory's parent) and adds it
    to sys.path.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "shared" / "dice_roller.py").exists():
            sys.path.insert(0, str(parent))
            return
    raise RuntimeError("Could not locate repo-root 'shared' package from dice_roller.py")


_add_repo_root_to_path()

from shared.dice_roller import (  # noqa: E402
    POINT_BUY_BUDGET,
    STANDARD_ARRAY,
    check_point_buy,
    generate_rolled as _generate_rolled,
    modifier,
)


def generate_rolled(*, seed: int | None = None) -> dict:
    result = _generate_rolled(seed=seed)
    return {"method": "roll", **result}


def generate_standard() -> dict:
    scores = list(STANDARD_ARRAY)
    return {
        "method": "standard_array",
        "scores": scores,
        "modifiers": [modifier(s) for s in scores],
        "total": sum(scores),
        "average": round(sum(scores) / 6, 2)
    }


def generate_point_buy(scores: list[int] | None = None) -> dict:
    if scores is None:
        # Default balanced point buy: 15, 14, 13, 12, 10, 8 (cost = 27)
        scores = [15, 14, 13, 12, 10, 8]

    valid, msg, total_cost = check_point_buy(scores)
    if not valid:
        return {"method": "point_buy", "error": msg}

    scores_sorted = sorted(scores, reverse=True)
    return {
        "method": "point_buy",
        "scores": scores_sorted,
        "modifiers": [modifier(s) for s in scores_sorted],
        "points_spent": total_cost,
        "points_remaining": POINT_BUY_BUDGET - total_cost,
        "total": sum(scores_sorted),
        "average": round(sum(scores_sorted) / 6, 2)
    }


def main():
    parser = argparse.ArgumentParser(description="D&D 5e Ability Score Generator")
    parser.add_argument("method", nargs="?", default="roll",
                        choices=["roll", "standard", "pointbuy"],
                        help="Generation method (default: roll)")
    parser.add_argument("--scores", nargs=6, type=int,
                        help="Six ability scores for point buy validation")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible rolls")

    args = parser.parse_args()

    if args.method == "roll":
        result = generate_rolled(seed=args.seed)
    elif args.method == "standard":
        result = generate_standard()
    elif args.method == "pointbuy":
        result = generate_point_buy(args.scores)
    else:
        result = generate_rolled(seed=args.seed)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
