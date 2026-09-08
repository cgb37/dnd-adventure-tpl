from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from session_state import (
    SessionStateError,
    read_session_state,
    write_session_state,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "session_state.py"


def test_read_returns_none_when_missing(tmp_path: Path):
    assert read_session_state(tmp_path, "my-campaign") is None


def test_write_creates_file_with_current_position(tmp_path: Path):
    write_session_state(tmp_path, "my-campaign", {"current_position": {"beat": "01.01.01"}})
    result = read_session_state(tmp_path, "my-campaign")
    assert result["current_position"] == {"beat": "01.01.01"}
    assert result["event_log"] == []
    assert result["delivered_beats"] == []


def test_write_replaces_current_position_wholesale(tmp_path: Path):
    write_session_state(tmp_path, "my-campaign", {"current_position": {"beat": "01.01.01"}})
    write_session_state(tmp_path, "my-campaign", {"current_position": {"beat": "01.01.02"}})
    result = read_session_state(tmp_path, "my-campaign")
    assert result["current_position"] == {"beat": "01.01.02"}


def test_write_appends_event_log_without_overwriting(tmp_path: Path):
    write_session_state(
        tmp_path,
        "my-campaign",
        {"event_log": [{"beat": "01.01.01", "summary": "Arrived at the gates."}]},
    )
    write_session_state(
        tmp_path,
        "my-campaign",
        {"event_log": [{"beat": "01.01.02", "summary": "Agreed to help the local."}]},
    )
    result = read_session_state(tmp_path, "my-campaign")
    assert result["event_log"] == [
        {"beat": "01.01.01", "summary": "Arrived at the gates."},
        {"beat": "01.01.02", "summary": "Agreed to help the local."},
    ]


def test_write_appends_delivered_beats_without_duplicating(tmp_path: Path):
    write_session_state(tmp_path, "my-campaign", {"delivered_beats": ["01.01.01"]})
    write_session_state(tmp_path, "my-campaign", {"delivered_beats": ["01.01.01", "01.01.02"]})
    result = read_session_state(tmp_path, "my-campaign")
    assert result["delivered_beats"] == ["01.01.01", "01.01.02"]


def test_write_combines_all_three_updates_in_one_call(tmp_path: Path):
    write_session_state(
        tmp_path,
        "my-campaign",
        {
            "current_position": {"beat": "01.01.02"},
            "event_log": [{"beat": "01.01.01", "summary": "Arrived at the gates."}],
            "delivered_beats": ["01.01.01"],
        },
    )
    result = read_session_state(tmp_path, "my-campaign")
    assert result["current_position"] == {"beat": "01.01.02"}
    assert result["event_log"] == [{"beat": "01.01.01", "summary": "Arrived at the gates."}]
    assert result["delivered_beats"] == ["01.01.01"]


def test_read_malformed_file_raises_invalid_session_state(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "session.yml").write_bytes(b"\xff\xfe not valid utf-8 or yaml \x00")
    try:
        read_session_state(tmp_path, "my-campaign")
        assert False, "expected SessionStateError"
    except SessionStateError as exc:
        assert exc.code == "invalid_session_state"


def test_cli_read_missing_returns_found_false(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"found": false' in result.stdout


def test_cli_write_then_read_round_trips(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    write_result = subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--campaign", "my-campaign"],
        input='{"current_position": {"beat": "01.01.01"}, "delivered_beats": ["01.01.01"]}',
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert write_result.returncode == 0
    assert "session.yml" in write_result.stdout

    read_result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert read_result.returncode == 0
    assert '"beat": "01.01.01"' in read_result.stdout
