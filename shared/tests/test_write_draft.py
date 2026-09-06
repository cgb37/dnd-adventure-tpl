from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from write_draft import (
    DraftWriteError,
    compute_draft_id,
    find_repo_root,
    get_active_campaign,
    render_frontmatter,
    write_draft,
)


def test_render_frontmatter_handles_strings_lists_bools():
    yaml_text = render_frontmatter({
        "layout": "encounter",
        "title": "Goblin Ambush",
        "search": True,
        "tags": ["goblins", "ambush"],
    })
    assert "layout: encounter" in yaml_text
    assert "search: true" in yaml_text
    assert "tags:\n  - goblins\n  - ambush" in yaml_text


def test_render_frontmatter_handles_empty_list():
    yaml_text = render_frontmatter({"tags": []})
    assert "tags: []" in yaml_text


def test_render_frontmatter_quotes_numeric_looking_strings():
    yaml_text = render_frontmatter({"chapter": "01", "episode": "02"})
    assert 'chapter: "01"' in yaml_text
    assert 'episode: "02"' in yaml_text


def test_render_frontmatter_quotes_yaml_bool_and_null_lookalikes():
    yaml_text = render_frontmatter({"a": "yes", "b": "null", "c": "true"})
    assert 'a: "yes"' in yaml_text
    assert 'b: "null"' in yaml_text
    assert 'c: "true"' in yaml_text


def test_render_frontmatter_quotes_leading_indicator_chars():
    yaml_text = render_frontmatter({"title": "*The Wailing Deep*"})
    assert 'title: "*The Wailing Deep*"' in yaml_text


def test_render_frontmatter_does_not_quote_ordinary_hyphen_prefixed_words():
    # PyYAML's safe_dump only treats a leading "-" as ambiguous when the string IS "-"
    # or starts with "- " (the block-sequence-entry form) - an ordinary word that merely
    # starts with a hyphen, like "-foo", is emitted unquoted.
    yaml_text = render_frontmatter({"k": "-foo", "j": "-1a", "m": "-yes"})
    assert "k: -foo" in yaml_text
    assert "j: -1a" in yaml_text
    assert "m: -yes" in yaml_text


def test_render_frontmatter_does_not_quote_none_string():
    # "none" (any case) is not a YAML 1.1 null lookalike - only null/Null/NULL/~/"" are.
    yaml_text = render_frontmatter({"k": "none", "j": "None", "m": "NONE"})
    assert "k: none" in yaml_text
    assert "j: None" in yaml_text
    assert "m: NONE" in yaml_text


def test_render_frontmatter_quotes_standalone_or_leading_hyphen_space():
    # These really are YAML-ambiguous: a bare "-" or "- " prefix reads as a block
    # sequence entry marker.
    yaml_text = render_frontmatter({"k": "-", "j": "- foo"})
    assert 'k: "-"' in yaml_text
    assert 'j: "- foo"' in yaml_text


def test_compute_draft_id_is_deterministic():
    first = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    second = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    assert first == second


def test_compute_draft_id_matches_known_namespace():
    # Same formula as services/llm_api/src/llm_api/services/ids.py::content_id().
    namespace = uuid.UUID("c9b4f65f-2d5a-4e62-9e04-8b6ea6c60b41")
    expected = uuid.uuid5(namespace, "encounter:test-campaign:goblin-ambush")
    actual = compute_draft_id(kind="encounter", campaign="test-campaign", slug="goblin-ambush")
    assert actual == expected


def test_get_active_campaign_missing_file_raises(tmp_path: Path):
    with pytest.raises(DraftWriteError) as exc_info:
        get_active_campaign(tmp_path)
    assert exc_info.value.code == "no_active_campaign"


def test_get_active_campaign_empty_file_raises(tmp_path: Path):
    (tmp_path / ".active-campaign").write_text("   \n", encoding="utf-8")
    with pytest.raises(DraftWriteError) as exc_info:
        get_active_campaign(tmp_path)
    assert exc_info.value.code == "no_active_campaign"


def test_get_active_campaign_reads_file(tmp_path: Path):
    (tmp_path / ".active-campaign").write_text("my-campaign\n", encoding="utf-8")
    assert get_active_campaign(tmp_path) == "my-campaign"


def test_write_draft_writes_frontmatter_and_body(tmp_path: Path):
    path = write_draft(
        repo_root=tmp_path,
        kind="encounter",
        campaign="test-campaign",
        slug="goblin-ambush",
        title="Goblin Ambush",
        frontmatter={"layout": "encounter", "title": "Goblin Ambush", "tags": ["goblins"]},
        body="A pack of goblins lies in wait.",
    )
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "layout: encounter" in text
    assert "# Goblin Ambush" in text
    assert "A pack of goblins lies in wait." in text
    assert path == tmp_path / "campaigns" / "test-campaign" / "_drafts" / "encounter" / "goblin-ambush.md"


def test_find_repo_root_walks_up_to_git_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == tmp_path


def test_find_repo_root_raises_when_not_found(tmp_path: Path):
    with pytest.raises(DraftWriteError) as exc_info:
        find_repo_root(tmp_path)
    assert exc_info.value.code == "repo_root_not_found"


def test_cli_end_to_end(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".active-campaign").write_text("test-campaign\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    script = Path(__file__).resolve().parents[1] / "write_draft.py"
    payload = {
        "kind": "encounter",
        "slug": "goblin-ambush",
        "title": "Goblin Ambush",
        "frontmatter": {"layout": "encounter", "title": "Goblin Ambush", "tags": []},
        "body": "Body text.",
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert out["path"] == "campaigns/test-campaign/_drafts/encounter/goblin-ambush.md"
    assert (tmp_path / out["path"]).exists()


def test_cli_no_active_campaign_exits_nonzero(tmp_path: Path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)

    script = Path(__file__).resolve().parents[1] / "write_draft.py"
    payload = {
        "kind": "encounter",
        "slug": "goblin-ambush",
        "title": "Goblin Ambush",
        "frontmatter": {},
        "body": "Body.",
    }
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "no_active_campaign"
