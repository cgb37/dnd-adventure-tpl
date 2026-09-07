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

`beat` is always zero-padded ("01.01.02") regardless of how the outline spelled
its numbers, so it is a stable join key against campaign.yml's content_index.
Outline entries whose numbers are missing or non-numeric are skipped rather than
raising - a malformed outline still gets valid JSON out of this tool.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any


def _num(value: Any) -> int | None:
    """Parse an outline number, or None if it isn't one.

    Outline numbers come out of campaign.yml, which can be hand-edited, so a
    malformed or missing entry must degrade to "this entry doesn't match" rather
    than raising out of main() as a raw traceback.
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _dicts(value: Any) -> list[dict[str, Any]]:
    """Yield only the dict entries of what should be a list of dicts."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _augment(
    chapter: dict[str, Any], episode: dict[str, Any], scene: dict[str, Any]
) -> dict[str, Any] | None:
    """Add chapter/episode/beat keys to a scene, or None if it can't be numbered.

    `beat` is zero-padded to two digits per level so an outline written with "1"
    and one written with "01" resolve to the same content_index key ("01.01.02")
    - otherwise the same scene could be generated twice under two different beats.
    """
    nums = [_num(chapter.get("chapter")), _num(episode.get("episode")), _num(scene.get("scene"))]
    if any(n is None for n in nums):
        return None
    return {
        **scene,
        "chapter": chapter.get("chapter"),
        "episode": episode.get("episode"),
        "beat": ".".join(f"{n:02d}" for n in nums),
    }


def _find_scenes(
    outline: list[dict[str, Any]],
    *,
    chapter_num: int | None = None,
    episode_num: int | None = None,
    scene_num: int | None = None,
) -> list[dict[str, Any]] | None:
    matches: list[dict[str, Any]] = []
    for chapter in _dicts(outline):
        if chapter_num is not None and _num(chapter.get("chapter")) != chapter_num:
            continue
        for episode in _dicts(chapter.get("episodes")):
            if episode_num is not None and _num(episode.get("episode")) != episode_num:
                continue
            for scene in _dicts(episode.get("scenes")):
                if scene_num is not None and _num(scene.get("scene")) != scene_num:
                    continue
                augmented = _augment(chapter, episode, scene)
                if augmented is not None:
                    matches.append(augmented)
    return matches if matches else None


def resolve_scope(outline: list[dict[str, Any]], scope_text: str) -> list[dict[str, Any]] | None:
    """Resolve a freeform scope phrase against an outline.

    Returns a list of matched scene dicts (each with 'chapter', 'episode',
    and 'beat' keys added), or None if nothing in the outline matches.
    """
    text = scope_text.strip().lower()

    if "next" in text:
        for chapter in _dicts(outline):
            for episode in _dicts(chapter.get("episodes")):
                for scene in _dicts(episode.get("scenes")):
                    if scene.get("status") != "planned":
                        continue
                    # A scene with no needs has nothing to generate, so filling it
                    # can never flip its status. Outlines are now written with such
                    # scenes already `filled`; this skip keeps a hand-edited outline
                    # from parking "the next part" on a scene that can never advance.
                    if not scene.get("needs"):
                        continue
                    augmented = _augment(chapter, episode, scene)
                    if augmented is not None:
                        return [augmented]
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
