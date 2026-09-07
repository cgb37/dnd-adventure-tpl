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
