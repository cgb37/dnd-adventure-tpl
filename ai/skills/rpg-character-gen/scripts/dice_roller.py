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
import random
import sys

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

POINT_BUY_COSTS = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9
}

POINT_BUY_BUDGET = 27


def modifier(score: int) -> int:
    return (score - 10) // 2


def roll_4d6_drop_lowest() -> int:
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort(reverse=True)
    return sum(rolls[:3])


def generate_rolled() -> dict:
    scores = sorted([roll_4d6_drop_lowest() for _ in range(6)], reverse=True)
    return {
        "method": "roll",
        "scores": scores,
        "modifiers": [modifier(s) for s in scores],
        "total": sum(scores),
        "average": round(sum(scores) / 6, 2)
    }


def generate_standard() -> dict:
    scores = list(STANDARD_ARRAY)
    return {
        "method": "standard_array",
        "scores": scores,
        "modifiers": [modifier(s) for s in scores],
        "total": sum(scores),
        "average": round(sum(scores) / 6, 2)
    }


def validate_point_buy(scores: list[int]) -> tuple[bool, str]:
    if len(scores) != 6:
        return False, f"Need exactly 6 scores, got {len(scores)}"
    for s in scores:
        if s < 8 or s > 15:
            return False, f"Score {s} out of range (8-15)"
    total_cost = sum(POINT_BUY_COSTS[s] for s in scores)
    if total_cost > POINT_BUY_BUDGET:
        return False, f"Total cost {total_cost} exceeds budget of {POINT_BUY_BUDGET}"
    return True, f"Valid. Points spent: {total_cost}/{POINT_BUY_BUDGET}"


def generate_point_buy(scores: list[int] | None = None) -> dict:
    if scores is None:
        # Default balanced point buy: 15, 14, 13, 12, 10, 8 (cost = 27)
        scores = [15, 14, 13, 12, 10, 8]

    valid, msg = validate_point_buy(scores)
    if not valid:
        return {"method": "point_buy", "error": msg}

    total_cost = sum(POINT_BUY_COSTS[s] for s in scores)
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

    if args.seed is not None:
        random.seed(args.seed)

    if args.method == "roll":
        result = generate_rolled()
    elif args.method == "standard":
        result = generate_standard()
    elif args.method == "pointbuy":
        result = generate_point_buy(args.scores)
    else:
        result = generate_rolled()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
