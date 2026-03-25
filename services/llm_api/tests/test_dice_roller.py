from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")


def test_rolled_returns_six_scores():
    from llm_api.services.dice_roller import generate_rolled

    result = generate_rolled(seed=42)
    assert len(result["scores"]) == 6
    assert all(3 <= s <= 18 for s in result["scores"])
    assert len(result["modifiers"]) == 6


def test_standard_array_returns_fixed_scores():
    from llm_api.services.dice_roller import generate_standard_array

    result = generate_standard_array()
    assert result["scores"] == [15, 14, 13, 12, 10, 8]
    assert len(result["modifiers"]) == 6


def test_point_buy_valid():
    from llm_api.services.dice_roller import generate_point_buy

    scores = [15, 14, 13, 12, 10, 8]  # standard array = 27 points
    result = generate_point_buy(scores)
    assert result["total_points"] == 27
    assert result["valid"] is True


def test_point_buy_over_budget():
    from llm_api.services.dice_roller import generate_point_buy

    scores = [15, 15, 15, 15, 15, 15]
    result = generate_point_buy(scores)
    assert result["valid"] is False


def test_point_buy_score_out_of_range():
    from llm_api.services.dice_roller import generate_point_buy

    with pytest.raises(ValueError, match="8.*15"):
        generate_point_buy([7, 14, 13, 12, 10, 8])


def test_rolled_seed_reproducible():
    from llm_api.services.dice_roller import generate_rolled

    a = generate_rolled(seed=99)
    b = generate_rolled(seed=99)
    assert a["scores"] == b["scores"]
