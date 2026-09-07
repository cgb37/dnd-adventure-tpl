from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dnd5eapi_client import Dnd5eApiError, fetch


def _fake_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = json.dumps(payload).encode("utf-8")
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


def test_fetch_returns_cached_response_without_network(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "rules-grappling.json").write_text(
        json.dumps({"name": "Grappling"}), encoding="utf-8"
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen.assert_not_called()
    assert result == {"name": "Grappling"}


def test_fetch_writes_successful_response_to_cache(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {"name": "Grappling", "desc": "You can grapple..."}

    with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock_urlopen:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen.assert_called_once()
    assert result == payload
    cached = json.loads((cache_dir / "rules-grappling.json").read_text(encoding="utf-8"))
    assert cached == payload


def test_fetch_second_call_hits_cache_not_network(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {"name": "Grappling"}

    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        fetch("rules/grappling", cache_dir=cache_dir)

    with patch("urllib.request.urlopen") as mock_urlopen_second:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen_second.assert_not_called()
    assert result == payload


def test_fetch_maps_http_404_to_not_found(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/nonexistent", cache_dir=cache_dir)

    assert exc_info.value.code == "not_found"


def test_fetch_maps_other_http_errors_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.HTTPError(url="x", code=500, msg="Server Error", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_maps_connection_failure_to_network_error(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.URLError("Connection refused")

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "network_error"


def test_fetch_maps_timeout_error_to_network_error(tmp_path: Path):
    cache_dir = tmp_path / "cache"

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "network_error"


def test_fetch_maps_malformed_json_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    mock = MagicMock()
    mock.read.return_value = b"not json"
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_maps_corrupt_cache_file_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "rules-grappling.json").write_text("not json", encoding="utf-8")

    with pytest.raises(Dnd5eApiError) as exc_info:
        fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_maps_invalid_utf8_cache_file_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "rules-grappling.json").write_bytes(b"\xff\xfe not utf8")

    with pytest.raises(Dnd5eApiError) as exc_info:
        fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_cache_write_failure_does_not_prevent_returning_data(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {"name": "Grappling"}

    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        with patch("pathlib.Path.mkdir", side_effect=OSError("disk full")):
            result = fetch("rules/grappling", cache_dir=cache_dir)

    assert result == payload


def test_fetch_raises_repo_root_not_found_without_cache_dir_or_git(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Dnd5eApiError) as exc_info:
        fetch("rules/grappling")
    assert exc_info.value.code == "repo_root_not_found"


def test_cli_success_prints_json(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    cache_dir = tmp_path / ".cache" / "dnd5eapi"
    cache_dir.mkdir(parents=True)
    (cache_dir / "rules-grappling.json").write_text(
        json.dumps({"name": "Grappling"}), encoding="utf-8"
    )

    script = Path(__file__).resolve().parents[1] / "dnd5eapi_client.py"
    result = subprocess.run(
        [sys.executable, str(script), "rules/grappling"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out == {"name": "Grappling"}


def test_cli_error_exits_nonzero(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    cache_dir = tmp_path / ".cache" / "dnd5eapi"
    cache_dir.mkdir(parents=True)
    (cache_dir / "rules-nonexistent.json").write_text("not json", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "dnd5eapi_client.py"
    result = subprocess.run(
        [sys.executable, str(script), "rules/nonexistent"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "invalid_response"
