from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from players_state import read_players_state

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "players_state.py"


def test_read_returns_none_when_missing(tmp_path: Path):
    assert read_players_state(tmp_path, "my-campaign") is None


def test_read_parses_single_player_with_characters(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "players.yml").write_text(
        "players:\n"
        "  - name: Chuck\n"
        "    slug: chuck\n"
        "    characters:\n"
        "      - aiden-oathkeeper\n"
        "      - dravroth-oathbreaker\n"
        "      - guillemette-bevan\n"
        "      - stallion\n",
        encoding="utf-8",
    )
    state = read_players_state(tmp_path, "my-campaign")
    assert state == {
        "players": [
            {
                "name": "Chuck",
                "slug": "chuck",
                "characters": [
                    "aiden-oathkeeper",
                    "dravroth-oathbreaker",
                    "guillemette-bevan",
                    "stallion",
                ],
            }
        ]
    }


def test_read_parses_multiple_players(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "players.yml").write_text(
        "players:\n"
        "  - name: Chuck\n"
        "    slug: chuck\n"
        "    characters:\n"
        "      - aiden-oathkeeper\n"
        "  - name: Robin\n"
        "    slug: robin\n"
        "    characters:\n"
        "      - stallion\n",
        encoding="utf-8",
    )
    state = read_players_state(tmp_path, "my-campaign")
    assert state == {
        "players": [
            {"name": "Chuck", "slug": "chuck", "characters": ["aiden-oathkeeper"]},
            {"name": "Robin", "slug": "robin", "characters": ["stallion"]},
        ]
    }


def test_read_returns_none_when_file_has_no_players(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "players.yml").write_text("players:\n", encoding="utf-8")
    assert read_players_state(tmp_path, "my-campaign") is None


def test_cli_read_missing_returns_found_false(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "nope"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["found"] is False


def test_cli_read_found(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "players.yml").write_text(
        "players:\n"
        "  - name: Chuck\n"
        "    slug: chuck\n"
        "    characters:\n"
        "      - aiden-oathkeeper\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out == {
        "players": [{"name": "Chuck", "slug": "chuck", "characters": ["aiden-oathkeeper"]}]
    }
