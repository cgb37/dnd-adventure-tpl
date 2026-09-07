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
