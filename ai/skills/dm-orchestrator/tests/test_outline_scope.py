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


# --- finding 1: an empty-needs scene must never be a permanent dead end -------

def _outline_with_empty_needs_scene(*, trailing_planned: bool) -> list[dict]:
    """Simulates a hand-edited outline where a needs: [] scene is still 'planned'."""
    scenes = [
        {"scene": "01", "premise": "The party negotiates with the mayor.",
         "needs": [], "status": "planned"},
    ]
    if trailing_planned:
        scenes.append(
            {"scene": "02", "premise": "The mayor's guards turn on them.",
             "needs": ["encounter"], "status": "planned"}
        )
    return [{
        "chapter": "01",
        "title": "The Festival Gates",
        "episodes": [{"episode": "01", "title": "Arrival", "scenes": scenes}],
    }]


def test_resolve_next_skips_planned_scene_with_empty_needs():
    outline = _outline_with_empty_needs_scene(trailing_planned=True)
    matches = resolve_scope(outline, "the next part")
    assert [m["beat"] for m in matches] == ["01.01.02"]


def test_resolve_next_returns_none_when_only_empty_needs_scenes_remain():
    outline = _outline_with_empty_needs_scene(trailing_planned=False)
    assert resolve_scope(outline, "the next part") is None


def test_explicit_scope_still_matches_an_empty_needs_scene():
    """Skipping applies only to 'next' resolution - a named scope still finds it."""
    outline = _outline_with_empty_needs_scene(trailing_planned=False)
    matches = resolve_scope(outline, "chapter 1")
    assert [m["beat"] for m in matches] == ["01.01.01"]


# --- finding 7: beat normalization and malformed-number tolerance -------------

UNPADDED_OUTLINE = [
    {
        "chapter": "1",
        "title": "The Festival Gates",
        "episodes": [
            {
                "episode": "1",
                "title": "Arrival",
                "scenes": [
                    {"scene": "2", "premise": "A local begs for help.",
                     "needs": ["encounter"], "status": "planned"},
                ],
            }
        ],
    }
]


def test_unpadded_outline_numbers_normalize_to_the_same_beat():
    """"1"/"1"/"2" and "01"/"01"/"02" must join to the same content_index key."""
    content_index = [{"beat": "01.01.02", "kind": "encounter"}]
    matches = resolve_scope(UNPADDED_OUTLINE, "chapter 1")
    assert [m["beat"] for m in matches] == ["01.01.02"]
    assert matches[0]["beat"] == content_index[0]["beat"]


def test_unpadded_outline_is_reachable_by_next_and_by_scene_scope():
    assert [m["beat"] for m in resolve_scope(UNPADDED_OUTLINE, "the next part")] == ["01.01.02"]
    assert [m["beat"] for m in resolve_scope(UNPADDED_OUTLINE, "scene 1.1.2")] == ["01.01.02"]


MALFORMED_OUTLINE = [
    {"chapter": "prologue", "episodes": [
        {"episode": "01", "scenes": [
            {"scene": "01", "needs": ["location"], "status": "planned"}]}]},
    {"chapter": "01", "episodes": [
        {"episode": "one", "scenes": [
            {"scene": "01", "needs": ["location"], "status": "planned"}]},
        {"episode": "01", "scenes": [
            {"needs": ["encounter"], "status": "planned"},
            {"scene": "02", "needs": ["encounter"], "status": "planned"}]}]},
]


def test_malformed_outline_entries_are_skipped_not_raised():
    matches = resolve_scope(MALFORMED_OUTLINE, "chapter 1")
    assert [m["beat"] for m in matches] == ["01.01.02"]


def test_next_resolution_survives_malformed_outline_entries():
    matches = resolve_scope(MALFORMED_OUTLINE, "the next part")
    assert [m["beat"] for m in matches] == ["01.01.02"]


def test_resolve_scope_tolerates_a_structurally_broken_outline():
    assert resolve_scope(["not a chapter", 7, None], "chapter 1") is None
    assert resolve_scope([{"chapter": "01", "episodes": "nope"}], "the next part") is None
