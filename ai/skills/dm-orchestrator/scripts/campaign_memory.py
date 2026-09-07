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
