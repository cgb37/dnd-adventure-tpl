"""Canonical D&D 5e ability-score generation logic.

Single source of truth for the 4d6-drop-lowest roll, standard array, and
point-buy rules used by both the rpg-character-gen skill's CLI script
(ai/skills/rpg-character-gen/scripts/dice_roller.py) and the FastAPI
llm_api service (services/llm_api/src/llm_api/services/dice_roller.py).
"""
from __future__ import annotations

import random

STANDARD_ARRAY: list[int] = [15, 14, 13, 12, 10, 8]

# Point-buy cost table (score -> cost). Scores 8-15 only.
POINT_BUY_COSTS: dict[int, int] = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9,
}
POINT_BUY_BUDGET = 27


def modifier(score: int) -> int:
    return (score - 10) // 2


def roll_4d6_drop_lowest(rng: random.Random) -> int:
    rolls = sorted(rng.randint(1, 6) for _ in range(4))
    return sum(rolls[1:])


def generate_rolled(*, seed: int | None = None) -> dict:
    """Roll 4d6-drop-lowest for six ability scores.

    Args:
        seed: Optional RNG seed for reproducibility.

    Returns:
        Dict with ``scores`` (sorted descending), ``modifiers``, ``total``, ``average``.
    """
    rng = random.Random(seed)
    scores = sorted((roll_4d6_drop_lowest(rng) for _ in range(6)), reverse=True)
    modifiers = [modifier(s) for s in scores]
    return {
        "scores": scores,
        "modifiers": modifiers,
        "total": sum(scores),
        "average": round(sum(scores) / 6, 2),
    }


def generate_standard_array() -> dict:
    """Return the standard array [15, 14, 13, 12, 10, 8]."""
    scores = list(STANDARD_ARRAY)
    modifiers = [modifier(s) for s in scores]
    return {
        "scores": scores,
        "modifiers": modifiers,
        "total": sum(scores),
        "average": round(sum(scores) / 6, 2),
    }


def validate_point_buy_scores(scores: list[int]) -> None:
    """Raise ValueError if the six point-buy scores are structurally invalid.

    Only checks count and per-score range (8-15) — budget overruns are not
    an error, and are reported separately via ``check_point_buy``.
    """
    if len(scores) != 6:
        raise ValueError(f"Expected 6 scores, got {len(scores)}")
    for s in scores:
        if s < 8 or s > 15:
            raise ValueError(f"Point-buy scores must be 8-15, got {s}")


def check_point_buy(scores: list[int]) -> tuple[bool, str, int]:
    """Validate point-buy scores without raising.

    Returns:
        ``(valid, message, total_cost)``, covering both structural problems
        (wrong count, out-of-range score) and budget overruns.
    """
    if len(scores) != 6:
        return False, f"Need exactly 6 scores, got {len(scores)}", 0
    for s in scores:
        if s < 8 or s > 15:
            return False, f"Score {s} out of range (8-15)", 0
    total_cost = sum(POINT_BUY_COSTS[s] for s in scores)
    if total_cost > POINT_BUY_BUDGET:
        return False, f"Total cost {total_cost} exceeds budget of {POINT_BUY_BUDGET}", total_cost
    return True, f"Valid. Points spent: {total_cost}/{POINT_BUY_BUDGET}", total_cost
