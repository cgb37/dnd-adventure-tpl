from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from party_state import read_party_state, write_party_state


def test_read_party_state_returns_none_when_missing(tmp_path: Path):
    assert read_party_state(tmp_path, "my-campaign") is None


def test_write_then_read_party_state_round_trips(tmp_path: Path):
    write_party_state(tmp_path, "my-campaign", level=5, size=4, classes=["bard", "barbarian"])
    state = read_party_state(tmp_path, "my-campaign")
    assert state == {
        "level": 5,
        "size": 4,
        "composition": [{"class": "bard"}, {"class": "barbarian"}],
    }


def test_read_party_state_returns_none_when_incomplete(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "party.yml").write_text("level: 5\n", encoding="utf-8")
    assert read_party_state(tmp_path, "my-campaign") is None


def test_cli_write_then_read(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    script = Path(__file__).resolve().parents[1] / "scripts" / "party_state.py"

    subprocess.run(
        [sys.executable, str(script), "write", "--campaign", "my-campaign",
         "--level", "5", "--size", "4", "--classes", "bard", "barbarian"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    result = subprocess.run(
        [sys.executable, str(script), "read", "--campaign", "my-campaign"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["level"] == 5
    assert out["size"] == 4
    assert out["composition"] == [{"class": "bard"}, {"class": "barbarian"}]


def test_cli_read_missing_returns_found_false(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    script = Path(__file__).resolve().parents[1] / "scripts" / "party_state.py"
    result = subprocess.run(
        [sys.executable, str(script), "read", "--campaign", "nope"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["found"] is False
