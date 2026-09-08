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
