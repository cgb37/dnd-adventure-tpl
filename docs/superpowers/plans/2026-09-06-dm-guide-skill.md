# dm-guide Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dm-guide` AI skill — the first Phase 2 skill of the AI Skills initiative — which answers DM rules questions from local reference tables (falling back to a new shared, cached 2014 SRD API client for anything not covered locally) and can compile a fixed core-rules cheat-sheet into the active campaign's draft pipeline.

**Architecture:** Two independent pieces. (1) `shared/dnd5eapi_client.py` — a generic, cached, stdlib-only client for `https://www.dnd5eapi.co/api/2014/<endpoint>`, a sibling of the existing `shared/write_draft.py`, reusable later by any other skill for any endpoint (rules, monsters, spells, equipment, ...). Responses are cached indefinitely under `.cache/dnd5eapi/` since 2014 SRD content never changes; a cache hit never touches the network. (2) The `dm-guide` skill itself — two condensed reference files (`core-adjudication.md`, `combat-mechanics.md`) that are the fast, offline, primary path for Q&A, with the API client as a fallback for anything not covered locally, plus a `SKILL.md` tying the workflow together and an `evals.json` for skill-level testing. The cheat-sheet output is always compiled from the local reference files only (never API-fetched) and written via the existing `shared/write_draft.py`, using the repo's pre-existing but currently-unused `dmnote` Jekyll layout.

**Tech Stack:** Python 3 (stdlib only — `urllib.request`/`urllib.error`, no `requests` dependency, matching the existing `write_draft.py`/`encounter_budget.py`/`party_state.py` convention), pytest with `unittest.mock.patch` for network mocking (tests never hit the real network).

**Spec:** [docs/superpowers/specs/2026-09-06-dm-guide-skill-design.md](../specs/2026-09-06-dm-guide-skill-design.md)

## Global Constraints

- No external dependencies (no `requests`) — use `urllib.request`/`urllib.error` from the stdlib only.
- `dnd5eapi_client.py`'s `fetch()` must never raise anything other than `Dnd5eApiError` to its callers, with one of these codes: `"network_error"` (connection/timeout failure), `"not_found"` (HTTP 404), `"invalid_response"` (any other non-2xx status, malformed JSON, or a corrupt cache file). `"repo_root_not_found"` is a separate, pre-existing-pattern code for when `fetch()` is called with no explicit `cache_dir` and no `.git` directory can be found above the current working directory.
- Cache responses indefinitely (no TTL/expiry) under `<repo_root>/.cache/dnd5eapi/<endpoint-with-dashes>.json` — SRD content is static. `.cache/` is already covered by the repo's `.gitignore` (verified: it already contains a bare `.cache/` entry).
- Base URL is exactly `https://www.dnd5eapi.co/api/2014` — `endpoint` arguments never include a leading slash or this prefix.
- Request timeout: 5 seconds.
- No tests may perform a real network call — every test that exercises `fetch()`'s network path must mock `urllib.request.urlopen`.
- The cheat-sheet Markdown body is fixed, campaign-agnostic content compiled only from `core-adjudication.md` and `combat-mechanics.md` — never API-fetched, never campaign-tailored.
- Cheat-sheet frontmatter must use `layout: dmnote` (the existing `_layouts/dmnote.html`), `category: dm-guide`, `permalink: /dm-guide/:slug`, and always overwrite `campaigns/<campaign>/_drafts/dm-guide/core-rules.md` on every request (no promoted-page check).
- No active campaign → surface the same `no_active_campaign` error path as `encounter-generator` ("Run scripts/use-campaign first"). This applies only to the cheat-sheet workflow — the Q&A workflow has no campaign dependency.

---

## Task 1: Shared SRD API client (`shared/dnd5eapi_client.py`)

**Files:**
- Create: `shared/dnd5eapi_client.py`
- Test: `shared/tests/test_dnd5eapi_client.py`

