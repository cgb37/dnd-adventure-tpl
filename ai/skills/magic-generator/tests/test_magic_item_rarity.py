from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from magic_item_rarity import RarityError, rarity_details, rarity_for_level


def test_rarity_for_level_1():
    result = rarity_for_level(1)
    assert result["eligible_rarities"] == ["common", "uncommon"]
    assert result["recommended_rarity"] == "uncommon"
    assert result["typically_requires_attunement"] == {"common": False, "uncommon": False}


def test_rarity_for_level_8():
    result = rarity_for_level(8)
    assert result["eligible_rarities"] == ["common", "uncommon", "rare"]
    assert result["recommended_rarity"] == "rare"


def test_rarity_for_level_20():
    result = rarity_for_level(20)
    assert result["eligible_rarities"] == ["common", "uncommon", "rare", "very rare", "legendary"]
    assert result["recommended_rarity"] == "legendary"


def test_rarity_for_level_invalid_raises():
    with pytest.raises(RarityError) as exc_info:
        rarity_for_level(21)
    assert exc_info.value.code == "invalid_level"


def test_rarity_details_rare():
    result = rarity_details("rare")
    assert result["minimum_level"] == 5
    assert result["typically_requires_attunement"] is True


def test_rarity_details_case_insensitive():
    result = rarity_details("Very Rare")
    assert result["rarity"] == "very rare"
    assert result["minimum_level"] == 11


def test_rarity_details_invalid_raises():
    with pytest.raises(RarityError) as exc_info:
        rarity_details("mythic")
    assert exc_info.value.code == "invalid_rarity"


def test_cli_party_level_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script), "--party-level", "8"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["recommended_rarity"] == "rare"


def test_cli_rarity_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script), "--rarity", "legendary"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["minimum_level"] == 17


def test_cli_missing_input_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "missing_input"
