# DM Livesession Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dm-livesession` skill (Phase 4): a solo-player turn-by-turn narration loop with a spoiler guarantee, plus a stateless DM co-pilot lookup/dice-roll workflow, both built on top of `dm-orchestrator`'s existing `campaign.yml` memory model.

**Architecture:** One skill, two mode-gated workflows sharing a single `SKILL.md`, exactly mirroring how `dm-orchestrator` branches on `campaign.yml`'s `mode`. Player mode owns a new hand-rolled-YAML file, `session.yml` (bookmark + recap log), written via a new `session_state.py` script that duplicates `campaign_memory.py`'s parse/render core rather than importing it (matching every existing skill script's self-containment). DM mode is stateless: it reads `campaign.yml`/`content_index`/generated drafts directly and never writes anything. Neither workflow calls the Phase 1 generator skills directly — content generation always goes through `dm-orchestrator`'s existing fill workflow, invoked as a skill exactly as a human user would. A new `dice.py` script (general `NdM+K` notation, not the ability-score-only `shared/dice_roller.py`) backs the DM co-pilot's ad-hoc roll requests.

**Tech Stack:** Python 3 stdlib only (argparse, json, pathlib, re, random) — no new dependencies. pytest for tests, matching every existing skill's test suite.

**Spec:** `docs/superpowers/specs/2026-09-07-dm-livesession-skill-design.md`

## Global Constraints

- No new third-party dependencies — stdlib only, matching every existing skill script.
- `session_state.py` and `dice.py` do not import from `shared/`, from `dm-orchestrator`'s scripts, or from any other skill's scripts — fully self-contained. `session_state.py` duplicates `campaign_memory.py`'s hand-rolled YAML parse/render functions rather than importing them, matching that file's own precedent of duplicating `write_draft.py`'s indicator-prefix logic rather than importing it.
- `campaign.yml`'s schema is never changed, and no file under `ai/skills/dm-orchestrator/` is ever modified by this plan. `dm-livesession` reads `campaign.yml` via `dm-orchestrator`'s existing `campaign_memory.py` and `outline_scope.py` CLIs, invoked cross-skill by full path — the same pattern `dm-orchestrator` itself already uses to reuse `encounter-generator`'s `party_state.py`.
- `dm-livesession` never invokes `encounter-generator`, `location-generator`, `monster-generator`, or `magic-generator` directly. All content generation goes through `dm-orchestrator`'s fill workflow, invoked as a skill (a natural-language request like "fill in scene 01.01.02"), never bypassed.
- Player-mode spoiler guarantee: no chat response may ever reveal a beat beyond `session.yml`'s `current_position` — no title, premise, or `needs` tag for a future scene. This is release-blocking (see Task 5's eval).
- `session.yml` exists and is written only for `mode: player` campaigns. `mode: dm` campaigns never have a `session.yml` written or read.
- No structured combat tracker. `dice.py` rolls are stateless single-expression calculator calls — no initiative order, HP, or condition state is persisted anywhere.
- Off-script player actions never trigger a `dm-orchestrator` outline edit and never advance `session.yml`'s `current_position` — improvisation is narrative-only until play resolves back onto a planned beat.

---

### Task 1: `session_state.py` — parse/render/read/write core

**Files:**
- Create: `ai/skills/dm-livesession/scripts/session_state.py`
- Test: `ai/skills/dm-livesession/tests/test_session_state.py`

