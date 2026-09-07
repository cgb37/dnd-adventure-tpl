# DM Orchestrator Skill (Batch Mode) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dm-orchestrator` skill (Phase 3, batch mode): a campaign memory model (`campaign.yml`) plus an outline-generation workflow and a fill-in-content workflow that invokes the existing Phase 1 generator skills, with a hard `dm`/`player` mode split so player-facing campaigns never leak spoilers into chat.

**Architecture:** Two hand-rolled, dependency-free Python scripts (`campaign_memory.py` for the YAML-like memory file, `outline_scope.py` for parsing scope phrases like "chapter 2" against the outline) live under `ai/skills/dm-orchestrator/scripts/`, following the exact pattern of `ai/skills/encounter-generator/scripts/party_state.py`. `SKILL.md` instructs Claude to read/write memory via these scripts' CLIs and to invoke the four Phase 1 generator skills directly (as if a human user asked for them) with context assembled from memory. No Phase 1/2 skill code changes.

**Tech Stack:** Python 3 stdlib only (argparse, json, pathlib, re) — no new dependencies. pytest for tests, matching every existing skill's test suite.

**Spec:** `docs/superpowers/specs/2026-09-07-dm-orchestrator-skill-design.md`

## Global Constraints

- No new third-party dependencies — stdlib only, matching every Phase 1/2 skill script.
- `campaign_memory.py` and `outline_scope.py` do not import from `shared/` or from any other skill's scripts — fully self-contained, matching `party_state.py`'s existing precedent.
- `party.yml` and every Phase 1 skill's code (`encounter_budget.py`, `party_state.py`, and the location/monster/magic-generator scripts) are never modified.
- `mode` (`dm` | `player`) is immutable once written for a campaign — enforced in `campaign_memory.py`'s write path, not just in `SKILL.md` prose.
- `content_index` entries are unique by `(beat, kind)` — a repeat write for the same key replaces, never appends — enforced in `campaign_memory.py`'s write path.
- In `player` mode, no chat response may ever contain a chapter/episode/scene title, a scene premise, or a generated draft's file path. This is the spoiler guarantee and is release-blocking (see Task 6's eval).
- `dm-orchestrator` never runs `git` inside a campaign submodule and never calls `scripts/promote-draft` itself.

---

### Task 1: `campaign_memory.py` — parse/render/read/write core

**Files:**
- Create: `ai/skills/dm-orchestrator/scripts/campaign_memory.py`
- Test: `ai/skills/dm-orchestrator/tests/test_campaign_memory.py`

