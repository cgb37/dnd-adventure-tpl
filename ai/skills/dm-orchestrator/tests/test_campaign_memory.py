from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from campaign_memory import (
    CampaignMemoryError,
    read_campaign_memory,
    redact_campaign_memory,
    write_campaign_memory,
)

SAMPLE = {
    "mode": "dm",
    "premise": "A cursed harvest festival draws travelers to a town that never lets them leave.",
    "scope": "3 chapters, short",
    "outline": [
        {
            "chapter": "01",
            "title": "The Festival Gates",
            "episodes": [
                {
                    "episode": "01",
                    "title": "Arrival",
                    "scenes": [
                        {
                            "scene": "01",
                            "premise": "The party arrives as the gates seal behind them.",
                            "needs": ["location"],
                            "status": "planned",
                        },
                        {
                            "scene": "02",
                            "premise": "A frightened local begs them to find her missing brother.",
                            "needs": ["encounter"],
                            "status": "planned",
                        },
                    ],
                }
            ],
        }
    ],
    "threads": [
        {
            "id": "missing-caravan",
            "summary": "A caravan vanished on the north road three days ago.",
            "status": "introduced",
        }
    ],
    "npcs": [
        {
            "name": "Captain Elena",
            "role": "town guard captain",
            "disposition": "suspicious of outsiders",
            "last_seen": "chapter 01, episode 01",
        }
    ],
    "content_index": [
        {
            "beat": "01.01.02",
            "kind": "encounter",
            "slug": "missing-brother-ambush",
            "path": "campaigns/my-campaign/_drafts/encounter/missing-brother-ambush.md",
        }
    ],
}


def test_read_campaign_memory_returns_none_when_missing(tmp_path: Path):
    assert read_campaign_memory(tmp_path, "my-campaign") is None


def test_write_then_read_round_trips(tmp_path: Path):
    write_campaign_memory(tmp_path, "my-campaign", SAMPLE)
    assert read_campaign_memory(tmp_path, "my-campaign") == SAMPLE


def test_read_returns_none_on_missing_required_keys(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "campaign.yml").write_text("premise: only this\n", encoding="utf-8")
    assert read_campaign_memory(tmp_path, "my-campaign") is None


def test_write_rejects_mode_change(tmp_path: Path):
    write_campaign_memory(tmp_path, "my-campaign", SAMPLE)
    changed = {**SAMPLE, "mode": "player"}
    try:
        write_campaign_memory(tmp_path, "my-campaign", changed)
        assert False, "expected CampaignMemoryError"
    except CampaignMemoryError as exc:
        assert exc.code == "mode_immutable"


def test_write_allows_same_mode_rewrite(tmp_path: Path):
    write_campaign_memory(tmp_path, "my-campaign", SAMPLE)
    updated = {**SAMPLE, "premise": "Updated premise text."}
    write_campaign_memory(tmp_path, "my-campaign", updated)
    result = read_campaign_memory(tmp_path, "my-campaign")
    assert result["premise"] == "Updated premise text."


def test_write_dedupes_content_index_by_beat_and_kind(tmp_path: Path):
    data = {
        **SAMPLE,
        "content_index": [
            {"beat": "01.01.02", "kind": "encounter", "slug": "first-version", "path": "a.md"},
            {"beat": "01.01.02", "kind": "encounter", "slug": "second-version", "path": "b.md"},
        ],
    }
    write_campaign_memory(tmp_path, "my-campaign", data)
    result = read_campaign_memory(tmp_path, "my-campaign")
    assert len(result["content_index"]) == 1
    assert result["content_index"][0]["slug"] == "second-version"


def test_numeric_looking_string_fields_round_trip_as_strings(tmp_path: Path):
    write_campaign_memory(tmp_path, "my-campaign", SAMPLE)
    result = read_campaign_memory(tmp_path, "my-campaign")
    chapter = result["outline"][0]
    assert chapter["chapter"] == "01"
    assert isinstance(chapter["chapter"], str)
    episode = chapter["episodes"][0]
    assert episode["episode"] == "01"
    scene = episode["scenes"][0]
    assert scene["scene"] == "01"


# --- finding 3: renderer/parser quoting must be true inverses ----------------

def _write_malformed(tmp_path: Path) -> Path:
    """A campaign.yml that makes the reader actually raise, not merely miss keys."""
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    path = campaign_dir / "campaign.yml"
    # Undecodable bytes: read_text(encoding="utf-8") raises inside the parse block,
    # which is exactly the "file exists but cannot be read" case that must not be
    # reported as "no campaign yet".
    path.write_bytes(b"mode: dm\noutline:\n  - chapter: \xff\xfe\x00\n")
    return path


