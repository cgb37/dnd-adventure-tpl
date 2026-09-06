from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from encounter_budget import BudgetError, compute_budget


def test_compute_budget_medium_level_5_party_of_4():
    result = compute_budget(level=5, party_size=4, difficulty="medium")
    assert result["per_character_xp"] == 500
    assert result["total_xp_budget"] == 2000


def test_compute_budget_deadly_level_1_party_of_4():
    result = compute_budget(level=1, party_size=4, difficulty="deadly")
    assert result["per_character_xp"] == 100
    assert result["total_xp_budget"] == 400


def test_compute_budget_includes_cr_to_xp_table():
    result = compute_budget(level=1, party_size=4, difficulty="easy")
    assert result["cr_to_xp"]["1"] == 200
    assert result["cr_to_xp"]["1/4"] == 50
    assert result["cr_to_xp"]["1/8"] == 25


def test_compute_budget_invalid_level_raises():
    with pytest.raises(BudgetError) as exc_info:
        compute_budget(level=21, party_size=4, difficulty="medium")
    assert exc_info.value.code == "invalid_level"


def test_compute_budget_invalid_difficulty_raises():
    with pytest.raises(BudgetError) as exc_info:
        compute_budget(level=5, party_size=4, difficulty="impossible")
    assert exc_info.value.code == "invalid_difficulty"


def test_compute_budget_invalid_party_size_raises():
    with pytest.raises(BudgetError) as exc_info:
        compute_budget(level=5, party_size=0, difficulty="medium")
    assert exc_info.value.code == "invalid_party_size"


def test_cli_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "encounter_budget.py"
    result = subprocess.run(
        [sys.executable, str(script), "--level", "5", "--party-size", "4", "--difficulty", "medium"],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert out["total_xp_budget"] == 2000


def test_cli_invalid_difficulty_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "encounter_budget.py"
    result = subprocess.run(
        [sys.executable, str(script), "--level", "5", "--party-size", "4", "--difficulty", "nope"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "invalid_difficulty"
