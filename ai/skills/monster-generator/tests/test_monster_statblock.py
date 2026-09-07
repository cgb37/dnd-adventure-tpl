from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from monster_statblock import StatblockError, cr_guidelines, score_to_modifier


def test_cr_guidelines_cr_5():
    result = cr_guidelines("5")
    assert result["cr"] == "5"
    assert result["proficiency_bonus"] == 3
    assert result["ac_range"] == [15, 17]
    assert result["hp_range"] == [101, 115]
    assert result["attack_bonus_range"] == [6, 8]
    assert result["damage_per_round_range"] == [33, 38]


def test_cr_guidelines_cr_1_8():
    result = cr_guidelines("1/8")
    assert result["proficiency_bonus"] == 2
    assert result["hp_range"] == [7, 12]


def test_cr_guidelines_cr_20():
    result = cr_guidelines("20")
    assert result["proficiency_bonus"] == 6
    assert result["hp_range"] == [341, 400]


def test_cr_guidelines_invalid_cr_raises():
    with pytest.raises(StatblockError) as exc_info:
        cr_guidelines("6")
    assert exc_info.value.code == "invalid_cr"


def test_score_to_modifier_positive():
    assert score_to_modifier(16) == "+3"


def test_score_to_modifier_zero():
    assert score_to_modifier(10) == "+0"
    assert score_to_modifier(11) == "+0"


def test_score_to_modifier_negative():
    assert score_to_modifier(8) == "-1"


def test_score_to_modifier_invalid_raises():
    with pytest.raises(StatblockError) as exc_info:
        score_to_modifier(0)
    assert exc_info.value.code == "invalid_score"


def test_cli_cr_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--cr", "5"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["proficiency_bonus"] == 3


def test_cli_score_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--score", "16"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["modifier"] == "+3"


def test_cli_invalid_cr_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--cr", "6"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "invalid_cr"


def test_cli_missing_input_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "missing_input"
