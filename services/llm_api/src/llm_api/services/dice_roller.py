"""Dice roller for D&D 5e ability score generation.

Thin adapter over the canonical implementation in shared/dice_roller.py
(repo root), which is also used by
ai/skills/rpg-character-gen/scripts/dice_roller.py. This module exists so
callers can keep importing ``llm_api.services.dice_roller`` unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_shared_on_path() -> None:
    """Add the repo root to sys.path so ``shared`` can be imported.

    llm_api is installed as a normal pip package (see pyproject.toml), so
    it can't reach the repo-root ``shared/`` directory the way the
    ai/skills/* standalone scripts do. This walks up from this file's
    on-disk location (stable under an editable install) to find the repo
    root and adds it to sys.path once.

    Note: this only works when the source tree is present on disk (local
    dev, editable install, or the docker-compose ``api`` service, which
    bind-mounts the whole repo). The standalone services/llm_api/Dockerfile
    does not currently copy shared/ into its image and is not wired into
    docker-compose.yml's build step; it would need that fix separately
    before an image built from it could import this module.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "shared" / "dice_roller.py").exists():
            root = str(parent)
            if root not in sys.path:
                sys.path.insert(0, root)
            return
    raise ImportError(
        "Could not locate the repo-root 'shared' package from "
        f"{__file__}. It must be present on disk alongside 'services/'."
    )


_ensure_shared_on_path()

from shared.dice_roller import (  # noqa: E402
    POINT_BUY_BUDGET,
    POINT_BUY_COSTS,
    STANDARD_ARRAY,
    generate_rolled,
    generate_standard_array as _generate_standard_array,
    modifier,
    validate_point_buy_scores,
)

__all__ = ["STANDARD_ARRAY", "generate_rolled", "generate_standard_array", "generate_point_buy"]


def generate_standard_array() -> dict:
    """Return the standard array [15, 14, 13, 12, 10, 8]."""
    result = _generate_standard_array()
    return {"scores": result["scores"], "modifiers": result["modifiers"]}


def generate_point_buy(scores: list[int]) -> dict:
    """Validate and cost a set of six point-buy ability scores.

    Args:
        scores: Exactly 6 scores, each between 8 and 15 inclusive.

    Returns:
        Dict with ``scores``, ``modifiers``, ``costs``, ``total_points``, ``valid``.

    Raises:
        ValueError: If any score is outside 8-15 or count != 6.
    """
    validate_point_buy_scores(scores)
    costs = [POINT_BUY_COSTS[s] for s in scores]
    total = sum(costs)
    return {
        "scores": scores,
        "modifiers": [modifier(s) for s in scores],
        "costs": costs,
        "total_points": total,
        "valid": total <= POINT_BUY_BUDGET,
    }