**Interfaces:**
- Produces (used by Task 4's `SKILL.md` instructions, and reusable later by other skills):
  - `Dnd5eApiError(code: str, message: str)` — exception with `.code` and `.message` attributes.
  - `fetch(endpoint: str, *, cache_dir: Path | None = None) -> dict` — `endpoint` is the path after `/api/2014/`, no leading slash (e.g. `"rules/grappling"`). Returns the parsed JSON body. Raises `Dnd5eApiError` on any failure (`"network_error"`, `"not_found"`, `"invalid_response"`, or `"repo_root_not_found"` if `cache_dir` is omitted and no `.git` is found above `Path.cwd()`).
  - CLI: `python3 dnd5eapi_client.py <endpoint>` → prints the JSON body (exit 0) or `{"error": {"code": "...", "message": "..."}}` (exit 1).

- [ ] **Step 1: Write the failing tests**

Create `shared/tests/test_dnd5eapi_client.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dnd5eapi_client import Dnd5eApiError, fetch


def _fake_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = json.dumps(payload).encode("utf-8")
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


def test_fetch_returns_cached_response_without_network(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "rules-grappling.json").write_text(
        json.dumps({"name": "Grappling"}), encoding="utf-8"
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen.assert_not_called()
    assert result == {"name": "Grappling"}


def test_fetch_writes_successful_response_to_cache(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {"name": "Grappling", "desc": "You can grapple..."}

    with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as mock_urlopen:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen.assert_called_once()
    assert result == payload
    cached = json.loads((cache_dir / "rules-grappling.json").read_text(encoding="utf-8"))
    assert cached == payload


def test_fetch_second_call_hits_cache_not_network(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    payload = {"name": "Grappling"}

    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        fetch("rules/grappling", cache_dir=cache_dir)

    with patch("urllib.request.urlopen") as mock_urlopen_second:
        result = fetch("rules/grappling", cache_dir=cache_dir)

    mock_urlopen_second.assert_not_called()
    assert result == payload


def test_fetch_maps_http_404_to_not_found(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/nonexistent", cache_dir=cache_dir)

    assert exc_info.value.code == "not_found"


def test_fetch_maps_other_http_errors_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.HTTPError(url="x", code=500, msg="Server Error", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_maps_connection_failure_to_network_error(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    error = urllib.error.URLError("Connection refused")

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "network_error"


def test_fetch_maps_malformed_json_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    mock = MagicMock()
    mock.read.return_value = b"not json"
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock):
        with pytest.raises(Dnd5eApiError) as exc_info:
            fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_maps_corrupt_cache_file_to_invalid_response(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "rules-grappling.json").write_text("not json", encoding="utf-8")

    with pytest.raises(Dnd5eApiError) as exc_info:
        fetch("rules/grappling", cache_dir=cache_dir)

    assert exc_info.value.code == "invalid_response"


def test_fetch_raises_repo_root_not_found_without_cache_dir_or_git(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Dnd5eApiError) as exc_info:
        fetch("rules/grappling")
    assert exc_info.value.code == "repo_root_not_found"


def test_cli_success_prints_json(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    cache_dir = tmp_path / ".cache" / "dnd5eapi"
    cache_dir.mkdir(parents=True)
    (cache_dir / "rules-grappling.json").write_text(
        json.dumps({"name": "Grappling"}), encoding="utf-8"
    )

    script = Path(__file__).resolve().parents[1] / "dnd5eapi_client.py"
    result = subprocess.run(
        [sys.executable, str(script), "rules/grappling"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out == {"name": "Grappling"}


def test_cli_error_exits_nonzero(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    cache_dir = tmp_path / ".cache" / "dnd5eapi"
    cache_dir.mkdir(parents=True)
    (cache_dir / "rules-nonexistent.json").write_text("not json", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "dnd5eapi_client.py"
    result = subprocess.run(
        [sys.executable, str(script), "rules/nonexistent"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "invalid_response"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest shared/tests/test_dnd5eapi_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dnd5eapi_client'`

- [ ] **Step 3: Write the implementation**

Create `shared/dnd5eapi_client.py`:

```python
#!/usr/bin/env python3
"""
Generic, cached client for the public D&D 2014 SRD API
(https://www.dnd5eapi.co/api/2014/, docs: https://5e-bits.github.io/docs/introduction).

Lives at the repo root's shared/ dir (a sibling of write_draft.py) so any
skill can reach it via the same sys.path bootstrap (walk up from the
script's own path to find .git, then add repo_root / "shared" to sys.path).
It is deliberately endpoint-agnostic - dm-guide calls it for rules/*, but
future skills (monster-generator, magic-generator, players-handbook) can
call it for monsters/*, spells/*, equipment/*, etc. without any change
here.

Local-first, API-supplemental: dm-guide's own local reference markdown is
the fast, offline path for common questions. This client exists for
follow-up questions those local tables don't cover.

Responses are cached indefinitely under <repo_root>/.cache/dnd5eapi/ (2014
SRD content is static, so there is no expiry/TTL logic) - a cache hit
never touches the network. Every test of this module mocks
urllib.request.urlopen; none of them perform a real network call.

CLI usage:
  python3 dnd5eapi_client.py rules/grappling

Output (stdout): the JSON body (exit 0), or
  {"error": {"code": "...", "message": "..."}} (exit 1).
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://www.dnd5eapi.co/api/2014"
TIMEOUT_SECONDS = 5


class Dnd5eApiError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until a directory containing `.git` is found."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise Dnd5eApiError("repo_root_not_found", f"No .git directory found above {start}")


def _default_cache_dir() -> Path:
    return find_repo_root(Path.cwd()) / ".cache" / "dnd5eapi"


def _cache_path(cache_dir: Path, endpoint: str) -> Path:
    safe_name = endpoint.strip("/").replace("/", "-")
    return cache_dir / f"{safe_name}.json"


def fetch(endpoint: str, *, cache_dir: Path | None = None) -> dict:
    """Fetch `endpoint` (path after /api/2014/, no leading slash) as JSON.

    Checks the on-disk cache first; a hit is returned without any network
    call. On a miss, fetches from BASE_URL, caches the result, and returns
    it. Raises Dnd5eApiError on any failure - never any other exception
    type reaches the caller.
    """
    resolved_cache_dir = cache_dir if cache_dir is not None else _default_cache_dir()
    path = _cache_path(resolved_cache_dir, endpoint)

    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Dnd5eApiError(
                "invalid_response", f"Cached response for {endpoint!r} is corrupt: {exc}"
            )

    url = f"{BASE_URL}/{endpoint.strip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise Dnd5eApiError("not_found", f"No resource at {endpoint!r} (HTTP 404)")
        raise Dnd5eApiError(
            "invalid_response", f"HTTP {exc.code} fetching {endpoint!r}: {exc.reason}"
        )
    except urllib.error.URLError as exc:
        raise Dnd5eApiError("network_error", f"Could not reach dnd5eapi.co: {exc.reason}")

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Dnd5eApiError("invalid_response", f"Malformed JSON from {endpoint!r}: {exc}")

    resolved_cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="Path after /api/2014/, e.g. rules/grappling")
    args = parser.parse_args()

    try:
        data = fetch(args.endpoint)
    except Dnd5eApiError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest shared/tests/test_dnd5eapi_client.py -v`
Expected: PASS (all 11 tests)

- [ ] **Step 5: Commit**

```bash
git add shared/dnd5eapi_client.py shared/tests/test_dnd5eapi_client.py
git commit -m "feat(shared): add cached SRD API client for skill rules lookups"
```

---

## Task 2: dm-guide reference content

**Files:**
- Create: `ai/skills/dm-guide/references/core-adjudication.md`
- Create: `ai/skills/dm-guide/references/combat-mechanics.md`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces (used by Task 3's `SKILL.md` workflow and Task 4's evals): condensed rules content Claude reads directly and (for the cheat-sheet path) renders verbatim into the draft body. No code interface.

- [ ] **Step 1: Write `core-adjudication.md`**

Create `ai/skills/dm-guide/references/core-adjudication.md`:

```markdown
# Core Adjudication Reference

Quick rulings for the "how do I call this" moments that come up constantly
at the table — not a full rules reprint. If a question isn't covered here,
fall back to `scripts` — actually, dm-guide has no scripts; fall back to
`dnd5eapi_client.py` (see SKILL.md).

## Ability Checks & DCs

| DC | Difficulty  |
|----|-------------|
| 5  | Very easy   |
| 10 | Easy        |
| 15 | Medium      |
| 20 | Hard        |
| 25 | Very hard   |
| 30 | Nearly impossible |

A check succeeds if `d20 + ability modifier + proficiency bonus (if
proficient) >= DC`. Default to DC 15 for an unremarkable "can they do this"
moment; reserve DC 20+ for genuinely difficult, high-stakes attempts.

## Advantage & Disadvantage

- Roll two d20s, take the higher (advantage) or lower (disadvantage).
- Advantage and disadvantage never stack — any number of sources of each
  still cancels out to a single net advantage, disadvantage, or straight
  roll (one of each cancels to a flat roll).
- Common advantage sources: attacking a prone target in melee, attacking
  an unseen/distracted target, help from another creature (see below).
- Common disadvantage sources: attacking a prone target at range,
  attacking while restrained/prone, attacking at long range with a
  ranged weapon, attacking in melee while an enemy is adjacent to a
  ranged attacker.

## The Help Action

A creature can use its action to help another creature's ability check or
attack roll, granting advantage on the next such roll before the helper's
next turn — provided the helper is capable of actually assisting (e.g. not
helping pick a lock they don't have tools for).

## Conditions

| Condition   | Key effects |
|-------------|-------------|
| Blinded     | Auto-fails sight-based checks; attacks against it have advantage; its attacks have disadvantage. |
| Charmed     | Can't attack the charmer or target it with harmful abilities/magic. |
| Deafened    | Auto-fails hearing-based checks. |
| Frightened  | Disadvantage on ability checks/attacks while the source of fear is in sight; can't willingly move closer to it. |
| Grappled    | Speed becomes 0. Ends if the grappler is incapacitated, or if the grappled creature is moved out of the grappler's reach by an effect. |
| Incapacitated | Can't take actions or reactions. |
| Invisible   | Considered heavily obscured; attacks against it have disadvantage, its attacks have advantage. |
| Paralyzed   | Incapacitated, can't move/speak; auto-fails Str/Dex saves; attacks against it have advantage; any hit from within 5 ft. is a critical hit. |
| Petrified   | Transformed to stone; incapacitated, can't move/speak; unaware of surroundings; resistance to all damage; auto-fails Str/Dex saves; immune to poison/disease. |
| Poisoned    | Disadvantage on attack rolls and ability checks. |
| Prone       | Can only crawl unless it stands (costs half movement); disadvantage on attack rolls; attacks against it have advantage if attacker is within 5 ft., disadvantage otherwise. |
| Restrained  | Speed 0; disadvantage on attack rolls and Dex saves; attacks against it have advantage. |
| Stunned     | Incapacitated, can't move, can speak only falteringly; auto-fails Str/Dex saves; attacks against it have advantage. |
| Unconscious | Incapacitated, can't move/speak, unaware of surroundings; drops what it's holding, falls prone; auto-fails Str/Dex saves; attacks against it have advantage; any hit from within 5 ft. is a critical hit. |

## Cover

| Cover      | Effect |
|------------|--------|
| Half cover | +2 to AC and Dex saves. (At least half the body is blocked.) |
| Three-quarters cover | +5 to AC and Dex saves. (Only a small portion is exposed — e.g. an arrow slit.) |
| Total cover | Can't be targeted directly. |

## Resting

- **Short rest** (1 hour): spend Hit Dice to heal (roll the die + Con
  modifier per Hit Die spent, minimum 0).
- **Long rest** (8 hours, at least 1 hour of which is sleeping or light
  activity): regain all HP and up to half total Hit Dice (minimum 1).
  Regains most limited-use class features. A character needs at least 6
  hours of sleep/rest as part of a long rest; interrupting it with more
  than 1 hour of walking, fighting, or similarly strenuous activity
  restarts the clock.
- A creature can't benefit from more than one long rest in a 24-hour
  period, and needs at least 1 hit point at the start of a long rest to
  gain its benefits.

## Death Saves

- At 0 HP (and not killed outright), an unconscious creature has three
  death-save "lives." Each turn, roll a d20 with no modifiers:
  - 10 or higher: a success.
  - 9 or lower: a failure.
  - Natural 20: regain 1 HP and become conscious.
  - Natural 1: counts as two failures.
- Three successes: stabilize (unconscious, but no more rolls needed until
  healed or it takes damage). Three failures: the creature dies.
- Taking any damage while at 0 HP causes one death-save failure (two if
  the hit is a critical hit); taking damage equal to or exceeding the
  creature's max HP in one hit while at 0 HP causes instant death
  (massive damage).
- A creature that receives healing while at 0 HP regains consciousness
  with the healed HP total, wiping any accumulated successes/failures.
```

- [ ] **Step 2: Write `combat-mechanics.md`**

Create `ai/skills/dm-guide/references/combat-mechanics.md`:

```markdown
# Combat Mechanics Reference

Turn structure and action-economy rulings for running combat smoothly.
For picking/scaling monsters against an XP budget, see the
`encounter-generator` skill's `references/encounter-building.md` instead —
this file covers turn-by-turn mechanics, not encounter design.

## Turn Order

1. Everyone rolls initiative (`d20 + Dex modifier`) at the start of
   combat; ties are broken by the DM's judgment (highest Dex modifier is
   a reasonable default tiebreaker).
2. Turns proceed from highest initiative to lowest, looping each round.
3. On your turn you may take one action, one move (up to your speed,
   which can be split before/after the action), and one bonus action (if
   a feature grants one) — in any order.

## Actions, Bonus Actions, Reactions

- **Action**: Attack, Cast a Spell (most spells), Dash (double effective
  movement this turn), Disengage (movement doesn't provoke opportunity
  attacks this turn), Dodge (attacks against you have disadvantage, you
  have advantage on Dex saves, until your next turn), Help, Hide, Ready
  (prepare an action to trigger on a stated condition, using your
  reaction when it triggers), Search, Use an Object.
- **Bonus action**: Only usable if a specific feature/spell grants one
  (e.g. Two-Weapon Fighting's off-hand attack, a Rogue's Cunning Action).
  You get at most one bonus action per turn, regardless of how many
  features would grant one.
- **Reaction**: One per round (refreshes at the start of your turn),
  usable on another creature's turn when its trigger occurs (most
  commonly an opportunity attack, or a readied action).

## Opportunity Attacks

Triggered when a hostile creature you can see moves out of your reach
(within 5 ft., or your weapon's reach) without using the Disengage
action. You may use your reaction to make one melee attack against it as
it leaves. Teleportation, being forced to move (e.g. shoved), and moves
that don't leave your reach (e.g. moving within your reach) don't
provoke it.

## Multiattack

A "Multiattack" action lets a creature make more than one attack on its
turn as a single action (as opposed to a player character's Extra Attack
feature, which is its own separate class feature). Each attack in a
Multiattack is resolved separately (separate to-hit roll, separate
damage).

## Ranged Attacks in Melee

Making a ranged attack (weapon or spell) while a hostile creature is
within 5 ft. of you imposes disadvantage on the attack roll, unless you
have a feature that says otherwise (e.g. a Fighting Style).

## Mounted Combat

- A rider can control a mount if it's trained for combat, using the
  mount's own movement and actions as normal for a mount (see below);
  an independent (untrained) mount acts on its own initiative and the
  rider can't direct its movement or actions.
- The rider chooses whether attacks target the rider or the mount when
  both are viable targets, unless an attacker specifically targets one.
- If the mount is knocked prone, the rider must succeed on a DC 10 Dex
  save or be dismounted, landing prone in an unoccupied space within 5
  ft.; on a failed save while not dismounted, the rider still falls
  prone with the mount if it doesn't otherwise avoid the fall.
- Mounting or dismounting costs movement equal to half your speed, and
  can't be done if you have no movement left.
```

- [ ] **Step 3: Commit**

```bash
git add ai/skills/dm-guide/references/core-adjudication.md ai/skills/dm-guide/references/combat-mechanics.md
git commit -m "docs(skills): add dm-guide core-adjudication and combat-mechanics references"
```

---

## Task 3: `SKILL.md` — the dm-guide skill definition

**Files:**
- Create: `ai/skills/dm-guide/SKILL.md`

**Interfaces:**
- Consumes: `shared/dnd5eapi_client.py` (Task 1), `references/core-adjudication.md` and `references/combat-mechanics.md` (Task 2), `shared/write_draft.py` (pre-existing, from the `encounter-generator` plan).
- Produces: the skill's triggering description and workflow — this is what Claude reads to decide when and how to use the skill. No code interface.

- [ ] **Step 1: Write the skill definition**

Create `ai/skills/dm-guide/SKILL.md`:

```markdown
---
name: dm-guide
description: Answer D&D 5e DM rules questions (ability checks, conditions, cover, resting, death saves, turn order, actions/bonus actions/reactions, opportunity attacks, multiattack, mounted combat, and similar rulings) and, on request, compile a core-rules cheat-sheet page into the active campaign. Use this skill whenever a DM asks how a rule works, what a condition does, what DC to use, or asks for a quick-reference sheet at the table. This is a rules-lookup skill, not a content generator — use encounter-generator/location-generator/monster-generator/rpg-character-gen instead for creating encounters, locations, monsters, or characters.
---

# DM Guide

Answer D&D 5e rules questions for the DM, and compile a fixed core-rules
cheat-sheet into the active campaign on request.

## Workflow: Answering a Rules Question

### Step 1: Check local references first

Read `references/core-adjudication.md` (ability checks/DCs, advantage &
disadvantage, conditions, cover, resting, death saves) and
`references/combat-mechanics.md` (turn order, actions/bonus
actions/reactions, opportunity attacks, multiattack, ranged-in-melee,
mounted combat). If the question is covered there, answer directly from
that content — no network call needed.

### Step 2: Fall back to the SRD API for anything not covered locally

If the local references don't cover the question, call the shared API
client:

```bash
python3 <repo-root>/shared/dnd5eapi_client.py rules/<relevant-endpoint>
```

Pick `<relevant-endpoint>` based on the question — the 2014 SRD API's
rules endpoints are organized by rule section (e.g. `rules/grappling`,
`rules/mounted-combat`). If you're unsure of the exact endpoint slug, try
your best guess; on a 404 (`"not_found"`), try `rules` (no sub-path) to
see the list of available sections, or answer from your own best
judgment instead of guessing repeatedly.

Answer the question using the JSON response.

### Step 3: If the API call fails, don't block the answer

If the client exits non-zero (its stdout is `{"error": {"code": "...",
"message": "..."}}`), tell the user the rules API couldn't be reached —
relay the error message plainly — and then still answer the question
from your own knowledge and best judgment. Never refuse to answer a rules
question just because the API lookup failed.

This entire workflow has no dependency on an active campaign — it works
the same with or without one set.

## Workflow: Compiling the Core-Rules Cheat-Sheet

Triggered by requests like "give me a core-rules cheat sheet" or "compile
the DM reference page."

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is
empty, stop and tell the user to run `scripts/use-campaign <name>` first
— don't guess a campaign, and don't write anything.

### Step 2: Compile the fixed content

Render **both** `references/core-adjudication.md` and
`references/combat-mechanics.md` into one Markdown body, covering every
section in both files. This content is the same every time — don't
tailor it to the current campaign or fetch anything from the SRD API for
this path; the committed cheat-sheet should never depend on network
availability.

### Step 3: Write the draft

Build the frontmatter with these exact keys:

```json
{
  "layout": "dmnote",
  "title": "Core Rules Reference",
  "permalink": "/dm-guide/:slug",
  "category": "dm-guide",
  "jumbo": "",
  "search": true,
  "excerpt_separator": ""
}
```

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.) `layout: dmnote` uses this repo's existing
`_layouts/dmnote.html`, a DM-only page layout.

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "dm-guide",
  "slug": "core-rules",
  "title": "Core Rules Reference",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
```

This **always overwrites** `campaigns/<campaign>/_drafts/dm-guide/core-rules.md`
— there's no promoted-page check, so re-running this on a campaign that
already promoted a previous cheat-sheet will still overwrite the draft
(it won't touch anything already promoted to `_pages/`).

On success, tell the user the draft is ready and that
`scripts/promote-draft dm-guide core-rules` will publish it.

On error (e.g. `no_active_campaign`), relay the error message directly —
don't retry silently or guess a fix.

## Tips for Good Output

- **Prefer the local references over the API for anything they cover** —
  they're faster, always available, and don't depend on the SRD site
  being up.
- **Don't guess mechanically when the answer matters at the table.** If
  neither the local references nor the API cover something precisely,
  say so plainly rather than presenting a guess as settled rules.
- **Keep cheat-sheet content skimmable.** It's meant to be glanced at
  mid-session, not read start to finish — preserve the tables and
  headers from the source references rather than converting them to
  prose.
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-guide/SKILL.md
git commit -m "feat(skills): define dm-guide skill workflow"
```

---

## Task 4: dm-guide evals

**Files:**
- Create: `ai/skills/dm-guide/evals/evals.json`

**Interfaces:**
- Consumes: nothing (content file describing expected end-to-end skill behavior, mirroring `ai/skills/encounter-generator/evals/evals.json`'s shape).
- Produces: nothing consumed by later tasks — this is the last task in the plan.

- [ ] **Step 1: Write the evals file**

Create `ai/skills/dm-guide/evals/evals.json`:

```json
{
  "skill_name": "dm-guide",
  "evals": [
    {
      "id": 0,
      "prompt": "What happens if I paralyze the goblin, then another goblin attacks it in melee?",
      "expected_output": "An answer explaining that Paralyzed grants advantage to attacks against the creature and that any hit from within 5 feet is a critical hit, sourced from references/core-adjudication.md without calling the SRD API.",
      "files": [],
      "assertions": [
        { "name": "answered_locally", "description": "The condition table in references/core-adjudication.md is used; dnd5eapi_client.py is not invoked" },
        { "name": "mechanically_correct", "description": "Response states advantage on attacks against the paralyzed creature and automatic critical hit within 5 ft." }
      ]
    },
    {
      "id": 1,
      "prompt": "My players want to ride warhorses into battle for the first time. How does mounted combat work if the horses aren't trained for war?",
      "expected_output": "An answer covering that an independent (untrained) mount acts on its own initiative and can't be directed, sourced from references/combat-mechanics.md's Mounted Combat section, falling back to the SRD API only if the local answer is judged insufficient.",
      "files": [],
      "assertions": [
        { "name": "answered_locally_or_via_fallback", "description": "Response correctly distinguishes trained vs. independent mount behavior" },
        { "name": "graceful_fallback_if_used", "description": "If dnd5eapi_client.py was called and it failed, the response still answers the question and states the API was unreachable rather than refusing to answer" }
      ]
    },
    {
      "id": 2,
      "prompt": "Compile the core rules cheat sheet for my campaign.",
      "expected_output": "A draft written to campaigns/<active-campaign>/_drafts/dm-guide/core-rules.md with layout: dmnote frontmatter and a body covering every section from both core-adjudication.md and combat-mechanics.md.",
      "files": [],
      "assertions": [
        { "name": "draft_written", "description": "A file exists at campaigns/<active-campaign>/_drafts/dm-guide/core-rules.md" },
        { "name": "correct_layout", "description": "Frontmatter includes layout: dmnote, category: dm-guide, permalink: /dm-guide/:slug" },
        { "name": "content_complete", "description": "Body includes content from both reference files' sections, not a partial subset" }
      ]
    },
    {
      "id": 3,
      "prompt": "Compile the core rules cheat sheet.",
      "expected_output": "No active campaign is set, so the skill reports the no_active_campaign error and tells the user to run scripts/use-campaign first, without writing any draft.",
      "files": [],
      "assertions": [
        { "name": "no_draft_written", "description": "No file is created under any campaigns/*/_drafts/dm-guide/" },
        { "name": "clear_error", "description": "Response tells the user to run scripts/use-campaign, matching the no_active_campaign error message" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/dm-guide/evals/evals.json
git commit -m "test(skills): add dm-guide evals"
```

---

## Final Verification

- [ ] **Run the full test suite for this skill**

```bash
python3 -m pytest shared/tests/test_dnd5eapi_client.py -v
```

Expected: PASS (all 11 tests)

- [ ] **Sanity-check the CLI cache path end-to-end (no real network call)**

```bash
cd /tmp && rm -rf dnd5eapi-smoke-test && mkdir dnd5eapi-smoke-test && cd dnd5eapi-smoke-test
git init -q
mkdir -p .cache/dnd5eapi
echo '{"index": "grappling", "name": "Grappling"}' > .cache/dnd5eapi/rules-grappling.json
python3 <repo-root>/shared/dnd5eapi_client.py rules/grappling
cd - && rm -rf /tmp/dnd5eapi-smoke-test
```

Expected: prints `{"index": "grappling", "name": "Grappling"}` with no
network access attempted (the cache file satisfies the request).

- [ ] **(Optional, manual) Verify a real network fetch works**

This step is not required for automated verification (CI/sandboxed
environments may have no network access), but if you have internet
access, confirm the live API integration actually works end-to-end:

```bash
cd /tmp && rm -rf dnd5eapi-live-test && mkdir dnd5eapi-live-test && cd dnd5eapi-live-test
git init -q
python3 <repo-root>/shared/dnd5eapi_client.py rules/grappling
cat .cache/dnd5eapi/rules-grappling.json
cd - && rm -rf /tmp/dnd5eapi-live-test
```

Expected: both commands print the same JSON body — the second command
proves the first call cached its response to disk.

---

## Self-Review Notes

- **Spec coverage:** Client interface (Task 1), local-first Q&A with API
  fallback (Task 3), fixed cheat-sheet content and `dmnote` layout (Task
  3), caching with no expiry (Task 1), error handling for both workflows
  (Task 3), testing for both the client (Task 1) and the skill (Task 4)
  are all covered. The spec's "Out of Scope" items (wiring other skills
  to the client, campaign-tailored cheat-sheets, cache TTL,
  `players-handbook`, `dm-orchestrator`) are intentionally not tasked
  here.
- **Placeholder scan:** No TBD/TODO markers; every step has runnable
  code or complete Markdown content.
- **Type consistency:** `fetch(endpoint: str, *, cache_dir: Path | None = None) -> dict`
  and `Dnd5eApiError(code: str, message: str)` are defined once in Task 1
  and referenced identically (same names, same call shape) in Task 3's
  `SKILL.md` instructions.