**Interfaces:**
- Produces: `find_repo_root(start: Path) -> Path`; `read_campaign_memory(repo_root: Path, campaign: str) -> dict | None`; `write_campaign_memory(repo_root: Path, campaign: str, data: dict) -> Path`; `CampaignMemoryError(code: str, message: str)` (exception with `.code`/`.message` attributes, same shape as `write_draft.py`'s `DraftWriteError`).

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/dm-orchestrator/tests/test_campaign_memory.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from campaign_memory import (
    CampaignMemoryError,
    read_campaign_memory,
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_campaign_memory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'campaign_memory'` (the file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `ai/skills/dm-orchestrator/scripts/campaign_memory.py`:

```python
#!/usr/bin/env python3
"""
Read/write the per-campaign memory file (campaigns/<campaign>/campaign.yml).

This is the Phase 3 campaign memory model referenced (but not built) by
every Phase 1/2 skill spec: the campaign outline (chapters/episodes/scenes),
story threads, a running NPC registry, and an index of already-generated
content. It lives beside campaigns/<campaign>/party.yml but is a separate
file - party.yml and party_state.py are untouched by this module.

Parsing/writing is hand-rolled for this exact schema (not a general YAML
library), mirroring party_state.py's approach but generalized to handle
nested dicts and lists of dicts, since campaign.yml's outline/threads/npcs/
content_index sections need that nesting. Only the shapes documented in
docs/superpowers/specs/2026-09-07-dm-orchestrator-skill-design.md are ever
produced or parsed - this is not a general-purpose YAML implementation.

CLI usage (write subcommand added in a later change to this file):
  Read: python3 campaign_memory.py read --campaign my-campaign

Output (read, found): the full campaign.yml structure as JSON
Output (read, not found or malformed): {"found": false}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CampaignMemoryError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"No .git directory found above {start}")


def _campaign_memory_path(repo_root: Path, campaign: str) -> Path:
    return repo_root / "campaigns" / campaign / "campaign.yml"


# --- rendering (write side) -------------------------------------------------

_NON_STRING_LOOKALIKES = {
    "true", "True", "TRUE", "false", "False", "FALSE",
    "yes", "Yes", "YES", "no", "No", "NO",
    "null", "Null", "NULL", "~",
}


def _looks_like_non_string(text: str) -> bool:
    if text in _NON_STRING_LOOKALIKES:
        return True
    try:
        int(text)
        return True
    except ValueError:
        pass
    try:
        float(text)
        return True
    except ValueError:
        return False


def _render_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if (
        text == ""
        or any(ch in text for ch in [":", "#", "\n"])
        or text != text.strip()
        or _looks_like_non_string(text)
    ):
        return json.dumps(text)
    return text


def _render_list_dict_item(item: dict[str, Any], indent: int) -> list[str]:
    inner = _render_mapping(item, indent + 2)
    if not inner:
        return [f"{' ' * indent}-"]
    first, *rest = inner
    first_content = first[indent + 2:]
    return [f"{' ' * indent}- {first_content}", *rest]


def _render_mapping(data: dict[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            if not value:
                lines.append(f"{prefix}{key}: {{}}")
                continue
            lines.append(f"{prefix}{key}:")
            lines.extend(_render_mapping(value, indent + 2))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
                continue
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.extend(_render_list_dict_item(item, indent + 2))
                else:
                    lines.append(f"{' ' * (indent + 2)}- {_render_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {_render_scalar(value)}")
    return lines


# --- parsing (read side) -----------------------------------------------------

def _split_indent(line: str) -> tuple[int, str]:
    stripped = line.lstrip(" ")
    return len(line) - len(stripped), stripped


def _parse_scalar(text: str) -> Any:
    if text.startswith('"') and text.endswith('"'):
        return json.loads(text)
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "[]":
        return []
    if text == "{}":
        return {}
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _parse_mapping(lines: list[str], start: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line_indent, content = _split_indent(lines[i])
        if line_indent != indent or content.startswith("- "):
            break
        key, sep, value_part = content.partition(":")
        if not sep:
            i += 1
            continue
        value_part = value_part.strip()
        if value_part == "":
            child, next_i = _parse_block(lines, i + 1, indent + 2)
            mapping[key] = child
            i = next_i
        else:
            mapping[key] = _parse_scalar(value_part)
            i += 1
    return mapping, i


def _parse_list(lines: list[str], start: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = start
    while i < len(lines):
        line_indent, content = _split_indent(lines[i])
        if line_indent != indent or not content.startswith("- "):
            break
        rest = content[2:]
        if ":" in rest and not rest.startswith('"'):
            fake_lines = [f"{' ' * (indent + 2)}{rest}"]
            j = i + 1
            while j < len(lines):
                next_indent, _ = _split_indent(lines[j])
                if next_indent <= indent:
                    break
                fake_lines.append(lines[j])
                j += 1
            item, _ = _parse_mapping(fake_lines, 0, indent + 2)
            items.append(item)
            i = j
        else:
            items.append(_parse_scalar(rest))
            i += 1
    return items, i


def _parse_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    if start >= len(lines):
        return {}, start
    line_indent, content = _split_indent(lines[start])
    if line_indent != indent:
        return {}, start
    if content.startswith("- "):
        return _parse_list(lines, start, indent)
    return _parse_mapping(lines, start, indent)


# --- public API ---------------------------------------------------------

_REQUIRED_KEYS = {"mode", "outline"}


def read_campaign_memory(repo_root: Path, campaign: str) -> dict[str, Any] | None:
    path = _campaign_memory_path(repo_root, campaign)
    if not path.exists():
        return None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        data, _ = _parse_mapping(lines, 0, 0)
    except Exception:
        return None
    if not _REQUIRED_KEYS.issubset(data.keys()):
        return None
    return data


def _dedupe_content_index(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, Any], dict[str, Any]] = {}
    for entry in entries:
        deduped[(entry.get("beat"), entry.get("kind"))] = entry
    return list(deduped.values())


def write_campaign_memory(repo_root: Path, campaign: str, data: dict[str, Any]) -> Path:
    existing = read_campaign_memory(repo_root, campaign)
    if existing is not None and existing.get("mode") != data.get("mode"):
        raise CampaignMemoryError(
            "mode_immutable",
            f"Campaign '{campaign}' is already in '{existing.get('mode')}' mode; "
            f"cannot change to '{data.get('mode')}'. Start a new campaign for the other mode.",
        )
    data = dict(data)
    data["content_index"] = _dedupe_content_index(data.get("content_index", []))

    path = _campaign_memory_path(repo_root, campaign)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = _render_mapping(data, 0)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_campaign_memory.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/skills/dm-orchestrator/scripts/campaign_memory.py ai/skills/dm-orchestrator/tests/test_campaign_memory.py
git commit -m "$(cat <<'EOF'
feat(skills): add dm-orchestrator campaign_memory core

Hand-rolled read/write for campaigns/<campaign>/campaign.yml (outline,
threads, npcs, content_index), enforcing mode immutability and
content_index uniqueness by (beat, kind) at the script level.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `campaign_memory.py` — CLI wiring

**Files:**
- Modify: `ai/skills/dm-orchestrator/scripts/campaign_memory.py` (append CLI)
- Test: `ai/skills/dm-orchestrator/tests/test_campaign_memory.py` (append CLI tests)

**Interfaces:**
- Consumes: `read_campaign_memory`, `write_campaign_memory`, `CampaignMemoryError`, `find_repo_root` (Task 1).
- Produces: `main() -> int` CLI entry point. `read --campaign <name>` prints the structure as JSON, or `{"found": false}`. `write --campaign <name>` reads a JSON payload from stdin, writes it, and prints `{"path": "..."}` on success or `{"error": {"code": ..., "message": ...}}` (exit 1) on failure.

- [ ] **Step 1: Write the failing CLI tests**

Append to `ai/skills/dm-orchestrator/tests/test_campaign_memory.py`:

```python
import json
import subprocess
import sys

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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_campaign_memory.py -v`
Expected: the three new tests FAIL — `main`/CLI entry point isn't wired up yet (running the script does nothing on `read`/`write` subcommands because there's no `if __name__ == "__main__"` block, so the subprocess exits without emitting the expected JSON).

- [ ] **Step 3: Add the CLI**

Append to `ai/skills/dm-orchestrator/scripts/campaign_memory.py`:

```python
def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--campaign", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--campaign", required=True)

    args = parser.parse_args()
    repo_root = find_repo_root(Path.cwd())

    if args.command == "read":
        data = read_campaign_memory(repo_root, args.campaign)
        print(json.dumps(data if data is not None else {"found": False}))
        return 0

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": {"code": "invalid_input", "message": str(exc)}}))
        return 1

    try:
        path = write_campaign_memory(repo_root, args.campaign, payload)
    except CampaignMemoryError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps({"path": str(path.relative_to(repo_root))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_campaign_memory.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/skills/dm-orchestrator/scripts/campaign_memory.py ai/skills/dm-orchestrator/tests/test_campaign_memory.py
git commit -m "$(cat <<'EOF'
feat(skills): add campaign_memory CLI (read/write)

Wires read/write subcommands onto campaign_memory.py so SKILL.md can drive
campaign.yml the same way encounter-generator drives party.yml.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `outline_scope.py` — scope resolution

**Files:**
- Create: `ai/skills/dm-orchestrator/scripts/outline_scope.py`
- Test: `ai/skills/dm-orchestrator/tests/test_outline_scope.py`

**Interfaces:**
- Produces: `resolve_scope(outline: list[dict], scope_text: str) -> list[dict] | None`. Each returned scene dict is the original scene dict plus `chapter`, `episode`, and `beat` (`"CC.EE.SS"`) keys. Returns `None` when `scope_text` matches nothing in `outline`.

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/dm-orchestrator/tests/test_outline_scope.py`:

```python
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from outline_scope import resolve_scope

OUTLINE = [
    {
        "chapter": "01",
        "title": "The Festival Gates",
        "episodes": [
            {
                "episode": "01",
                "title": "Arrival",
                "scenes": [
                    {"scene": "01", "premise": "Gates seal behind them.", "needs": ["location"], "status": "filled"},
                    {"scene": "02", "premise": "A local begs for help.", "needs": ["encounter"], "status": "planned"},
                ],
            },
            {
                "episode": "02",
                "title": "The Search",
                "scenes": [
                    {"scene": "01", "premise": "Tracking the missing brother.", "needs": ["encounter"], "status": "planned"},
                ],
            },
        ],
    },
    {
        "chapter": "02",
        "title": "Into the Dark",
        "episodes": [
            {
                "episode": "01",
                "title": "Below the Festival",
                "scenes": [
                    {"scene": "01", "premise": "The cellar entrance.", "needs": ["location"], "status": "planned"},
                ],
            }
        ],
    },
]


def test_resolve_chapter_scope_returns_every_scene_in_chapter():
    matches = resolve_scope(OUTLINE, "chapter 1")
    assert [m["beat"] for m in matches] == ["01.01.01", "01.01.02", "01.02.01"]


def test_resolve_everything_in_chapter_phrasing():
    matches = resolve_scope(OUTLINE, "everything in chapter 2")
    assert [m["beat"] for m in matches] == ["02.01.01"]


def test_resolve_episode_scope():
    matches = resolve_scope(OUTLINE, "episode 1.2")
    assert [m["beat"] for m in matches] == ["01.02.01"]


def test_resolve_scene_scope():
    matches = resolve_scope(OUTLINE, "scene 01.01.02")
    assert [m["beat"] for m in matches] == ["01.01.02"]


def test_resolve_next_part_returns_first_planned_scene():
    matches = resolve_scope(OUTLINE, "the next part")
    assert [m["beat"] for m in matches] == ["01.01.02"]


def test_resolve_reports_scene_status():
    matches = resolve_scope(OUTLINE, "chapter 1")
    statuses = {m["beat"]: m["status"] for m in matches}
    assert statuses["01.01.01"] == "filled"
    assert statuses["01.01.02"] == "planned"


def test_resolve_returns_none_for_nonexistent_chapter():
    assert resolve_scope(OUTLINE, "chapter 9") is None


def test_resolve_returns_none_for_unparseable_phrase():
    assert resolve_scope(OUTLINE, "banana") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_outline_scope.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'outline_scope'`.

- [ ] **Step 3: Write the implementation**

Create `ai/skills/dm-orchestrator/scripts/outline_scope.py`:

```python
#!/usr/bin/env python3
"""
Resolve a scope phrase ("chapter 2", "episode 1.3", "the next part") against
a campaign.yml outline structure to the scene(s) it refers to.

Pure function, no file I/O - dm-orchestrator's SKILL.md reads campaign.yml
via campaign_memory.py first, then passes the resulting outline list here.

CLI usage (ad-hoc / debugging):
  echo '<outline json>' | python3 outline_scope.py "chapter 2"

Output (match): {"matches": [{"chapter": "01", "episode": "01", "scene": "02",
  "beat": "01.01.02", "premise": "...", "needs": [...], "status": "planned"}]}
Output (no match): {"matches": null}
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any


def _augment(chapter: dict[str, Any], episode: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    return {
        **scene,
        "chapter": chapter["chapter"],
        "episode": episode["episode"],
        "beat": f"{chapter['chapter']}.{episode['episode']}.{scene['scene']}",
    }


def _find_scenes(
    outline: list[dict[str, Any]],
    *,
    chapter_num: int | None = None,
    episode_num: int | None = None,
    scene_num: int | None = None,
) -> list[dict[str, Any]] | None:
    matches: list[dict[str, Any]] = []
    for chapter in outline:
        if chapter_num is not None and int(chapter["chapter"]) != chapter_num:
            continue
        for episode in chapter.get("episodes", []):
            if episode_num is not None and int(episode["episode"]) != episode_num:
                continue
            for scene in episode.get("scenes", []):
                if scene_num is not None and int(scene["scene"]) != scene_num:
                    continue
                matches.append(_augment(chapter, episode, scene))
    return matches if matches else None


def resolve_scope(outline: list[dict[str, Any]], scope_text: str) -> list[dict[str, Any]] | None:
    """Resolve a freeform scope phrase against an outline.

    Returns a list of matched scene dicts (each with 'chapter', 'episode',
    and 'beat' keys added), or None if nothing in the outline matches.
    """
    text = scope_text.strip().lower()

    if "next" in text:
        for chapter in outline:
            for episode in chapter.get("episodes", []):
                for scene in episode.get("scenes", []):
                    if scene.get("status") == "planned":
                        return [_augment(chapter, episode, scene)]
        return None

    scene_match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if scene_match:
        c, e, s = (int(x) for x in scene_match.groups())
        return _find_scenes(outline, chapter_num=c, episode_num=e, scene_num=s)

    episode_match = re.search(r"episode\s+(\d+)\.(\d+)", text) or re.fullmatch(r"(\d+)\.(\d+)", text)
    if episode_match:
        c, e = (int(x) for x in episode_match.groups())
        return _find_scenes(outline, chapter_num=c, episode_num=e)

    chapter_match = re.search(r"chapter\s+(\d+)", text)
    if chapter_match:
        c = int(chapter_match.group(1))
        return _find_scenes(outline, chapter_num=c)

    return None


def main() -> int:
    scope_text = " ".join(sys.argv[1:])
    outline = json.load(sys.stdin)
    matches = resolve_scope(outline, scope_text)
    print(json.dumps({"matches": matches}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai/skills/dm-orchestrator && python3 -m pytest tests/test_outline_scope.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/skills/dm-orchestrator/scripts/outline_scope.py ai/skills/dm-orchestrator/tests/test_outline_scope.py
git commit -m "$(cat <<'EOF'
feat(skills): add dm-orchestrator outline_scope resolver

Parses scope phrases (chapter/episode/scene, "everything in chapter N",
"the next part") against a campaign.yml outline into matched scenes,
reporting each scene's current status so fill can skip completed ones.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `references/outline-building.md`

**Files:**
- Create: `ai/skills/dm-orchestrator/references/outline-building.md`

**Interfaces:**
- Produces: guidance content consumed by `SKILL.md`'s outline-design step (Task 5). No code interface.

- [ ] **Step 1: Write the reference file**

Create `ai/skills/dm-orchestrator/references/outline-building.md`:

```markdown
# Outline Building Guidance

Guidance for turning a premise + scope into a chapter/episode/scene outline.
This is judgement, not arithmetic — use it the way `encounter-building.md`
is used for encounter design: as grounding, not a rigid formula.

## Sizing from scope

Map the user's stated scope to a structure. As a starting point:

| Scope phrase | Chapters | Episodes/chapter | Scenes/episode |
|---|---|---|---|
| "short" / "one-shot" | 1 | 1-2 | 2-3 |
| "3 chapters, short" | 3 | 2 | 2-3 |
| "a full campaign" / unspecified length | 4-6 | 2-3 | 3-4 |

These are starting points, not caps — adjust for how much the premise
itself implies (a premise naming three distinct locations probably wants
at least three episodes to visit them).

## Pacing

- **Plant early, pay off late.** Every thread in `threads` should be
  introduced in the first third of the outline and either advance or
  resolve by the final chapter. An outline with threads that never move is
  a worse outline than a shorter one where every thread matters.
- **Escalate.** Later chapters should raise stakes relative to earlier
  ones — a bigger threat, a more personal cost, a harder choice. Don't
  repeat the same shape of scene (e.g. "another ambush") without variation
  in tone or consequence.
- **Vary `needs`.** Don't tag every scene `[encounter]`. A good outline
  mixes exploration/investigation scenes (`[location]`), combat
  (`[encounter]`), reward moments (`[magic]`), and monster-forward scenes
  where a specific creature drives the plot (`[monster]`). A scene can need
  more than one — e.g. `[location, encounter]` for a fight that happens in
  a place worth describing in its own right.

## Tagging `needs` from a premise

Infer tags from what the scene's one-line premise actually implies:

- Combat, ambush, "fight," "guarded by," "attacks" → `encounter`
- A place to explore, arrive at, or describe (a room, ruin, town, road) →
  `location`
- A specific named or important creature drives the scene (a boss, a
  unique monster, a CR-notable threat introduced by name) → `monster`
- A reward, artifact, or magic item is found or given → `magic`

A scene with no clear generator need (a pure roleplay/dialogue beat, e.g.
"the party negotiates with the mayor") can have `needs: []` — not every
scene requires generated content, and `dm-orchestrator`'s fill workflow
simply has nothing to do for such a scene (it's immediately `filled` since
an empty `needs` list is vacuously satisfied).

## Level appropriateness

Read the resolved party level (from `party_state.py`) before designing the
outline. Scenes tagged `encounter` or `monster` should assume a party at
roughly that level for the first chapter, escalating by no more than 2-3
levels by the outline's final chapter, consistent with the CR/level
judgement already used by `encounter-generator` and `monster-generator`.
Don't hand off a level-1-appropriate premise to a level-12 party's outline
without acknowledging the mismatch.
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-orchestrator/references/outline-building.md
git commit -m "$(cat <<'EOF'
docs(skills): add dm-orchestrator outline-building reference

Pacing/sizing guidance and needs-tagging heuristics for the outline
workflow, mirroring encounter-generator's references/ convention.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `SKILL.md`

**Files:**
- Create: `ai/skills/dm-orchestrator/SKILL.md`

**Interfaces:**
- Consumes: `scripts/campaign_memory.py` (`read`/`write` CLI, Tasks 1-2), `scripts/outline_scope.py` (CLI, Task 3), `references/outline-building.md` (Task 4), the existing `ai/skills/encounter-generator/scripts/party_state.py` `read`/`write` CLI (unchanged), and the four Phase 1 skills (`encounter-generator`, `location-generator`, `monster-generator`, `magic-generator`) invoked as skills.
- Produces: the `dm-orchestrator` skill itself — no code interface, this is the file other tasks (evals, Task 6) validate against.

- [ ] **Step 1: Write the skill file**

Create `ai/skills/dm-orchestrator/SKILL.md`:

```markdown
---
name: dm-orchestrator
description: Generate and maintain a D&D 5e campaign outline (chapters/episodes/scenes), and fill in that outline's content by invoking the encounter-generator, location-generator, monster-generator, and magic-generator skills. Use this skill whenever someone wants to start a new campaign, plan out a campaign's structure, or asks to "generate chapter 2," "fill in the next part," or "get my campaign ready to play." Distinguishes DM users (who see and approve the outline and generated content) from player users (who must get zero spoilers - no outline, scene, or draft details are ever shown in chat). This is Phase 3 "batch mode"; live turn-by-turn session delivery is a separate future skill (dm-livesession).
---

# DM Orchestrator (Batch Mode)

Maintain a campaign's outline and generated content by orchestrating the
Phase 1 generator skills. This skill never generates encounter, location,
monster, or magic-item content itself — it invokes those skills the same
way a human user would ask for them, supplying richer narrative context
than a human typically would.

## Read This First: Mode Rules

Every campaign has a `mode`, set once at outline creation and fixed for the
campaign's lifetime:

- **`dm`** — the user is running this campaign for others. Show the full
  outline, ask for approval/edits, and report exactly what was generated
  (titles, kinds, draft paths) after every fill request.
- **`player`** — the user will experience this campaign themselves, later,
  through the `dm-livesession` skill. **Never show outline content, scene
  premises, chapter/episode/scene titles, or draft file paths in chat under
  any circumstances in this mode.** Responses are limited to confirmations
  and counts (e.g. "Your campaign is ready," "2 scenes generated, 1 already
  ready"). If you catch yourself about to describe what a scene is about in
  `player` mode, stop — that is a spoiler.

Never allow a user to change an existing campaign's `mode`.
`scripts/campaign_memory.py`'s write path enforces this and returns a
`mode_immutable` error if you try — relay that error rather than working
around it.

## Workflow 1: Generate an Outline

Triggered by requests like "start a new campaign about a cursed harvest
festival, 3 chapters" or "generate a campaign for me to play, 1 chapter."

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If missing or empty, stop and
tell the user to run `scripts/use-campaign <name>` first — don't guess.
`dm-orchestrator` never creates a campaign; campaign submodules are added
to `.gitmodules` and checked out entirely outside this skill's scope.

### Step 2: Check for an existing outline

Run:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns a structure with a non-empty `outline` (not `{"found":
false}`), stop. Tell the user a campaign already exists (name its premise)
and ask whether to replace it or use a different campaign. Never overwrite
silently.

### Step 3: Resolve mode

Infer from phrasing: "I'm running this for my group" → `dm`; "generate a
campaign for me to play" → `player`. Ask directly only if genuinely
ambiguous: "Are you running this campaign as the DM, or is this for you to
play through yourself?"

### Step 4: Resolve party context

Run the existing party-state script (unchanged, shared with
`encounter-generator`):

```bash
python3 <repo-root>/ai/skills/encounter-generator/scripts/party_state.py read --campaign <active-campaign>
```

If missing, ask once for level/size/composition and write it via that same
script's `write` subcommand, exactly as `encounter-generator` does.

### Step 5: Resolve premise and scope

Take both directly from what the user already said. Only ask if either is
genuinely absent (e.g. a bare "start a new campaign").

### Step 6: Design the outline

Read `references/outline-building.md` for sizing, pacing, and `needs`-
tagging guidance. Produce chapters → episodes → scenes. Every scene gets a
one-line `premise` and a `needs` list (`location`, `encounter`, `monster`,
`magic`, any combination, or `[]`) inferred from that premise. Every scene
starts with `status: planned`. Seed `threads` with any hooks the outline
introduces. Leave `npcs` and `content_index` empty — nothing has been
generated yet.

### Step 7: Write to memory

Build the full structure (`mode`, `premise`, `scope`, `outline`, `threads`,
`npcs: []`, `content_index: []`) and write it:

```bash
echo '<json payload>' | python3 <skill-path>/scripts/campaign_memory.py write --campaign <active-campaign>
```

On a `mode_immutable` error, relay it directly — this shouldn't happen in
this workflow (Step 2 already checked for an existing outline), so treat it
as a signal something changed concurrently and re-read before retrying.

### Step 8: Report to the user (mode-gated)

- **`dm`**: show the outline — every chapter/episode/scene title and
  one-line premise, in order — as readable prose or a nested list, not raw
  YAML. Say the user can ask for edits, or ask `dm-orchestrator` to fill in
  any chapter/episode once they're happy.
- **`player`**: show nothing about the outline's content. Respond only:
  "Your campaign is ready. dm-livesession will guide you through it — no
  spoilers here." There is no edit loop in this mode.

## Workflow 2: Fill In Content

Triggered by requests like "generate chapter 2," "fill in episode 1.3," or
(in `player` mode) "get the next part ready."

### Step 1: Resolve active campaign and read memory

Same active-campaign resolution as Workflow 1, Step 1. Then:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate an outline first.

### Step 2: Resolve scope

Pass the outline and the user's scope phrase to the resolver:

```bash
echo '<outline json>' | python3 <skill-path>/scripts/outline_scope.py "<scope phrase>"
```

If `matches` is `null`, the scope didn't match anything in the outline.
This is the one place fill asks a clarifying question in **both** modes —
naming which chapters/episodes exist doesn't spoil anything. In `dm` mode,
list the valid chapters/episodes; in `player` mode, say "that part doesn't
exist yet" without listing titles.

### Step 3: Filter already-filled scenes

For each matched scene, check `content_index` for a row matching
`(beat, kind)` for every entry in that scene's `needs`. If every `needs`
entry (including an empty list) is already covered, skip the scene. Track
how many were skipped.

### Step 4: Generate remaining scenes

For each remaining scene, for each tag in its `needs` list:

1. Build inline narrative context from memory: the scene's own `premise`,
   every thread in `threads` with `status` `introduced` or `advancing`, and
   every NPC in `npcs` whose `last_seen` is at or before this scene's
   chapter.
2. Invoke the matching skill with that context plus the resolved party
   info, as if a user had asked for it directly but with this richer
   detail supplied:
   - `needs` entry `encounter` → invoke `encounter-generator`
   - `needs` entry `location` → invoke `location-generator`
   - `needs` entry `monster` → invoke `monster-generator`
   - `needs` entry `magic` → invoke `magic-generator`
3. **Immediately after that invocation succeeds** (before moving to the
   next `needs` entry or scene): record a `content_index` row (`beat`,
   `kind`, `slug`, `path` — read the path from the invoked skill's
   response), update the scene's `status` to `filled` if every `needs`
   entry for it is now covered, best-effort update `npcs`/`threads` if the
   generated content plausibly introduces a new named NPC or advances/
   resolves a thread, and write memory back:

   ```bash
   echo '<updated campaign.yml json>' | python3 <skill-path>/scripts/campaign_memory.py write --campaign <active-campaign>
   ```

   Writing after every successful generation (not once at the end of the
   whole fill request) means a later failure in the same batch never
   leaves memory behind what's actually on disk.
4. If an invocation fails, do not record a `content_index` row for it, do
   not abort the rest of the batch, and note the failure for the final
   report.

### Step 5: Report to the user (mode-gated)

- **`dm`**: list every scene generated (title, kind, draft path), every
  scene skipped (named, "already generated"), and every scene that failed
  (named, with why). This is the DM's review list before running
  `scripts/promote-draft` on anything they like.
- **`player`**: counts only — "X generated, Y already ready, Z couldn't be
  generated." No titles, premises, or paths, ever.

Never call `scripts/promote-draft` yourself, and never run `git` inside the
campaign submodule — drafts are left for the user to review and promote,
exactly as every Phase 1 skill already behaves.

## Error Handling

- No active campaign → stop, tell the user to run `scripts/use-campaign`
  first. Never guess a campaign.
- Outline already exists (Workflow 1) → stop, confirm before replacing.
- No outline yet (Workflow 2) → stop, tell the user to generate one first.
- Scope matches nothing (Workflow 2) → ask a clarifying question — the only
  question fill ever asks in `player` mode.
- A Phase 1 skill invocation fails for one scene → skip it, continue the
  rest of the batch, report the failure at the end.
- `campaign_memory.py` reports an error (`mode_immutable`,
  `invalid_input`) → relay it directly. Never guess a fix or silently
  retry.

## Tips for Good Output

- **The spoiler rule is absolute, not a suggestion.** A `player`-mode
  response that leaks even one scene title has failed regardless of how
  good the generated content is.
- **Context injection is what makes filled scenes feel connected**, not
  generic. A generic-sounding encounter is a sign you didn't actually pull
  the relevant threads/NPCs from memory before invoking
  `encounter-generator`.
- **An outline is a plan, not a commitment.** In `dm` mode, treat outline
  edit requests as normal — rewrite the affected part of the structure and
  write it back, same as Workflow 1.
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-orchestrator/SKILL.md
git commit -m "$(cat <<'EOF'
feat(skills): add dm-orchestrator SKILL.md

Outline-generation and fill-in-content workflows orchestrating the four
Phase 1 generator skills via campaign.yml, with a dm/player mode split
enforcing the no-spoilers guarantee for player-facing campaigns.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `evals/evals.json`

**Files:**
- Create: `ai/skills/dm-orchestrator/evals/evals.json`

**Interfaces:**
- Consumes: the workflows described in `SKILL.md` (Task 5).
- Produces: eval scenarios validated in Task 7's parse check, matching the shape of `ai/skills/encounter-generator/evals/evals.json` (`skill_name`, `evals: [{id, prompt, expected_output, files, assertions}]`).

- [ ] **Step 1: Write the evals file**

Create `ai/skills/dm-orchestrator/evals/evals.json`:

```json
{
  "skill_name": "dm-orchestrator",
  "evals": [
    {
      "id": 0,
      "prompt": "I'm running a campaign for my group about a cursed harvest festival in a town that seals its gates at night. Give me 3 chapters.",
      "expected_output": "campaign.yml is written with mode=dm, the given premise, a 3-chapter outline (episodes and scenes each with a premise and needs tags), threads seeded from the premise, and empty npcs/content_index. The full outline (chapter/episode/scene titles and premises) is shown in chat, and the user is told they can request edits or ask to fill in a chapter.",
      "files": [],
      "assertions": [
        {"name": "mode_dm", "description": "campaign.yml's mode field is 'dm'"},
        {"name": "outline_written", "description": "campaign.yml has a non-empty outline with 3 chapters"},
        {"name": "outline_shown", "description": "The chat response includes chapter/episode/scene titles and premises"},
        {"name": "party_resolved", "description": "party_state.py was read (and written if missing) before the outline was designed"}
      ]
    },
    {
      "id": 1,
      "prompt": "Generate a campaign for me to play through myself, one chapter, about smugglers in a coastal town.",
      "expected_output": "campaign.yml is written with mode=player and a 1-chapter outline. The chat response contains no chapter/episode/scene titles, no premises, and no outline details of any kind — only a short confirmation that the campaign is ready and that dm-livesession will guide the user through it.",
      "files": [],
      "assertions": [
        {"name": "mode_player", "description": "campaign.yml's mode field is 'player'"},
        {"name": "no_spoilers", "description": "The chat response contains none of the outline's chapter/episode/scene titles or scene premise text"},
        {"name": "confirmation_only", "description": "The chat response is a short readiness confirmation, not a description of the campaign's content"}
      ]
    },
    {
      "id": 2,
      "prompt": "Fill in chapter 2.",
      "expected_output": "Given an existing dm-mode campaign with a chapter 2 whose scenes are tagged needs: [location] and needs: [encounter], both scenes are generated by invoking location-generator and encounter-generator respectively, with context drawn from campaign.yml's threads/npcs. campaign.yml's content_index gains one row per generated scene, matching scenes' status becomes 'filled', and the chat response lists each generated scene's title, kind, and draft path.",
      "files": [],
      "assertions": [
        {"name": "correct_skills_invoked", "description": "location-generator was invoked for the location-tagged scene and encounter-generator for the encounter-tagged scene, not the other way around"},
        {"name": "content_index_updated", "description": "campaign.yml's content_index has a new row per generated scene, and affected scenes' status is 'filled'"},
        {"name": "context_injected", "description": "The generator invocations included narrative context (threads/npcs) drawn from campaign.yml, not just the bare scene premise"},
        {"name": "dm_report_detailed", "description": "The chat response names each generated scene's title, kind, and draft path"}
      ]
    },
    {
      "id": 3,
      "prompt": "Fill in chapter 1.",
      "expected_output": "Given a dm-mode campaign where every scene in chapter 1 already has a matching content_index entry, no generator skill is invoked, no new content_index rows are added, and the chat response reports that chapter 1's scenes are already generated (naming them, since mode is dm) rather than regenerating anything.",
      "files": [],
      "assertions": [
        {"name": "no_regeneration", "description": "No Phase 1 skill was invoked and content_index is unchanged"},
        {"name": "skip_reported", "description": "The chat response states the scenes were already generated"}
      ]
    },
    {
      "id": 4,
      "prompt": "Fill in chapter 9.",
      "expected_output": "Given a campaign whose outline only has 3 chapters, dm-orchestrator does not invoke any generator skill and instead asks a clarifying question about which chapter was meant. In dm mode this names the chapters that do exist (01-03); the response does not fabricate a chapter 9.",
      "files": [],
      "assertions": [
        {"name": "no_fabrication", "description": "No content is generated and no content_index row is added for a nonexistent chapter 9"},
        {"name": "clarifying_question_asked", "description": "The response asks which chapter was meant rather than silently failing or guessing"}
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate it parses**

Run: `python3 -c "import json; d = json.load(open('ai/skills/dm-orchestrator/evals/evals.json')); assert d['skill_name'] == 'dm-orchestrator'; assert len(d['evals']) >= 3; print('OK', len(d['evals']), 'evals')"`
Expected: `OK 5 evals`.

- [ ] **Step 3: Commit**

```bash
git add ai/skills/dm-orchestrator/evals/evals.json
git commit -m "$(cat <<'EOF'
test(skills): add dm-orchestrator evals

Covers dm-mode outline generation, player-mode no-spoilers guarantee,
fill invoking the correct Phase 1 skills with injected context, skip
behavior for already-filled scenes, and clarifying-question behavior for
an out-of-range scope.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Full verification pass

Run every affected test suite together to confirm nothing regressed.

**Files:** none (verification only).

**Interfaces:** none.

- [ ] **Step 1: Run the new skill's test suite**

```bash
cd ai/skills/dm-orchestrator && python3 -m pytest tests/ -v
```

Expected: all 18 tests pass (10 from `test_campaign_memory.py` + 8 from `test_outline_scope.py`).

- [ ] **Step 2: Run the existing skill test suites (regression check)**

```bash
cd ai/skills/encounter-generator && python3 -m pytest tests/ -v
cd ../monster-generator && python3 -m pytest tests/ -v
cd ../magic-generator && python3 -m pytest tests/ -v
```

Expected: all pre-existing tests still pass — nothing in this plan touched `party_state.py`, `encounter_budget.py`, or any Phase 1 skill's scripts.

- [ ] **Step 3: Run the shared module test suite (regression check)**

```bash
python3 -m pytest shared/tests/ -v
```

Expected: all pre-existing tests still pass — `shared/` was never touched.

- [ ] **Step 4: Validate the evals file one more time in place**

```bash
python3 -c "
import json
data = json.load(open('ai/skills/dm-orchestrator/evals/evals.json'))
assert data['skill_name'] == 'dm-orchestrator'
assert len(data['evals']) >= 3
print(f'OK ({len(data[\"evals\"])} evals)')
"
```

Expected: `OK (5 evals)`, no assertion errors.

No commit for this task — it's a verification-only pass over work already committed in Tasks 1-6. If any step fails, fix the regression in the task that introduced it and re-run this task's steps from the top.