def test_premise_with_internal_quotes_round_trips(tmp_path: Path):
    premise = 'Beware, she said, "the gate closes at dusk"'
    data = {**SAMPLE, "premise": premise}
    write_campaign_memory(tmp_path, "my-campaign", data)
    assert read_campaign_memory(tmp_path, "my-campaign")["premise"] == premise


def test_premise_starting_and_ending_with_a_quote_round_trips(tmp_path: Path):
    # The pathological case: rendered bare, this line would trip _parse_scalar's
    # startswith('"')/endswith('"') heuristic into json.loads and blow up the
    # whole read.
    premise = '"The gate closes at dusk," she warned, "so hurry"'
    data = {**SAMPLE, "premise": premise}
    write_campaign_memory(tmp_path, "my-campaign", data)
    assert read_campaign_memory(tmp_path, "my-campaign")["premise"] == premise


def test_parse_scalar_falls_back_to_raw_text_for_unparseable_quoted_token(tmp_path: Path):
    campaign_dir = tmp_path / "campaigns" / "my-campaign"
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "campaign.yml").write_text(
        'mode: dm\noutline: []\npremise: "a", "b"\n', encoding="utf-8"
    )
    result = read_campaign_memory(tmp_path, "my-campaign")
    assert result["premise"] == '"a", "b"'


# --- finding 2: corrupt is not the same as absent ----------------------------

def test_read_raises_invalid_campaign_memory_on_unreadable_file(tmp_path: Path):
    _write_malformed(tmp_path)
    try:
        read_campaign_memory(tmp_path, "my-campaign")
        assert False, "expected CampaignMemoryError"
    except CampaignMemoryError as exc:
        assert exc.code == "invalid_campaign_memory"


def test_write_propagates_invalid_campaign_memory_instead_of_swallowing_it(tmp_path: Path):
    """A corrupt file must block writes - otherwise mode silently becomes mutable."""
    _write_malformed(tmp_path)
    try:
        write_campaign_memory(tmp_path, "my-campaign", {**SAMPLE, "mode": "player"})
        assert False, "expected CampaignMemoryError"
    except CampaignMemoryError as exc:
        assert exc.code == "invalid_campaign_memory"


# --- finding 5: redaction ----------------------------------------------------

def test_redact_strips_every_spoiler_bearing_field():
    redacted = redact_campaign_memory(SAMPLE)
    assert set(redacted) == {"mode", "outline", "content_index"}
    assert redacted["mode"] == "dm"
    chapter = redacted["outline"][0]
    assert set(chapter) == {"chapter", "episodes"}
    episode = chapter["episodes"][0]
    assert set(episode) == {"episode", "scenes"}
    scene = episode["scenes"][0]
    assert set(scene) == {"scene", "needs", "status"}
    assert redacted["content_index"] == [{"beat": "01.01.02", "kind": "encounter"}]


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "campaign_memory.py"


def test_cli_read_missing_returns_found_false(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "nope"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == {"found": False}


def test_cli_write_then_read_round_trips(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--campaign", "my-campaign"],
        cwd=tmp_path, input=json.dumps(SAMPLE), capture_output=True, text=True, check=True,
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == SAMPLE


def test_cli_write_reports_mode_immutable_error(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--campaign", "my-campaign"],
        cwd=tmp_path, input=json.dumps(SAMPLE), capture_output=True, text=True, check=True,
    )
    changed = json.dumps({**SAMPLE, "mode": "player"})
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--campaign", "my-campaign"],
        cwd=tmp_path, input=changed, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["error"]["code"] == "mode_immutable"


def test_cli_read_reports_invalid_campaign_memory_error(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    _write_malformed(tmp_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "invalid_campaign_memory"
    assert payload["error"]["message"]


def test_cli_read_redact_returns_only_reduced_fields(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    subprocess.run(
        [sys.executable, str(SCRIPT), "write", "--campaign", "my-campaign"],
        cwd=tmp_path, input=json.dumps(SAMPLE), capture_output=True, text=True, check=True,
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "my-campaign", "--redact"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == {
        "mode": "dm",
        "outline": [
            {
                "chapter": "01",
                "episodes": [
                    {
                        "episode": "01",
                        "scenes": [
                            {"scene": "01", "needs": ["location"], "status": "planned"},
                            {"scene": "02", "needs": ["encounter"], "status": "planned"},
                        ],
                    }
                ],
            }
        ],
        "content_index": [{"beat": "01.01.02", "kind": "encounter"}],
    }
    # No spoiler-bearing text survives anywhere in the payload.
    for spoiler in ["Festival Gates", "Arrival", "gates seal", "Captain Elena",
                    "missing-caravan", "missing-brother-ambush", "_drafts"]:
        assert spoiler not in result.stdout


def test_cli_read_redact_on_missing_campaign_still_returns_found_false(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "read", "--campaign", "nope", "--redact"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == {"found": False}
