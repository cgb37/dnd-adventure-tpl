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

CLI usage:
  Read:          python3 campaign_memory.py read --campaign my-campaign
  Read (safe):   python3 campaign_memory.py read --campaign my-campaign --redact
  Write:         echo '<json>' | python3 campaign_memory.py write --campaign my-campaign

Output (read, found): the full campaign.yml structure as JSON
Output (read, found, --redact): a spoiler-free reduction of that structure -
  mode, outline numbering + needs/status, and content_index (beat, kind) only
Output (read, not found): {"found": false}
Output (read, unparseable): {"error": {"code": "invalid_campaign_memory", ...}},
  exit code 1 - a corrupt file is never confused with a missing one, and is
  never guess-repaired.
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


# Leading characters that must never appear unquoted in a rendered scalar, because
# they would change how this module's own parser reads the line back. The set
# mirrors shared/write_draft.py's `_YAML_INDICATOR_PREFIXES` (a sibling convention,
# deliberately duplicated rather than imported) with one addition: a leading '"'.
# `_parse_scalar` decides a token is quoted by checking startswith('"')/endswith('"'),
# so prose containing quoted speech - Beware, she said, "run" - must be rendered as a
# real JSON string or it round-trips into a parse failure.
# As in write_draft.py, '-' is handled separately: only the bare "-" and the "- "
# block-sequence-entry prefix are ambiguous, not an ordinary word like "-foo".
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
        # Only *looks* quoted. A hand-edited file can hold prose that opens and
        # closes with a quote mark without being a valid JSON string; falling back
        # to the raw token keeps one odd line from making the whole file unreadable.
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

_REQUIRED_KEYS = {"mode", "outline"}


def read_campaign_memory(repo_root: Path, campaign: str) -> dict[str, Any] | None:
    """Read campaign.yml.

    Returns None when there is simply no campaign yet - either the file does not
    exist, or it exists but lacks the required top-level keys (an outline was
    never written). Raises CampaignMemoryError('invalid_campaign_memory') when the
    file exists and reading/parsing it actually blows up: "corrupt" must never be
    mistaken for "absent", or a fill/outline workflow would happily overwrite a
    recoverable file and mode immutability would quietly stop being enforced.
    """
    path = _campaign_memory_path(repo_root, campaign)
    if not path.exists():
        return None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        data, _ = _parse_mapping(lines, 0, 0)
    except Exception as exc:
        raise CampaignMemoryError(
            "invalid_campaign_memory",
            f"Campaign memory at {path} exists but could not be read: "
            f"{type(exc).__name__}: {exc}. Repair or remove the file by hand - "
            f"dm-orchestrator will not guess-repair or overwrite it.",
        ) from exc
    if not _REQUIRED_KEYS.issubset(data.keys()):
        return None
    return data


def redact_campaign_memory(data: dict[str, Any]) -> dict[str, Any]:
    """Reduce campaign memory to the spoiler-free subset a player-mode fill needs.

    Keeps exactly what outline_scope.py's scope resolution and the fill workflow's
    already-generated skip-check consume: mode, outline numbering with each scene's
    needs/status, and content_index's (beat, kind) join key. Everything that could
    reveal what happens in the campaign - titles, premises, threads, npcs, the
    top-level premise/scope, and draft slugs/paths - is dropped.
    """
    return {
        "mode": data.get("mode"),
        "outline": [
            {
                "chapter": chapter.get("chapter"),
                "episodes": [
                    {
                        "episode": episode.get("episode"),
                        "scenes": [
                            {
                                "scene": scene.get("scene"),
                                "needs": scene.get("needs", []),
                                "status": scene.get("status"),
                            }
                            for scene in episode.get("scenes", [])
                        ],
                    }
                    for episode in chapter.get("episodes", [])
                ],
            }
            for chapter in data.get("outline", [])
        ],
        "content_index": [
            {"beat": entry.get("beat"), "kind": entry.get("kind")}
            for entry in data.get("content_index", [])
        ],
    }


def _dedupe_content_index(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, Any], dict[str, Any]] = {}
    for entry in entries:
        deduped[(entry.get("beat"), entry.get("kind"))] = entry
    return list(deduped.values())


def write_campaign_memory(repo_root: Path, campaign: str, data: dict[str, Any]) -> Path:
    # A CampaignMemoryError from this read is deliberately *not* caught: if the
    # existing file is unreadable we cannot know its mode, so we must refuse the
    # write rather than treat it as "no existing campaign" and let mode change.
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
    read_parser.add_argument(
        "--redact",
        action="store_true",
        help="Return only the spoiler-free subset (mode, outline numbering with "
             "needs/status, content_index beat/kind). Use in player mode.",
    )

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--campaign", required=True)

    args = parser.parse_args()
    repo_root = find_repo_root(Path.cwd())

    if args.command == "read":
        try:
            data = read_campaign_memory(repo_root, args.campaign)
        except CampaignMemoryError as exc:
            print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
            return 1
        if data is None:
            print(json.dumps({"found": False}))
            return 0
        print(json.dumps(redact_campaign_memory(data) if args.redact else data))
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
