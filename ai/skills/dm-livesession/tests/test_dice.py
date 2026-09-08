from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dice import DiceNotationError, roll

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dice.py"


def test_roll_single_die_with_positive_modifier():
    result = roll("1d20+3", random.Random(42))
    assert len(result["rolls"]) == 1
    assert 1 <= result["rolls"][0] <= 20
    assert result["modifier"] == 3
    assert result["total"] == result["rolls"][0] + 3


def test_roll_multiple_dice_no_modifier():
    result = roll("2d6", random.Random(1))
    assert len(result["rolls"]) == 2
    assert all(1 <= r <= 6 for r in result["rolls"])
    assert result["modifier"] == 0
    assert result["total"] == sum(result["rolls"])


def test_roll_negative_modifier():
    result = roll("1d8-2", random.Random(7))
    assert result["modifier"] == -2
    assert result["total"] == result["rolls"][0] - 2


def test_roll_is_deterministic_with_same_seed():
    first = roll("4d6", random.Random(99))
    second = roll("4d6", random.Random(99))
    assert first == second


def test_roll_rejects_missing_count():
    try:
        roll("d20", random.Random(1))
        assert False, "expected DiceNotationError"
    except DiceNotationError:
        pass


def test_roll_rejects_nonsense_notation():
    try:
        roll("banana", random.Random(1))
        assert False, "expected DiceNotationError"
    except DiceNotationError:
        pass


def test_roll_rejects_zero_count():
    try:
        roll("0d6", random.Random(1))
        assert False, "expected DiceNotationError"
    except DiceNotationError:
        pass


def test_roll_rejects_one_sided_die():
    try:
        roll("1d1", random.Random(1))
        assert False, "expected DiceNotationError"
    except DiceNotationError:
        pass


def test_cli_roll_prints_expected_shape():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "1d20+3", "--seed", "42"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"notation": "1d20+3"' in result.stdout
    assert '"modifier": 3' in result.stdout


def test_cli_rejects_invalid_notation():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "banana"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "invalid_dice_notation" in result.stdout
