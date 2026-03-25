"""Dice roller for D&D 5e ability score generation.

Ported from ai/skills/rpg-character-gen/scripts/dice_roller.py.
Three methods: roll (4d6 drop lowest), standard array, point buy.
"""
from __future__ import annotations

import random

STANDARD_ARRAY: list[int] = [15, 14, 13, 12, 10, 8]

# Point-buy cost table (score → cost). Scores 8–15 only.
_POINT_COSTS: dict[int, int] = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9,
}
_POINT_BUY_BUDGET = 27


def _modifier(score: int) -> int:
    return (score - 10) // 2


def generate_rolled(*, seed: int | None = None) -> dict:
    """Roll 4d6-drop-lowest for six ability scores.

    Args:
        seed: Optional RNG seed for reproducibility.

    Returns:
        Dict with ``scores`` (sorted descending), ``modifiers``, ``total``, ``average``.
    """
    rng = random.Random(seed)
    scores: list[int] = []
    for _ in range(6):
        rolls = sorted([rng.randint(1, 6) for _ in range(4)])
        scores.append(sum(rolls[1:]))  # drop lowest
    scores.sort(reverse=True)
    modifiers = [_modifier(s) for s in scores]
    return {
        "scores": scores,
        "modifiers": modifiers,
        "total": sum(scores),
        "average": round(sum(scores) / 6, 1),
    }


def generate_standard_array() -> dict:
    """Return the standard array [15, 14, 13, 12, 10, 8]."""
    scores = list(STANDARD_ARRAY)
    return {
        "scores": scores,
        "modifiers": [_modifier(s) for s in scores],
    }


def generate_point_buy(scores: list[int]) -> dict:
    """Validate and cost a set of six point-buy ability scores.

    Args:
        scores: Exactly 6 scores, each between 8 and 15 inclusive.

    Returns:
        Dict with ``scores``, ``modifiers``, ``costs``, ``total_points``, ``valid``.

    Raises:
        ValueError: If any score is outside 8–15 or count != 6.
    """
    if len(scores) != 6:
        raise ValueError(f"Expected 6 scores, got {len(scores)}")
    for s in scores:
        if s < 8 or s > 15:
            raise ValueError(f"Point-buy scores must be 8–15, got {s}")

    costs = [_POINT_COSTS[s] for s in scores]
    total = sum(costs)
    return {
        "scores": scores,
        "modifiers": [_modifier(s) for s in scores],
        "costs": costs,
        "total_points": total,
        "valid": total <= _POINT_BUY_BUDGET,
    }
