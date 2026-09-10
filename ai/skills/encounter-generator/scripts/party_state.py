#!/usr/bin/env python3
"""
Read/write the per-campaign party state file (campaigns/<campaign>/party.yml).

This is a lightweight seed for encounter-generator's low-friction workflow -
just enough to auto-fill party level/size without asking every time. It is
NOT the full campaign-memory model planned for the dm-orchestrator skill
(Phase 3 of docs/superpowers/concepts/2026-09-06-ai-skills-concept.md).

Parsing/writing is hand-rolled for this exact shape (not a general YAML
library) to keep the skill dependency-free:

  level: 5
  size: 4
  composition:
    - class: bard
    - class: barbarian

`write` only ever produces the minimal `class`-only composition shown
above. Reading, however, also accepts campaigns whose composition entries
were hand-authored with extra fields (`dm-livesession` looks these up to
know which characters/players exist), e.g.:

  composition:
    - name: Aiden Oathkeeper
      slug: aiden-oathkeeper
      class: paladin/warlock

Any keys present on a composition entry are passed through unchanged;
`class` is not treated specially during parsing.

CLI usage:
  Read:  python3 party_state.py read --campaign my-campaign
  Write: python3 party_state.py write --campaign my-campaign --level 5 \
             --size 4 --classes bard barbarian wizard cleric

Output (read, found): {"level": 5, "size": 4, "composition": [{"class": "bard"}, ...]}
Output (read, not found or incomplete): {"found": false}
Output (write): {"path": "campaigns/my-campaign/party.yml"}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"No .git directory found above {start}")


def _party_path(repo_root: Path, campaign: str) -> Path:
    return repo_root / "campaigns" / campaign / "party.yml"


def read_party_state(repo_root: Path, campaign: str) -> dict | None:
    path = _party_path(repo_root, campaign)
    if not path.exists():
        return None

    level: int | None = None
    size: int | None = None
    composition: list[dict[str, str]] = []
    current_entry: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line == "composition:":
            continue
        if line.startswith("level:"):
            current_entry = None
            try:
                level = int(line.split(":", 1)[1].strip())
            except ValueError:
                level = None
        elif line.startswith("size:"):
            current_entry = None
            try:
                size = int(line.split(":", 1)[1].strip())
            except ValueError:
                size = None
        elif line.startswith("- "):
            key, _, value = line[2:].partition(":")
            current_entry = {key.strip(): value.strip()}
            composition.append(current_entry)
        elif current_entry is not None and ":" in line:
            # A continuation field of the composition entry currently being
            # built (e.g. `slug:`/`class:` following a `- name:` line).
            key, _, value = line.partition(":")
            current_entry[key.strip()] = value.strip()

    if level is None or size is None:
        return None
    return {"level": level, "size": size, "composition": composition}


def write_party_state(
    repo_root: Path, campaign: str, level: int, size: int, classes: list[str]
) -> Path:
    path = _party_path(repo_root, campaign)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"level: {level}", f"size: {size}", "composition:"]
    for class_name in classes:
        lines.append(f"  - class: {class_name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--campaign", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--campaign", required=True)
    write_parser.add_argument("--level", type=int, required=True)
    write_parser.add_argument("--size", type=int, required=True)
    write_parser.add_argument("--classes", nargs="+", required=True)

    args = parser.parse_args()
    repo_root = find_repo_root(Path.cwd())

    if args.command == "read":
        state = read_party_state(repo_root, args.campaign)
        print(json.dumps(state if state is not None else {"found": False}))
        return 0

    path = write_party_state(
        repo_root, args.campaign, level=args.level, size=args.size, classes=args.classes
    )
    print(json.dumps({"path": str(path.relative_to(repo_root))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