**Interfaces:**
- Produces: `find_repo_root(start: Path) -> Path`; `SessionStateError(code: str, message: str)` (exception with `.code`/`.message`, same shape as `campaign_memory.py`'s `CampaignMemoryError`); `read_session_state(repo_root: Path, campaign: str) -> dict | None`; `write_session_state(repo_root: Path, campaign: str, updates: dict) -> Path`.

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/dm-livesession/tests/test_session_state.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai/skills/dm-livesession && python3 -m pytest tests/test_session_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'session_state'` (the file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `ai/skills/dm-livesession/scripts/session_state.py`:

```python
#!/usr/bin/env python3
"""
Read/write the per-campaign live-session bookmark (campaigns/<campaign>/session.yml).

Owned exclusively by dm-livesession's player-session workflow. campaign.yml
stays dm-orchestrator's file and is never written here. session.yml is
deliberately small: a single position bookmark, a short recap log, and the
set of beats actually played live - distinct from campaign.yml's
`status: filled`, which only means content was generated, not played.

Parsing/writing is hand-rolled for this exact schema, duplicating
ai/skills/dm-orchestrator/scripts/campaign_memory.py's parse/render
approach rather than importing it - skill scripts stay fully
self-contained, matching party_state.py's precedent.

CLI usage:
  Read:  python3 session_state.py read --campaign my-campaign
  Write: echo '<json>' | python3 session_state.py write --campaign my-campaign

Read output (found): {"current_position": {...}, "event_log": [...], "delivered_beats": [...]}
Read output (no session yet): {"found": false} - not an error; this is every
  campaign's state before its first live session.
Read output (unparseable): {"error": {"code": "invalid_session_state", ...}},
  exit code 1 - a corrupt file is never confused with a missing one, and is
  never guess-repaired.

Write input is a set of *updates*, not the full desired file - `write`
merges into whatever already exists:
  - "current_position" (object, optional): replaces the stored position.
  - "event_log" (array of objects, optional): entries to APPEND to the
    existing log, in the order given.
  - "delivered_beats" (array of strings, optional): beats to APPEND to the
    existing set - a beat already present is not duplicated.
A key left out of the payload leaves that part of the file unchanged. This
lets each turn make one write call with only what changed, without ever
re-transmitting the whole session history.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SessionStateError(Exception):
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


def _session_state_path(repo_root: Path, campaign: str) -> Path:
    return repo_root / "campaigns" / campaign / "session.yml"


# --- rendering (write side) -------------------------------------------------
# Duplicated from campaign_memory.py rather than imported - see module docstring.

_NON_STRING_LOOKALIKES = {
    "true", "True", "TRUE", "false", "False", "FALSE",
    "yes", "Yes", "YES", "no", "No", "NO",
    "null", "Null", "NULL", "~",
}

_INDICATOR_PREFIXES = ('"', "*", "&", "!", "|", ">", "%", "@", "`", "[", "{")


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
        pass
    if text == "-" or text.startswith("- "):
        return True
    return text.startswith(_INDICATOR_PREFIXES)


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
    if len(text) > 1 and text.startswith('"') and text.endswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
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

def read_session_state(repo_root: Path, campaign: str) -> dict[str, Any] | None:
    """Read session.yml.

    Returns None when there is simply no session yet (the file doesn't
    exist) - every campaign starts here, before its first live session.
    Raises SessionStateError('invalid_session_state') when the file exists
    but cannot be parsed - a corrupt file must never be mistaken for "no
    session yet," or a later write would silently discard whatever it held.
    """
    path = _session_state_path(repo_root, campaign)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if line.strip()]
        data, _ = _parse_mapping(lines, 0, 0)
    except Exception as exc:
        raise SessionStateError(
            "invalid_session_state",
            f"Session state at {path} exists but could not be read: "
            f"{type(exc).__name__}: {exc}. Repair or remove the file by hand - "
            f"dm-livesession will not guess-repair or overwrite it.",
        ) from exc
    return {
        "current_position": data.get("current_position", {}),
        "event_log": data.get("event_log", []),
        "delivered_beats": data.get("delivered_beats", []),
    }


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def write_session_state(repo_root: Path, campaign: str, updates: dict[str, Any]) -> Path:
    """Merge `updates` into the existing session.yml (or a fresh one) and write it.

    See the module docstring for exactly how each key merges. A
    SessionStateError from the read below is deliberately not caught: if
    the existing file is unreadable, this must refuse to write over it
    rather than silently replacing lost data with a fresh, mostly-empty
    file.
    """
    existing = read_session_state(repo_root, campaign) or {
        "current_position": {},
        "event_log": [],
        "delivered_beats": [],
    }

    if "current_position" in updates:
        existing["current_position"] = updates["current_position"]
    if "event_log" in updates:
        existing["event_log"] = [*existing["event_log"], *updates["event_log"]]
    if "delivered_beats" in updates:
        existing["delivered_beats"] = _dedupe_preserve_order(
            [*existing["delivered_beats"], *updates["delivered_beats"]]
        )

    path = _session_state_path(repo_root, campaign)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = _render_mapping(existing, 0)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
        try:
            data = read_session_state(repo_root, args.campaign)
        except SessionStateError as exc:
            print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
            return 1
        if data is None:
            print(json.dumps({"found": False}))
            return 0
        print(json.dumps(data))
        return 0

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": {"code": "invalid_input", "message": str(exc)}}))
        return 1

    try:
        path = write_session_state(repo_root, args.campaign, payload)
    except SessionStateError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps({"path": str(path.relative_to(repo_root))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai/skills/dm-livesession && python3 -m pytest tests/test_session_state.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/skills/dm-livesession/scripts/session_state.py ai/skills/dm-livesession/tests/test_session_state.py
git commit -m "$(cat <<'EOF'
feat(skills): add dm-livesession session_state core

session.yml is dm-livesession's own bookmark + recap log for player-mode
live sessions, kept separate from dm-orchestrator's campaign.yml. Parsing
duplicates campaign_memory.py's hand-rolled YAML approach rather than
importing it, matching every existing skill script's self-containment.
write merges updates (append event_log, dedupe-append delivered_beats,
replace current_position) rather than requiring the full history each call.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `dice.py` — general dice-notation roller

**Files:**
- Create: `ai/skills/dm-livesession/scripts/dice.py`
- Test: `ai/skills/dm-livesession/tests/test_dice.py`

**Interfaces:**
- Produces: `DiceNotationError(message: str)` (exception with `.message`); `roll(notation: str, rng: random.Random) -> dict` returning `{"notation": str, "rolls": list[int], "modifier": int, "total": int}`.
- Consumes: nothing from Task 1 — independent of `session_state.py`.

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/dm-livesession/tests/test_dice.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai/skills/dm-livesession && python3 -m pytest tests/test_dice.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dice'`.

- [ ] **Step 3: Write the implementation**

Create `ai/skills/dm-livesession/scripts/dice.py`:

```python
#!/usr/bin/env python3
"""
General dice-notation roller ("1d20+3", "2d6", "1d8-2") for ad-hoc DM
co-pilot rolls (initiative, damage, skill checks) during a live session.

Distinct from shared/dice_roller.py, which only generates D&D 5e ability
scores (4d6-drop-lowest / standard array / point buy) and has no general
NdM+K notation support - that module is not reused here because it cannot
do this job.

CLI usage:
  python3 dice.py "1d20+3"
  python3 dice.py "2d6" --seed 42

Output (success): {"notation": "1d20+3", "rolls": [14], "modifier": 3, "total": 17}
Output (invalid notation): {"error": {"code": "invalid_dice_notation", "message": "..."}},
  exit code 1 - never guesses at a malformed request.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from typing import Any

_NOTATION_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


class DiceNotationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def roll(notation: str, rng: random.Random) -> dict[str, Any]:
    """Roll a single dice-notation expression like '2d6+3'.

    Raises DiceNotationError on anything that isn't `count`d`sides`
    optionally followed by a +/- modifier (e.g. 'd20', '1d6x2', 'banana'
    all raise), or on a structurally nonsensical count/sides (0 dice, a
    1-sided die, more than 100 dice) - never guesses at what was meant.
    """
    match = _NOTATION_RE.match(notation.strip().replace(" ", ""))
    if not match:
        raise DiceNotationError(
            f"'{notation}' is not valid dice notation (expected e.g. '1d20+3', '2d6')"
        )
    count_text, sides_text, modifier_text = match.groups()
    count = int(count_text)
    sides = int(sides_text)
    modifier = int(modifier_text) if modifier_text else 0
    if count < 1 or count > 100:
        raise DiceNotationError(f"dice count must be 1-100, got {count}")
    if sides < 2:
        raise DiceNotationError(f"dice sides must be 2 or more, got {sides}")
    rolls = [rng.randint(1, sides) for _ in range(count)]
    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": sum(rolls) + modifier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notation", help="Dice notation, e.g. '1d20+3'")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible rolls")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    try:
        result = roll(args.notation, rng)
    except DiceNotationError as exc:
        print(json.dumps({"error": {"code": "invalid_dice_notation", "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai/skills/dm-livesession && python3 -m pytest tests/test_dice.py -v`
Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai/skills/dm-livesession/scripts/dice.py ai/skills/dm-livesession/tests/test_dice.py
git commit -m "$(cat <<'EOF'
feat(skills): add dm-livesession general dice-notation roller

shared/dice_roller.py only generates ability scores and has no NdM+K
notation support, so the DM co-pilot workflow's ad-hoc rolls (initiative,
damage, skill checks) need their own small roller instead.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `references/live-narration.md`

**Files:**
- Create: `ai/skills/dm-livesession/references/live-narration.md`

**Interfaces:**
- Consumes: nothing (pure guidance document).
- Produces: guidance `SKILL.md` (Task 4) points to for narration judgement.

- [ ] **Step 1: Write the reference file**

Create `ai/skills/dm-livesession/references/live-narration.md`:

```markdown
# Live Narration Guidance

Judgement guidance for narrating a player-mode scene turn-by-turn, the way
`references/outline-building.md` grounds `dm-orchestrator`'s outline
design. Used only in Workflow 1 (Player Session) - the DM co-pilot
workflow narrates nothing; it answers queries directly.

## The one rule everything else serves

Never narrate, hint at, or answer a question about anything beyond
`session.yml`'s `current_position`. Not a future scene's title, not its
premise, not which NPCs appear in it, not how many scenes remain in the
chapter. If a player asks something that would require peeking ahead
("are we near the end of this chapter?"), answer only in terms of what
they've already experienced ("you don't know yet - you'll find out as you
go"), never with real numbers from the outline.

## Turning generated content into narration

The current beat's generated draft(s) (location/encounter/monster/magic,
per its `needs`) are structured reference material, not narration text.
Read them for facts - what's in the room, what the creature's stat block
implies about how it fights, what the item does - then narrate in second
person, present tense, as a DM speaking to a player: sensory detail first,
mechanical facts folded in only as the fiction reveals them (a monster's
resistance is discovered through a blow that does less than expected, not
announced as a stat line).

## Story hooks

A hook is planted, not delivered as a summary. If a scene's `needs`
included content whose thread ties to something in `campaign.yml`'s
`threads`, surface it through action or dialogue the player can choose to
pursue or ignore - a nervous glance, a half-finished sentence, an object
that doesn't belong. Never say "this seems important" out loud; let the
detail's placement do that work.

## Puzzles

Give the puzzle's shape and its stakes up front, then let solutions come
from the player's stated actions - never solve it for them, and never
reject a creative approach the puzzle's premise doesn't actually rule out.
When a player is stuck, escalate hints gradually across turns (a stronger
sensory detail, then an NPC's suggestion, then a direct clue) rather than
either stonewalling or handing over the answer on the first ask.

## NPC agendas and unreliable narration

`campaign.yml`'s `npcs` entries carry only `role` and `disposition` -
there is no persisted `agenda` field, deliberately (see the design spec).
Infer an NPC's motive live, each time they appear, from those two fields
plus the current scene's premise, and stay consistent with what you
inferred earlier in the same session (check `session.yml`'s `event_log`
for how this NPC was already played before contradicting yourself).

An NPC can be an unreliable narrator - stating something false or
incomplete because of their own agenda, not because you're hiding
information from the player. The player should always be able to tell
*that* an NPC said something (verifiable, actionable), even when *what*
they said turns out to be wrong. Never have the narration itself (as
opposed to a character within it) state something false - the fourth wall
between "the DM's factual description" and "what this liar just claimed"
must stay intact.

## Off-script play

When a player does something the outline didn't anticipate, improvise the
immediate consequence using the same principles above (hooks, NPC
consistency, no future-beat leakage) - the outline being silent on this
exact action is not license to describe something that spoils a later
beat instead. Do not tell the player they've gone "off script." Resolve
the moment in-world and let the story continue; `SKILL.md` handles when
(and whether) `session.yml` advances as a result.
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-livesession/references/live-narration.md
git commit -m "$(cat <<'EOF'
docs(skills): add dm-livesession narration guidance

Judgement guidance for turn-by-turn narration: the spoiler boundary,
turning generated drafts into narration, planting hooks, pacing puzzle
hints, inferring NPC agenda/unreliable-narrator texture live from
role/disposition (no new campaign.yml fields), and handling off-script
play without breaking the fourth wall or leaking future beats.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `SKILL.md`

**Files:**
- Create: `ai/skills/dm-livesession/SKILL.md`

**Interfaces:**
- Consumes: `scripts/session_state.py` (`read`/`write` CLI, Task 1), `scripts/dice.py` (CLI, Task 2), `references/live-narration.md` (Task 3), `ai/skills/dm-orchestrator/scripts/campaign_memory.py` (`read [--redact]`/`write` CLI, unchanged, invoked cross-skill by path), `ai/skills/dm-orchestrator/scripts/outline_scope.py` (CLI, unchanged, invoked cross-skill by path), the `dm-orchestrator` skill itself (invoked for fills), and `shared/dnd5eapi_client.py` (CLI, unchanged, for ad-hoc rules/monster lookups in DM co-pilot mode).
- Produces: the `dm-livesession` skill itself — no code interface; other tasks (evals, Task 6) validate against it.

- [ ] **Step 1: Write the skill file**

Create `ai/skills/dm-livesession/SKILL.md`:

```markdown
---
name: dm-livesession
description: Run a live D&D 5e session turn-by-turn on top of an existing dm-orchestrator campaign. In a player-mode campaign, narrate scenes and react to the solo player's actions with a strict spoiler guarantee - nothing beyond the current bookmarked position is ever revealed. In a dm-mode campaign, act as a stateless co-pilot for a human DM running a live session for other players - answer "what's next," NPC lookups, content lookups, and ad-hoc dice rolls (initiative, damage, skill checks). Use this skill whenever someone wants to actually play through a campaign turn-by-turn, or wants live lookups/rolls during a session they're running. Never generates content itself - unprepped player-mode scenes trigger dm-orchestrator's fill workflow first.
---

# DM Livesession

Deliver an existing `dm-orchestrator` campaign live, turn-by-turn. This
skill never builds an outline and never generates encounter, location,
monster, or magic-item content itself - all of that already happened (or
happens on demand, via `dm-orchestrator`) before this skill narrates or
answers anything.

## Read This First: Mode Rules

Every campaign has a `mode`, fixed for its lifetime by `dm-orchestrator`:

- **`player`** — Workflow 1 applies. You are the solo player's DM. A
  strict spoiler guarantee applies: **never reveal any beat beyond
  `session.yml`'s `current_position`** - no title, premise, or `needs` tag
  for a future scene, under any circumstances.
- **`dm`** — Workflow 2 applies. You are a stateless co-pilot for a human
  DM running a live session for other people. There is no spoiler
  restriction - the DM already sees everything in this mode.

If a request doesn't match the campaign's actual mode (e.g. someone asks
for a co-pilot dice roll on a `player`-mode campaign, or a solo-play
narration on a `dm`-mode one), stop and say which mode this campaign
actually is - never silently serve the other workflow.

## Workflow 1: Player Session

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If missing, stop and tell the
user to run `scripts/use-campaign <name>` first.

### Step 2: Read campaign.yml, redacted

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign> --redact
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate a campaign via `dm-orchestrator` first. Confirm `mode` is
`player` - if it's `dm`, stop and say so (see Mode Rules).

The redacted read gives you the outline's chapter/episode/scene numbering
with each scene's `needs`/`status`, and `content_index` reduced to
`(beat, kind)`. That is everything the rest of this workflow needs
structurally; it never reveals a title or premise.

### Step 3: Read session.yml

```bash
python3 <skill-path>/scripts/session_state.py read --campaign <active-campaign>
```

If it returns `{"found": false}`, this is the first-ever session for this
campaign. Resolve the outline's first scene as the starting position by
resolving scope against the redacted outline from Step 2:

```bash
echo '<outline array from the redacted read>' | python3 <repo-root>/ai/skills/dm-orchestrator/scripts/outline_scope.py "chapter 1"
```

Take the first scene in the result as `current_position`. Otherwise, use
`session.yml`'s existing `current_position`.

### Step 4: Check the current beat's readiness

Find the current beat's scene in the redacted outline (matching
`current_position`'s `beat`). For every tag in that scene's `needs`, check
whether `content_index` already has a matching `(beat, kind)` row.

If anything is missing, invoke the `dm-orchestrator` skill to fill just
this beat - a request like "fill in scene `<beat>`" - the same way a human
user would ask for it. Never invoke `encounter-generator`,
`location-generator`, `monster-generator`, or `magic-generator` directly.

If the fill fails, stall gracefully in-narrative (e.g. "you pause at the
door for a moment") rather than breaking the fourth wall, and stop - do
not advance `current_position` or write `session.yml`. Otherwise, re-run
Step 2's redacted read to confirm the beat is now covered before
continuing.

### Step 5: Read the current beat's content, unredacted

Only once Step 4 confirms the current beat is ready:

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign>
```

From the full structure, use only: the current scene's `premise`, its
`content_index` entries' draft paths (read those files), every thread in
`threads` at `introduced` or `advancing` status, and every NPC in `npcs`
whose `last_seen` is at or before this beat's chapter. Do not read this
into anything you say about beats other than the current one.

### Step 6: Narrate

Using the content gathered in Step 5 plus `references/live-narration.md`
for hooks, puzzle pacing, NPC agenda/unreliable-narrator judgement, and
the spoiler boundary, narrate the scene and respond to whatever the player
says next.

### Step 7: React to the player's action

- **On-script** (the action resolves or meaningfully advances the current
  beat): determine the next scene in *play order* — this is a different
  question from "the next scene that still needs generating," which is
  what `outline_scope.py`'s `"the next part"` mode answers for
  `dm-orchestrator`'s fill workflow. Instead, resolve the current beat's
  chapter the same way Step 3 bootstraps the first session:

  ```bash
  echo '<outline array from the redacted read>' | python3 <repo-root>/ai/skills/dm-orchestrator/scripts/outline_scope.py "chapter <current chapter number>"
  ```

  Find the current beat within that chapter's ordered scene list and take
  the scene immediately after it. If the current beat was the last scene
  in its chapter, resolve the next chapter the same way
  (`"chapter <current chapter number + 1>"`) and take its first scene. If
  that also returns `{"matches": null}`, there is no next chapter - the
  campaign is complete (see Error Handling) - do not write `session.yml`
  further. Otherwise write:

  ```bash
  echo '{"current_position": {"beat": "<next beat>"}, "event_log": [{"beat": "<current beat>", "summary": "<one-sentence recap>"}], "delivered_beats": ["<current beat>"]}' | python3 <skill-path>/scripts/session_state.py write --campaign <active-campaign>
  ```

- **Off-script** (the player does something the outline didn't
  anticipate): improvise the consequence per `references/live-narration.md`.
  Do not call `dm-orchestrator` to edit the outline, and do not write
  `session.yml` - `current_position` stays where it is until play resolves
  back onto a planned beat.

### Step 8: Recap requests

Answer "what happened last time" / "where are we" purely from
`session.yml`'s `event_log` and `current_position` - never from the
outline beyond that point.

## Workflow 2: DM Co-pilot

Stateless. Never reads or writes `session.yml`.

### Step 1: Resolve the active campaign and read campaign.yml

Same active-campaign resolution as Workflow 1, Step 1. Then read the full
(non-redacted) memory immediately - there is no spoiler concern in `dm`
mode:

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate a campaign via `dm-orchestrator` first. Confirm `mode` is
`dm` - if it's `player`, stop and say so (see Mode Rules).

### Step 2: Answer the query directly

- **"What's next"**: `dm` mode tracks no position (Workflow 2 is
  stateless), so this means "what still needs content generated," not
  "what happens next at the table" (which only the human DM knows).
  Resolve `"the next part"` against the outline (same `outline_scope.py`
  CLI as Workflow 1's first-session bootstrap) and report the matched
  scene(s) - the next one(s) with `status: planned` - by title and
  premise. If the DM is actually asking what comes next in the story at
  their table, say you don't track that and ask them to name the
  chapter/scene they mean instead.
- **NPC lookup**: find the matching entry in `npcs` and report it.
- **Content lookup**: find the matching `content_index` entry and read
  that draft file directly.
- **Rules/monster lookup for something not already generated**: query
  `shared/dnd5eapi_client.py`, e.g.
  `python3 <repo-root>/shared/dnd5eapi_client.py monsters/goblin`.
- **Ad-hoc dice roll** (initiative, damage, a skill check): run
  `python3 <skill-path>/scripts/dice.py "<notation>"`, e.g.
  `python3 <skill-path>/scripts/dice.py "1d20+3"`. This is a stateless
  single-roll calculator call - no initiative order or combat state is
  tracked across turns.
- **No match** (e.g. an NPC name that doesn't exist): say so plainly.
  There is no spoiler concern in this mode, so be direct.

### Step 3: Never write anything

This workflow never creates, reads, or modifies `session.yml`, and never
writes `campaign.yml`.

## Error Handling

| Case | Handling |
|---|---|
| No active campaign | Stop; tell the user to run `scripts/use-campaign` first. |
| No `outline` in `campaign.yml` yet | Stop; tell the user to generate one via `dm-orchestrator` first. |
| Request's implied workflow doesn't match the campaign's actual `mode` | Stop; state the campaign's actual mode; do not serve the wrong workflow. |
| Current beat needs generation and the `dm-orchestrator` fill fails | Stall gracefully in-narrative; do not advance `current_position` or write `session.yml`. |
| `session.yml` missing on first-ever player session | Not an error - default to the outline's first scene, empty log; created on first write. |
| `session.yml` fails to parse (`invalid_session_state`) | Relay the error and stop - never guess-repair. |
| Off-script player action | Not an error - improvise per Workflow 1 Step 7; no structural write. |
| DM-mode query with no matching data | Say so plainly - no spoiler concern in this mode. |
| Invalid dice notation | Relay `dice.py`'s `invalid_dice_notation` error and ask for a valid expression (e.g. "1d20+3"). |
| Current beat was the campaign's last scene (no next chapter) | The campaign is complete - tell the player/DM so; do not write `session.yml` further. |
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-livesession/SKILL.md
git commit -m "$(cat <<'EOF'
feat(skills): add dm-livesession SKILL.md

Two mode-gated workflows: player-mode turn-by-turn narration with a
strict spoiler guarantee (session.yml bookmark, redacted-then-narrow-full
campaign.yml reads, dm-orchestrator fill on demand, off-script
improvisation), and a stateless dm-mode co-pilot for lookups and ad-hoc
dice rolls. Never invokes the Phase 1 generator skills directly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `evals/evals.json`

**Files:**
- Create: `ai/skills/dm-livesession/evals/evals.json`

**Interfaces:**
- Consumes: the workflows described in `SKILL.md` (Task 4).
- Produces: eval scenarios validated in Task 6's parse check, matching the shape of `ai/skills/dm-orchestrator/evals/evals.json`.

- [ ] **Step 1: Write the evals file**

Create `ai/skills/dm-livesession/evals/evals.json`:

```json
{
  "skill_name": "dm-livesession",
  "evals": [
    {
      "id": 0,
      "prompt": "Let's play. (First-ever session on a player-mode campaign whose first scene is not yet generated.)",
      "expected_output": "session.yml does not exist yet, so the current position defaults to the outline's first scene. That scene's needs are not covered by content_index, so dm-orchestrator's fill workflow is invoked for just that beat before any narration happens. Once filled, the scene is narrated using only that beat's content - no future beat's title, premise, or needs are mentioned anywhere in the response.",
      "files": [],
      "assertions": [
        {"name": "fill_triggered_for_current_beat_only", "description": "dm-orchestrator's fill workflow was invoked for the first scene's beat, not for any other beat"},
        {"name": "no_direct_generator_calls", "description": "encounter-generator/location-generator/monster-generator/magic-generator were never invoked directly by dm-livesession"},
        {"name": "no_future_beat_leakage", "description": "The narration response contains no title, premise, or needs tag belonging to any beat other than the current one"}
      ]
    },
    {
      "id": 1,
      "prompt": "The party resolves the current scene and moves on to what the outline expects next. (On-script resolution.)",
      "expected_output": "session.yml is updated in one call: current_position advances to the next planned scene, event_log gains a one-sentence recap of the resolved beat, and delivered_beats gains that beat. campaign.yml is not written by dm-livesession at all.",
      "files": [],
      "assertions": [
        {"name": "position_advanced", "description": "session.yml's current_position after the turn is the scene immediately following the resolved beat in outline order, whether or not that scene was already filled ahead of time"},
        {"name": "event_log_appended", "description": "session.yml's event_log has exactly one new entry for the resolved beat"},
        {"name": "delivered_beats_appended", "description": "session.yml's delivered_beats includes the resolved beat exactly once"},
        {"name": "campaign_yml_untouched", "description": "campaign.yml was not written by dm-livesession during this turn"}
      ]
    },
    {
      "id": 2,
      "prompt": "The player attacks an NPC the outline never expected them to fight. (Off-script action.)",
      "expected_output": "The consequence is improvised narratively in-character - the NPC reacts, the scene continues - without dm-livesession calling dm-orchestrator to edit the outline and without writing session.yml. current_position stays exactly where it was before the action.",
      "files": [],
      "assertions": [
        {"name": "no_outline_edit", "description": "dm-orchestrator was not asked to insert, remove, or restructure any outline scene"},
        {"name": "no_session_write", "description": "session.yml's current_position, event_log, and delivered_beats are unchanged from before the action"},
        {"name": "not_railroaded", "description": "The response does not refuse the action or force the player back onto the planned scene without in-fiction improvisation"}
      ]
    },
    {
      "id": 3,
      "prompt": "What's next? (DM co-pilot query on a dm-mode campaign.)",
      "expected_output": "The next planned scene(s) in outline order are reported by title and premise directly - no spoiler restriction applies in dm mode. session.yml is never read or written.",
      "files": [],
      "assertions": [
        {"name": "titles_and_premises_shown", "description": "The response includes the next planned scene's title and premise"},
        {"name": "no_session_yml_touch", "description": "session.yml was neither read nor written for this query"}
      ]
    },
    {
      "id": 4,
      "prompt": "Roll initiative for these three goblins. (DM co-pilot dice request.)",
      "expected_output": "dice.py is invoked once per roll needed (or once with the appropriate notation), returning a rolls/modifier/total breakdown. No initiative order or combat state is persisted anywhere - this is a one-off calculator call.",
      "files": [],
      "assertions": [
        {"name": "dice_py_invoked", "description": "The dm-livesession dice.py script was invoked with valid d20-based notation"},
        {"name": "no_persisted_combat_state", "description": "No file under the campaign directory was created or modified to track initiative order"}
      ]
    },
    {
      "id": 5,
      "prompt": "Let's play. (Player-session request made against a dm-mode campaign.)",
      "expected_output": "dm-livesession refuses to run Workflow 1 against this campaign, states plainly that this campaign is in dm mode, and does not narrate anything or read/write session.yml.",
      "files": [],
      "assertions": [
        {"name": "mode_mismatch_refused", "description": "The response states the campaign's actual mode and does not attempt player-mode narration"},
        {"name": "no_session_yml_created", "description": "No session.yml file was created for this dm-mode campaign"}
      ]
    },
    {
      "id": 6,
      "prompt": "The party resolves the current scene, on a campaign where every scene's content was pre-filled ahead of time by dm-orchestrator.",
      "expected_output": "current_position still advances to the scene immediately following the resolved beat in outline order (crossing into the next chapter if the resolved beat was the last scene in its chapter), even though every scene in the outline already has status: filled. dm-livesession never asks outline_scope.py for \"the next part\" to do this advance, since that resolver answers a different question (the next scene still needing content) and would return no match at all once everything is filled.",
      "files": [],
      "assertions": [
        {"name": "advance_independent_of_fill_status", "description": "current_position advances to the next scene in outline order regardless of every scene already being status: filled"},
        {"name": "no_deadlock_on_fully_filled_campaign", "description": "The turn does not fail, stall, or refuse to advance just because no scene has status: planned anymore"}
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate it parses**

Run: `python3 -c "import json; d = json.load(open('ai/skills/dm-livesession/evals/evals.json')); assert d['skill_name'] == 'dm-livesession'; assert len(d['evals']) >= 3; print('OK', len(d['evals']), 'evals')"`
Expected: `OK 7 evals`.

- [ ] **Step 3: Commit**

```bash
git add ai/skills/dm-livesession/evals/evals.json
git commit -m "$(cat <<'EOF'
test(skills): add dm-livesession evals

Covers first-session fill-on-demand, on-script session.yml advancement,
off-script improvisation without outline edits, dm-mode co-pilot lookups
and ad-hoc dice rolls, and refusal on a mode-mismatched request. The
no-future-beat-leakage assertion is the spoiler guarantee and is
release-blocking.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Full verification pass

Run every affected test suite together to confirm nothing regressed.

**Files:** none (verification only).

**Interfaces:** none.

- [ ] **Step 1: Run the new skill's test suite**

```bash
cd ai/skills/dm-livesession && python3 -m pytest tests/ -v
```

Expected: all 19 tests pass (9 from `test_session_state.py` + 10 from `test_dice.py`).

- [ ] **Step 2: Run dm-orchestrator's test suite (regression check)**

```bash
cd ai/skills/dm-orchestrator && python3 -m pytest tests/ -v
```

Expected: all pre-existing tests still pass - nothing in this plan touched `campaign_memory.py` or `outline_scope.py`.

- [ ] **Step 3: Run the remaining skill test suites (regression check)**

```bash
cd ai/skills/encounter-generator && python3 -m pytest tests/ -v
cd ../monster-generator && python3 -m pytest tests/ -v
cd ../magic-generator && python3 -m pytest tests/ -v
```

Expected: all pre-existing tests still pass - this plan never touched any Phase 1 skill's scripts.

- [ ] **Step 4: Run the shared module test suite (regression check)**

```bash
python3 -m pytest shared/tests/ -v
```

Expected: all pre-existing tests still pass - `shared/` was never touched.

- [ ] **Step 5: Validate the evals file one more time in place**

```bash
python3 -c "
import json
data = json.load(open('ai/skills/dm-livesession/evals/evals.json'))
assert data['skill_name'] == 'dm-livesession'
assert len(data['evals']) >= 3
print(f'OK ({len(data[\"evals\"])} evals)')
"
```

Expected: `OK (7 evals)`, no assertion errors.

No commit for this task - it's a verification-only pass over work already committed in Tasks 1-5. If any step fails, fix the regression in the task that introduced it and re-run this task's steps from the top.
