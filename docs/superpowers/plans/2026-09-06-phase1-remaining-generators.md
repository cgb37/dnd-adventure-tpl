# Phase 1 Remaining Generator Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the three remaining Phase 1 AI Skills — `location-generator`, `monster-generator`, `magic-generator` — completing Phase 1 of the AI Skills initiative alongside the existing `encounter-generator`.

**Architecture:** Each skill is a self-contained directory under `ai/skills/<name>-generator/` (`SKILL.md` + optional `scripts/` + `references/` + `evals/evals.json`), following `ai/skills/encounter-generator`'s established shape exactly. All three reuse the existing `shared/write_draft.py` for campaign resolution and draft writing — no changes to that file. `monster-generator` and `magic-generator` each get one new pure-calculator script (`monster_statblock.py`, `magic_item_rarity.py`), unit-tested the same way as `encounter-generator/scripts/encounter_budget.py`. `location-generator` needs no script. One small, necessary fix to `services/llm_api` (registering the `magic-item` promotion mapping) is included so `scripts/promote-draft magic-item <slug>` works for the new skill's documented workflow.

**Tech Stack:** Python 3 (stdlib only for skill scripts — `argparse`, `json`; no new dependencies), `pytest` for all tests.

**Spec:** `docs/superpowers/specs/2026-09-06-phase1-remaining-generators-design.md`

## Global Constraints

- Skill scripts are dependency-free stdlib Python, matching `encounter_budget.py` and `party_state.py` — no new pip dependencies.
- Every script prints JSON to stdout and uses `{"error": {"code", "message"}}` + exit code 1 on invalid input — never a raw traceback.
- `location-generator` and `monster-generator` write **structured frontmatter** matching the real Jekyll layouts (`_layouts/location.html`, `_layouts/monster.html`) with an **empty Markdown body** — do not duplicate frontmatter content into prose body text for these two skills.
- `magic-generator` writes a **prose Markdown body** under the reused `reward` layout, matching `encounter-generator`'s shape — not a structured stat block.
- Every skill's error handling matches `encounter-generator`: no active campaign → relay `no_active_campaign` guidance verbatim; `write_draft.py` failures → relay the underlying error; never guess a campaign or silently retry.
- `monster-generator` and `magic-generator` never block on a missing party level/CR/rarity — they assume a stated default (CR 3 / level 5 party) and say so, per the spec's "optional calibration context" rule. This differs from `encounter-generator`, which does ask once for missing party info — do not copy that blocking behavior into these two skills.

---

### Task 1: Register the `magic-item` promotion mapping

`magic-generator`'s `SKILL.md` (Task 6) will tell users to run `scripts/promote-draft magic-item <slug>`. That command currently fails with `unsupported_kind` because `magic-item` isn't in `PROMOTION_RULES`. Fix this first so later tasks' documented workflow is actually true.

**Files:**
- Modify: `services/llm_api/src/llm_api/services/promotion_mapping.py`
- Test: `services/llm_api/tests/test_promotion_mapping.py` (new file)

**Interfaces:**
- Consumes: `llm_api.services.promotion_mapping.get_promoted_path(*, campaign_root, kind, slug)` (existing function, unchanged signature).
- Produces: `PROMOTION_RULES["magic-item"]` entry mapping to `_pages/magic-items`, usable by any later task or skill that promotes a `magic-item` draft.

- [ ] **Step 1: Write the failing test**

Create `services/llm_api/tests/test_promotion_mapping.py`:

```python
from __future__ import annotations

from pathlib import Path

from llm_api.services.promotion_mapping import get_promoted_path


def test_magic_item_promotes_to_pages_magic_items(tmp_path: Path):
    campaign_root = tmp_path / "campaigns" / "test-campaign"
    result = get_promoted_path(campaign_root=campaign_root, kind="magic-item", slug="ring-of-warmth")
    assert result == campaign_root / "_pages" / "magic-items" / "ring-of-warmth.md"


def test_magic_item_kind_is_listed_as_promotable():
    from llm_api.services.promotion_mapping import list_promotable_kinds

    assert "magic-item" in list_promotable_kinds()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd services/llm_api && pytest tests/test_promotion_mapping.py -v`
Expected: FAIL — `KeyError` inside `get_promoted_path` (no `PROMOTION_RULES["magic-item"]` entry yet), and the second test fails the `assert`.

- [ ] **Step 3: Add the mapping entry**

In `services/llm_api/src/llm_api/services/promotion_mapping.py`, add one line to the `PROMOTION_RULES` dict (keep alphabetical-by-kind grouping already present — insert after `"location"` and before `"monster"`):

```python
    "location": PromotionRule(kind="location", target_pages_dir="_pages/locations"),
    "magic-item": PromotionRule(kind="magic-item", target_pages_dir="_pages/magic-items"),
    "monster": PromotionRule(kind="monster", target_pages_dir="_pages/monsters"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/llm_api && pytest tests/test_promotion_mapping.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add services/llm_api/src/llm_api/services/promotion_mapping.py services/llm_api/tests/test_promotion_mapping.py
git commit -m "$(cat <<'EOF'
fix(llm_api): register magic-item promotion mapping

magic-generator's documented workflow calls `scripts/promote-draft
magic-item <slug>`; without this entry that call fails with
unsupported_kind since PROMOTION_RULES had no magic-item rule.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `monster_statblock.py` — CR guidance and ability modifier calculator

**Files:**
- Create: `ai/skills/monster-generator/scripts/monster_statblock.py`
- Test: `ai/skills/monster-generator/tests/test_monster_statblock.py`

**Interfaces:**
- Consumes: nothing (pure stdlib).
- Produces: `cr_guidelines(cr: str) -> dict` (raises `StatblockError`), `score_to_modifier(score: int) -> str` (raises `StatblockError`), both importable by `ai/skills/monster-generator/tests/test_monster_statblock.py` and invocable as a CLI (`--cr`, `--score` flags) by Task 5's `SKILL.md` instructions.

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/monster-generator/tests/test_monster_statblock.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from monster_statblock import StatblockError, cr_guidelines, score_to_modifier


def test_cr_guidelines_cr_5():
    result = cr_guidelines("5")
    assert result["cr"] == "5"
    assert result["proficiency_bonus"] == 3
    assert result["ac_range"] == [15, 17]
    assert result["hp_range"] == [101, 115]
    assert result["attack_bonus_range"] == [6, 8]
    assert result["damage_per_round_range"] == [33, 38]


def test_cr_guidelines_cr_1_8():
    result = cr_guidelines("1/8")
    assert result["proficiency_bonus"] == 2
    assert result["hp_range"] == [7, 12]


def test_cr_guidelines_cr_20():
    result = cr_guidelines("20")
    assert result["proficiency_bonus"] == 6
    assert result["hp_range"] == [341, 400]


def test_cr_guidelines_invalid_cr_raises():
    with pytest.raises(StatblockError) as exc_info:
        cr_guidelines("6")
    assert exc_info.value.code == "invalid_cr"


def test_score_to_modifier_positive():
    assert score_to_modifier(16) == "+3"


def test_score_to_modifier_zero():
    assert score_to_modifier(10) == "+0"
    assert score_to_modifier(11) == "+0"


def test_score_to_modifier_negative():
    assert score_to_modifier(8) == "-1"


def test_score_to_modifier_invalid_raises():
    with pytest.raises(StatblockError) as exc_info:
        score_to_modifier(0)
    assert exc_info.value.code == "invalid_score"


def test_cli_cr_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--cr", "5"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["proficiency_bonus"] == 3


def test_cli_score_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--score", "16"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["modifier"] == "+3"


def test_cli_invalid_cr_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script), "--cr", "6"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "invalid_cr"


def test_cli_missing_input_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "monster_statblock.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "missing_input"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ai/skills/monster-generator && python3 -m pytest tests/test_monster_statblock.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'monster_statblock'` (the script doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `ai/skills/monster-generator/scripts/monster_statblock.py`:

```python
#!/usr/bin/env python3
"""
Compute D&D 5e stat-block guidance (AC/HP/attack/damage ranges, proficiency
bonus) for a target challenge rating, plus an ability-score-to-modifier
helper.

Deterministic lookup only - monster-generator uses this so Claude never
eyeballs whether a stat block is plausible for its CR. Values mirror
../../rpg-character-gen/references/npc-stat-blocks.md's "CR Estimation
Guidelines" table exactly; see references/monster-building.md for how to
turn these ranges into a full stat block.

Usage:
  python3 monster_statblock.py --cr 5
  python3 monster_statblock.py --score 16

Output (--cr): JSON {"cr", "proficiency_bonus", "ac_range": [lo, hi],
  "hp_range": [lo, hi], "attack_bonus_range": [lo, hi],
  "damage_per_round_range": [lo, hi]}
Output (--score): JSON {"score", "modifier"}
On invalid input: JSON {"error": {"code", "message"}}, exit code 1.
"""
from __future__ import annotations

import argparse
import json

# CR Estimation Guidelines, exactly matching
# ../../rpg-character-gen/references/npc-stat-blocks.md.
CR_GUIDELINES: dict[str, dict[str, object]] = {
    "0": {"proficiency_bonus": 2, "ac_range": [10, 12], "hp_range": [1, 6], "attack_bonus_range": [2, 3], "damage_per_round_range": [0, 1]},
    "1/8": {"proficiency_bonus": 2, "ac_range": [12, 13], "hp_range": [7, 12], "attack_bonus_range": [3, 3], "damage_per_round_range": [2, 5]},
    "1/4": {"proficiency_bonus": 2, "ac_range": [13, 13], "hp_range": [13, 20], "attack_bonus_range": [3, 4], "damage_per_round_range": [4, 6]},
    "1/2": {"proficiency_bonus": 2, "ac_range": [13, 13], "hp_range": [20, 35], "attack_bonus_range": [3, 4], "damage_per_round_range": [6, 8]},
    "1": {"proficiency_bonus": 2, "ac_range": [13, 14], "hp_range": [36, 49], "attack_bonus_range": [3, 5], "damage_per_round_range": [9, 14]},
    "2": {"proficiency_bonus": 2, "ac_range": [13, 14], "hp_range": [50, 70], "attack_bonus_range": [3, 5], "damage_per_round_range": [15, 20]},
    "3": {"proficiency_bonus": 2, "ac_range": [13, 15], "hp_range": [71, 85], "attack_bonus_range": [4, 6], "damage_per_round_range": [21, 26]},
    "5": {"proficiency_bonus": 3, "ac_range": [15, 17], "hp_range": [101, 115], "attack_bonus_range": [6, 8], "damage_per_round_range": [33, 38]},
    "8": {"proficiency_bonus": 3, "ac_range": [16, 17], "hp_range": [146, 160], "attack_bonus_range": [7, 9], "damage_per_round_range": [51, 56]},
    "12": {"proficiency_bonus": 4, "ac_range": [17, 18], "hp_range": [206, 220], "attack_bonus_range": [8, 10], "damage_per_round_range": [69, 74]},
    "17": {"proficiency_bonus": 6, "ac_range": [19, 20], "hp_range": [281, 310], "attack_bonus_range": [10, 12], "damage_per_round_range": [93, 98]},
    "20": {"proficiency_bonus": 6, "ac_range": [19, 21], "hp_range": [341, 400], "attack_bonus_range": [10, 13], "damage_per_round_range": [111, 116]},
}


class StatblockError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _cr_sort_key(cr: str) -> float:
    if "/" in cr:
        num, den = cr.split("/")
        return int(num) / int(den)
    return float(cr)


def cr_guidelines(cr: str) -> dict:
    if cr not in CR_GUIDELINES:
        valid = sorted(CR_GUIDELINES, key=_cr_sort_key)
        raise StatblockError("invalid_cr", f"CR must be one of {valid}, got {cr!r}")
    return {"cr": cr, **CR_GUIDELINES[cr]}


def score_to_modifier(score: int) -> str:
    if score < 1 or score > 30:
        raise StatblockError("invalid_score", f"Ability score must be 1-30, got {score}")
    modifier = (score - 10) // 2
    return f"+{modifier}" if modifier >= 0 else str(modifier)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cr", help="Challenge rating, e.g. 5 or 1/4")
    parser.add_argument("--score", type=int, help="Ability score to convert to a modifier")
    args = parser.parse_args()

    if args.cr is None and args.score is None:
        print(json.dumps({"error": {"code": "missing_input", "message": "Provide --cr or --score"}}))
        return 1

    try:
        if args.cr is not None:
            result = cr_guidelines(args.cr)
        else:
            result = {"score": args.score, "modifier": score_to_modifier(args.score)}
    except StatblockError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ai/skills/monster-generator && python3 -m pytest tests/test_monster_statblock.py -v`
Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add ai/skills/monster-generator/scripts/monster_statblock.py ai/skills/monster-generator/tests/test_monster_statblock.py
git commit -m "$(cat <<'EOF'
feat(skills): add monster-generator CR statblock calculator

Deterministic AC/HP/attack/damage guidance by CR, plus an
ability-score-to-modifier helper, so the monster-generator skill never
hand-computes stat block numbers.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `magic_item_rarity.py` — rarity-by-level calculator

**Files:**
- Create: `ai/skills/magic-generator/scripts/magic_item_rarity.py`
- Test: `ai/skills/magic-generator/tests/test_magic_item_rarity.py`

**Interfaces:**
- Consumes: nothing (pure stdlib).
- Produces: `rarity_for_level(party_level: int) -> dict` (raises `RarityError`), `rarity_details(rarity: str) -> dict` (raises `RarityError`), both importable by `ai/skills/magic-generator/tests/test_magic_item_rarity.py` and invocable as a CLI (`--party-level`, `--rarity` flags) by Task 6's `SKILL.md` instructions.

- [ ] **Step 1: Write the failing tests**

Create `ai/skills/magic-generator/tests/test_magic_item_rarity.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from magic_item_rarity import RarityError, rarity_details, rarity_for_level


def test_rarity_for_level_1():
    result = rarity_for_level(1)
    assert result["eligible_rarities"] == ["common", "uncommon"]
    assert result["recommended_rarity"] == "uncommon"
    assert result["typically_requires_attunement"] == {"common": False, "uncommon": False}


def test_rarity_for_level_8():
    result = rarity_for_level(8)
    assert result["eligible_rarities"] == ["common", "uncommon", "rare"]
    assert result["recommended_rarity"] == "rare"


def test_rarity_for_level_20():
    result = rarity_for_level(20)
    assert result["eligible_rarities"] == ["common", "uncommon", "rare", "very rare", "legendary"]
    assert result["recommended_rarity"] == "legendary"


def test_rarity_for_level_invalid_raises():
    with pytest.raises(RarityError) as exc_info:
        rarity_for_level(21)
    assert exc_info.value.code == "invalid_level"


def test_rarity_details_rare():
    result = rarity_details("rare")
    assert result["minimum_level"] == 5
    assert result["typically_requires_attunement"] is True


def test_rarity_details_case_insensitive():
    result = rarity_details("Very Rare")
    assert result["rarity"] == "very rare"
    assert result["minimum_level"] == 11


def test_rarity_details_invalid_raises():
    with pytest.raises(RarityError) as exc_info:
        rarity_details("mythic")
    assert exc_info.value.code == "invalid_rarity"


def test_cli_party_level_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script), "--party-level", "8"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["recommended_rarity"] == "rare"


def test_cli_rarity_outputs_json():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script), "--rarity", "legendary"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["minimum_level"] == 17


def test_cli_missing_input_exits_nonzero():
    script = Path(__file__).resolve().parents[1] / "scripts" / "magic_item_rarity.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["error"]["code"] == "missing_input"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ai/skills/magic-generator && python3 -m pytest tests/test_magic_item_rarity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'magic_item_rarity'`.

- [ ] **Step 3: Write the implementation**

Create `ai/skills/magic-generator/scripts/magic_item_rarity.py`:

```python
#!/usr/bin/env python3
"""
Compute D&D 5e magic item rarity guidance (DMG "Magic Item Rarity by
Character Level") for a target party level, or look up attunement/level
norms for an explicitly chosen rarity.

Deterministic lookup only - magic-generator uses this so Claude never
guesses whether a rarity is level-appropriate. See
references/magic-item-building.md for property-budget guidance once a
rarity is chosen.

Usage:
  python3 magic_item_rarity.py --party-level 8
  python3 magic_item_rarity.py --rarity rare

Output (--party-level): JSON {"party_level", "eligible_rarities": [...],
  "recommended_rarity", "typically_requires_attunement": {rarity: bool, ...}}
Output (--rarity): JSON {"rarity", "minimum_level", "typically_requires_attunement"}
On invalid input: JSON {"error": {"code", "message"}}, exit code 1.
"""
from __future__ import annotations

import argparse
import json

# DMG "Magic Item Rarity by Character Level" minimum levels, and whether
# attunement is typical (not universal - varies per item) at that rarity.
RARITY_ORDER: list[str] = ["common", "uncommon", "rare", "very rare", "legendary"]
RARITY_MINIMUM_LEVEL: dict[str, int] = {
    "common": 1, "uncommon": 1, "rare": 5, "very rare": 11, "legendary": 17,
}
RARITY_TYPICALLY_REQUIRES_ATTUNEMENT: dict[str, bool] = {
    "common": False, "uncommon": False, "rare": True, "very rare": True, "legendary": True,
}


class RarityError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def rarity_for_level(party_level: int) -> dict:
    if party_level < 1 or party_level > 20:
        raise RarityError("invalid_level", f"Party level must be 1-20, got {party_level}")

    eligible = [r for r in RARITY_ORDER if RARITY_MINIMUM_LEVEL[r] <= party_level]
    return {
        "party_level": party_level,
        "eligible_rarities": eligible,
        "recommended_rarity": eligible[-1],
        "typically_requires_attunement": {r: RARITY_TYPICALLY_REQUIRES_ATTUNEMENT[r] for r in eligible},
    }


def rarity_details(rarity: str) -> dict:
    key = rarity.strip().lower()
    if key not in RARITY_MINIMUM_LEVEL:
        raise RarityError("invalid_rarity", f"Rarity must be one of {RARITY_ORDER}, got {rarity!r}")
    return {
        "rarity": key,
        "minimum_level": RARITY_MINIMUM_LEVEL[key],
        "typically_requires_attunement": RARITY_TYPICALLY_REQUIRES_ATTUNEMENT[key],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--party-level", type=int)
    parser.add_argument("--rarity")
    args = parser.parse_args()

    if args.party_level is None and args.rarity is None:
        print(json.dumps({"error": {"code": "missing_input", "message": "Provide --party-level or --rarity"}}))
        return 1

    try:
        if args.rarity is not None:
            result = rarity_details(args.rarity)
        else:
            result = rarity_for_level(args.party_level)
    except RarityError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ai/skills/magic-generator && python3 -m pytest tests/test_magic_item_rarity.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add ai/skills/magic-generator/scripts/magic_item_rarity.py ai/skills/magic-generator/tests/test_magic_item_rarity.py
git commit -m "$(cat <<'EOF'
feat(skills): add magic-generator rarity-by-level calculator

Deterministic DMG rarity-by-level and attunement guidance so the
magic-generator skill never guesses whether a rarity is level-appropriate.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `location-generator` skill files

No script needed for this skill (see spec). This task creates the full skill directory in one pass: `SKILL.md`, `references/location-building.md`, `evals/evals.json`.

**Files:**
- Create: `ai/skills/location-generator/SKILL.md`
- Create: `ai/skills/location-generator/references/location-building.md`
- Create: `ai/skills/location-generator/evals/evals.json`

**Interfaces:**
- Consumes: `shared/write_draft.py`'s CLI contract (unchanged — `kind`, `campaign`, `slug`, `title`, `frontmatter`, `body` JSON payload piped via stdin, per Task 1's spec reference and `ai/skills/encounter-generator/SKILL.md`'s Step 6 for the exact invocation pattern).
- Produces: nothing consumed by later tasks (this skill is a leaf).

- [ ] **Step 1: Write `SKILL.md`**

Create `ai/skills/location-generator/SKILL.md`:

```markdown
---
name: location-generator
description: Generate a D&D 5e location (town, dungeon, wilderness site, ...) and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a location, place, dungeon, town, or area for their campaign. Triggers on requests like "give me a location for the swamp chapter," "generate a hidden temple," or "I need a town for the party to rest in." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Location Generator

Generate a story-appropriate D&D 5e location and write it as a draft in the
active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve narrative and calibration context

- Narrative context (where/why this location matters, what chapter it's
  in) comes from whatever the user already said. Only ask if the request
  is genuinely bare (e.g. just "generate a location").
- Party level, if the user mentions it (or it's obvious from context),
  calibrates challenge severity in Step 3. If no level is given, assume a
  level 5 party (a reasonable mid-campaign default) and say so in your
  response — don't block on asking for it, unlike `encounter-generator`
  (a location doesn't need the full party composition).

### Step 3: Design the location

Read `references/location-building.md` for DC/severity scaling by level and
guidance on tying secrets, plot hooks, and NPCs to the active story.

Write:
- `description`: prose covering the location's look, feel, and atmosphere.
- `challenges`: up to four categories (`traps`, `ambushes`, `puzzles`,
  `hazards`), each a bullet-list string (see Step 4's exact format) scaled
  to the party level from Step 2. Omit any category that doesn't fit this
  location rather than inventing filler.
- `secrets`, `plot_hooks`: tied to the campaign's story context from Step 2.
- `npcs`: named characters who can be found here, if any fit.
- `environmental_features`: at least one feature the party can interact
  with, not just scenery.
- `additional_notes`: guidance for the DM on customizing this location at
  the table.

### Step 4: Write the draft

Build the frontmatter with these exact keys (matching the existing FastAPI
location generator's schema):

\`\`\`json
{
  "layout": "location",
  "title": "<title>",
  "permalink": "/locations/:slug",
  "category": "location",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/location-thumb.png",
  "portrait": "/assets/images/placeholders/location-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": "",
  "name": "<location name>",
  "type": "<location type, e.g. \"Enchanted Forest\">",
  "description": "<prose from Step 3>",
  "challenges": {
    "traps": "- Trap Name: description\n- Another Trap: description",
    "ambushes": "- Ambush description",
    "puzzles": "- Puzzle description",
    "hazards": "- Hazard description"
  },
  "secrets": ["<secret>", "..."],
  "plot_hooks": ["<hook>", "..."],
  "npcs": [{ "name": "<name>", "description": "<description>" }],
  "environmental_features": ["<feature>", "..."],
  "additional_notes": "<prose guidance for the DM>"
}
\`\`\`

Each populated `challenges` category is a single string whose *content* is
a Markdown-style bullet list (one `- Name: description` per line, joined
with `\n`) — not a YAML list. Omit any `challenges` category, or the whole
`challenges` key, that doesn't apply. `additional_notes` is a single prose
string, not a list.

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Pipe it to the shared writer:

\`\`\`bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
\`\`\`

Where `<json payload>` is:

\`\`\`json
{
  "kind": "location",
  "campaign": "<active-campaign>",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": ""
}
\`\`\`

Use the `<active-campaign>` value already resolved in Step 1 — don't rely
on `write_draft.py`'s `.active-campaign`/cwd-based auto-resolution, since
campaign directories are git submodules and a cwd inside one could resolve
the wrong repo root. `body` is empty because `location.html` renders every
field from frontmatter; don't duplicate content into a Markdown body.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/location/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft location <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Story fit matters most.** A location that doesn't connect to the
  campaign's plot, faction, or the party's current chapter reads as
  filler.
- **Give the DM something to react to** in `environmental_features` and
  `challenges`, not just atmosphere — at least one thing the party can
  use, trigger, or solve.
- **Match challenge severity to the party level** from Step 2 using
  `references/location-building.md`'s guidance — a level 1 party facing a
  DC 18 puzzle is a broken encounter, not a challenge.
```

- [ ] **Step 2: Write `references/location-building.md`**

Create `ai/skills/location-generator/references/location-building.md`:

```markdown
# Location Building Reference

Guidance for scaling challenge severity and tying a location to the active
campaign's story.

## Scaling Challenges to Party Level

Traps, hazards, and puzzle DCs should track roughly with the party's
level, the same way `encounter-generator`'s XP budget tracks with level.
Use these bands as a starting point — judgment calls, not a DMG table:

| Party Level | Trap/Hazard DC | Trap/Hazard Damage | Puzzle Difficulty |
|---|---|---|---|
| 1-4 | 10-13 | 1d6-2d6 | Straightforward, 1-2 steps |
| 5-10 | 13-16 | 2d6-4d10 | Multi-step, may need a specific skill or spell |
| 11-16 | 16-19 | 4d10-6d10 | Requires piecing together clues from multiple sources |
| 17-20 | 19-22 | 6d10-10d10 | Layered, may require a specific combination of actions |

Ambushes should reference
`../../encounter-generator/references/encounter-building.md`'s monster-role
and CR guidance if the ambush is meant to be run as a real combat
encounter, rather than inventing separate monster balance rules here.

## Structuring Challenges

Each `challenges` category (`traps`, `ambushes`, `puzzles`, `hazards`) is a
list of one-line entries, each `Name: what happens and how to
resist/avoid it (DC, damage, or skill check where relevant)`. Two or three
entries per populated category is enough — don't pad. Skip a category
entirely if nothing in this location warrants it (not every location
needs a puzzle).

## Tying the Location to the Story

- Ground `secrets` and `plot_hooks` in whatever campaign context the user
  already gave — a faction, an NPC, an ongoing plot thread. A secret that
  doesn't connect to anything is a dead end for the DM.
- `npcs` should be characters the party can actually meet here, not a
  worldbuilding aside — give each one a reason to be present and a reason
  to matter to the plot hooks above.
- `environmental_features` should describe things the party can use,
  trigger, or be affected by (cover, an updraft, unstable footing, a
  resource to loot) rather than pure scenery.
- `additional_notes` is where you tell the DM how to adapt this location
  on the fly — what to change if the party goes off-script, what to leave
  vague on purpose.
```

- [ ] **Step 3: Write `evals/evals.json`**

Create `ai/skills/location-generator/evals/evals.json`:

```json
{
  "skill_name": "location-generator",
  "evals": [
    {
      "id": 0,
      "prompt": "My party is exploring the ruins of an old elven tower in chapter 2. Generate a location for it.",
      "expected_output": "A written draft at campaigns/<active-campaign>/_drafts/location/<slug>.md with elven-tower-themed content, populated challenges/secrets/plot_hooks/npcs/environmental_features tied to the ruins setting, and all required frontmatter keys.",
      "files": [],
      "assertions": [
        { "name": "draft_written", "description": "A file exists at campaigns/<active-campaign>/_drafts/location/<slug>.md" },
        { "name": "valid_frontmatter", "description": "Frontmatter includes layout, title, permalink, category, chapter, episode, scene, jumbo, thumb, portrait, tags, search, excerpt_separator, id, slug, name, type, description" },
        { "name": "fits_theme", "description": "name/type/description/environmental_features are specifically elven-ruins-themed, not generic" },
        { "name": "no_stray_body", "description": "The draft's Markdown body is empty - all content lives in frontmatter" }
      ]
    },
    {
      "id": 1,
      "prompt": "Generate a location for my campaign.",
      "expected_output": "No active campaign is set, so the skill reports the no_active_campaign error and tells the user to run scripts/use-campaign first, without writing any draft.",
      "files": [],
      "assertions": [
        { "name": "no_draft_written", "description": "No file is created under any campaigns/*/_drafts/location/" },
        { "name": "clear_error", "description": "Response tells the user to run scripts/use-campaign, matching the no_active_campaign error message" }
      ]
    },
    {
      "id": 2,
      "prompt": "Generate a hidden temple for the party to discover, no other details given.",
      "expected_output": "No party level is mentioned, so the skill assumes a level 5 party, says so in its response, and still generates and writes a complete draft without blocking on a clarifying question.",
      "files": [],
      "assertions": [
        { "name": "states_assumption", "description": "Response explicitly states it assumed a level 5 party" },
        { "name": "no_blocking_question", "description": "The skill does not stop to ask the user for party level before generating" },
        { "name": "draft_written", "description": "A location draft is still written despite no level being given" }
      ]
    }
  ]
}
```

- [ ] **Step 4: Validate the eval JSON parses**

Run: `python3 -c "import json; json.load(open('ai/skills/location-generator/evals/evals.json'))" && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ai/skills/location-generator/
git commit -m "$(cat <<'EOF'
feat(skills): add location-generator skill

Generates a D&D 5e location matching _layouts/location.html's structured
frontmatter fields exactly, writing directly into the active campaign's
draft pipeline via shared/write_draft.py.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `monster-generator` skill files

**Files:**
- Create: `ai/skills/monster-generator/SKILL.md`
- Create: `ai/skills/monster-generator/references/monster-building.md`
- Create: `ai/skills/monster-generator/evals/evals.json`

**Interfaces:**
- Consumes: `monster_statblock.py`'s CLI (`--cr <cr>` → CR guidance JSON; `--score <score>` → modifier JSON) from Task 2. `shared/write_draft.py`'s CLI contract (same as Task 4). Optionally `shared/dnd5eapi_client.py`'s CLI (`python3 dnd5eapi_client.py monsters/<index>`, already existing and unchanged).
- Produces: nothing consumed by later tasks (this skill is a leaf).

- [ ] **Step 1: Write `SKILL.md`**

Create `ai/skills/monster-generator/SKILL.md`:

```markdown
---
name: monster-generator
description: Generate a D&D 5e monster stat block and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a monster, creature, or beast for their campaign. Triggers on requests like "give me a monster for the swamp encounter," "generate a CR 5 undead," or "I need a boss creature for the finale." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Monster Generator

Generate a CR-appropriate, story-appropriate D&D 5e monster stat block and
write it as a draft in the active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve the target CR and narrative context

- The user's request usually implies or states a CR (e.g. "a CR 5 undead,"
  "a boss for a level 12 party" — for the latter, pick a CR roughly equal
  to party level for a solo boss, per
  `../encounter-generator/references/encounter-building.md`'s multiplier
  guidance). If genuinely unstated, assume CR 3 (a common mid-tier threat)
  and say so in your response — don't block on asking.
- Narrative context (what this creature is, why it's here) comes from
  whatever the user already said.

### Step 3: Compute the stat-block guidance

\`\`\`bash
python3 <skill-path>/scripts/monster_statblock.py --cr <cr>
\`\`\`

This returns `proficiency_bonus`, `ac_range`, `hp_range`,
`attack_bonus_range`, and `damage_per_round_range` for the target CR. Do
not invent these numbers yourself — always use the script's output as the
band your stat block should land in. If you need an ability modifier for a
specific score, run:

\`\`\`bash
python3 <skill-path>/scripts/monster_statblock.py --score <score>
\`\`\`

`--cr` only accepts the exact values in
`references/monster-building.md`'s CR table (0, 1/8, 1/4, 1/2, 1, 2, 3, 5,
8, 12, 17, 20) — round the requested CR to the nearest of these before
calling the script, then adjust the numbers within the returned range to
taste for the exact CR requested.

### Step 4: Design the stat block

Read `references/monster-building.md` for how to turn the Step 3 ranges
into ability scores, actions, and special abilities appropriate for the
CR. Optionally look up an existing SRD monster for inspiration:

\`\`\`bash
python3 <repo-root>/shared/dnd5eapi_client.py monsters/<index>
\`\`\`

(e.g. `monsters/dire-wolf`; skip this if you're inventing something
original rather than reskinning a known creature.)

### Step 5: Write the draft

Build the frontmatter with these exact keys (matching the existing FastAPI
monster generator's schema):

\`\`\`json
{
  "layout": "monster",
  "title": "<title>",
  "permalink": "/monsters/:slug",
  "category": "monster",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/monster-thumb.png",
  "portrait": "/assets/images/placeholders/monster-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": "",
  "name": "<monster name>",
  "description": "<prose>",
  "type": "<Beast | Dragon | Undead | ...>",
  "size": "<Tiny | Small | Medium | Large | Huge | Gargantuan>",
  "ac": { "value": 0, "type": "natural armor" },
  "hp": "<N (XdY + Z)>",
  "hp_dice": "<XdY>",
  "speed": "<e.g. \"30 ft., fly 60 ft.\">",
  "abilities": {
    "strength": { "score": 0, "modifier": "+0" },
    "dexterity": { "score": 0, "modifier": "+0" },
    "constitution": { "score": 0, "modifier": "+0" },
    "intelligence": { "score": 0, "modifier": "+0" },
    "wisdom": { "score": 0, "modifier": "+0" },
    "charisma": { "score": 0, "modifier": "+0" }
  },
  "saving_throws": [{ "name": "dexterity", "modifier": "+0" }],
  "skills": "<e.g. \"Perception +4, Stealth +3\">",
  "senses": "<e.g. \"darkvision 60 ft., passive Perception 14\">",
  "languages": ["<language>"],
  "challenge": "<N (NNN XP)>",
  "special_abilities": [{ "name": "<name>", "description": "<description>" }],
  "actions": [
    {
      "name": "<name>",
      "type": "Melee Weapon Attack",
      "hit_bonus": "+0",
      "reach": "5 ft.",
      "target": "one target",
      "damage": [{ "type": "piercing", "dice": "1d10 + 2", "avg": 7 }]
    }
  ]
}
\`\`\`

Notes on optional keys:
- `abilities.*.modifier` and any ability-check-derived numbers should come
  from `monster_statblock.py --score <score>`, not hand math.
- `challenge`'s XP comes from
  `../encounter-generator/scripts/encounter_budget.py`'s `cr_to_xp` table
  (run it with any valid `--level`/`--party-size`/`--difficulty` just to
  read the table, or read
  `../rpg-character-gen/references/npc-stat-blocks.md` directly) — don't
  invent the XP number.
- Include `spellcasting` (with `ability`, `dc`, `slots`, `spells`) only if
  the monster casts spells; omit the key entirely otherwise.
- Include `reactions`, `treasure`, `notes` only when applicable; omit
  otherwise.

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Pipe it to the shared writer:

\`\`\`bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
\`\`\`

Where `<json payload>` is:

\`\`\`json
{
  "kind": "monster",
  "campaign": "<active-campaign>",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": ""
}
\`\`\`

Use the `<active-campaign>` value already resolved in Step 1 — don't rely
on `write_draft.py`'s `.active-campaign`/cwd-based auto-resolution, since
campaign directories are git submodules and a cwd inside one could resolve
the wrong repo root. `body` is empty because `monster.html` renders every
field from frontmatter; don't duplicate content into a Markdown body.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/monster/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft monster <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Mechanical accuracy matters.** Always ground AC/HP/attack/damage in
  `monster_statblock.py`'s ranges for the target CR — a monster that's
  meaningfully outside its CR band breaks encounter balance for anyone
  who uses it later.
- **Story fit matters as much as CR fit.** Tie type, abilities, and
  description to whatever context the user gave rather than generating a
  generic creature.
- **Give it at least one distinguishing special ability or tactic**, not
  just a bigger number than a mundane beast of the same size.
```

- [ ] **Step 2: Write `references/monster-building.md`**

Create `ai/skills/monster-generator/references/monster-building.md`:

```markdown
# Monster Building Reference

Guidance for turning `scripts/monster_statblock.py`'s CR guidance into a
full stat block.

## Using the CR Guidance

`monster_statblock.py --cr <cr>` returns ranges for AC, HP, attack bonus,
and damage per round, plus the CR's proficiency bonus. These are the same
ranges as `../../rpg-character-gen/references/npc-stat-blocks.md`'s "CR
Estimation Guidelines" table:

| CR | Prof Bonus | Approx AC | Approx HP | Approx Attack | Approx Damage/Round |
|---:|----------:|----------:|----------:|--------------:|--------------------:|
| 0 | +2 | 10-12 | 1-6 | +2-3 | 0-1 |
| 1/8 | +2 | 12-13 | 7-12 | +3 | 2-5 |
| 1/4 | +2 | 13 | 13-20 | +3-4 | 4-6 |
| 1/2 | +2 | 13 | 20-35 | +3-4 | 6-8 |
| 1 | +2 | 13-14 | 36-49 | +3-5 | 9-14 |
| 2 | +2 | 13-14 | 50-70 | +3-5 | 15-20 |
| 3 | +2 | 13-15 | 71-85 | +4-6 | 21-26 |
| 5 | +3 | 15-17 | 101-115 | +6-8 | 33-38 |
| 8 | +3 | 16-17 | 146-160 | +7-9 | 51-56 |
| 12 | +4 | 17-18 | 206-220 | +8-10 | 69-74 |
| 17 | +6 | 19-20 | 281-310 | +10-12 | 93-98 |
| 20 | +6 | 19-21 | 341-400 | +10-13 | 111-116 |

Pick a value inside the range, not just the midpoint every time — low-AC,
high-HP "bruiser" and high-AC, low-HP "skirmisher" builds at the same CR
should feel different.

## Ability Scores

Pick six ability scores that fit the monster's concept (a golem needs high
STR/CON and near-zero DEX/CHA; a specter needs the reverse), then run each
through `monster_statblock.py --score <score>` for its modifier — never
hand-compute `(score - 10) // 2`.

## Type, Size, and Special Abilities by CR Band

- **CR 0-2**: mundane or lightly magical creatures. 0-1 special abilities,
  no spellcasting, no legendary actions.
- **CR 3-8**: distinct tactical identity — 1-2 special abilities (a
  recharge breath weapon, a fear aura, resistance/immunity to a damage
  type), spellcasting only for concept-appropriate creatures (a hag, not a
  wolf).
- **CR 9-16**: multiple special abilities, spellcasting common for
  intelligent creatures, reactions (parry, redirect) start appearing.
- **CR 17+**: legendary-tier — multiple special abilities plus
  spellcasting or a signature multi-part action are expected, not
  optional, to justify the CR against a full-strength high-level party.

## Actions and Damage

- Give at least one action whose `damage` list has more than one entry
  (e.g. piercing + poison) once CR reaches 2+ — a single flat damage type
  reads as a placeholder monster.
- `hit_bonus` should track the CR's attack-bonus range from the table
  above, not the raw ability modifier alone (assume proficiency is
  already factored in).
- Total expected damage per round across all actions (assuming all hit)
  should land inside `damage_per_round_range` for the CR.

## Treasure and Notes

`treasure` and `notes` are optional — include them only when the
narrative context calls for guarding something specific, otherwise omit
both keys rather than writing "none."
```

- [ ] **Step 3: Write `evals/evals.json`**

Create `ai/skills/monster-generator/evals/evals.json`:

```json
{
  "skill_name": "monster-generator",
  "evals": [
    {
      "id": 0,
      "prompt": "Generate a CR 5 undead guardian for the crypt my party is exploring.",
      "expected_output": "A written draft at campaigns/<active-campaign>/_drafts/monster/<slug>.md with an undead-type stat block whose AC/HP/attack/damage fall within monster_statblock.py's CR 5 ranges, and all required frontmatter keys.",
      "files": [],
      "assertions": [
        { "name": "draft_written", "description": "A file exists at campaigns/<active-campaign>/_drafts/monster/<slug>.md" },
        { "name": "valid_frontmatter", "description": "Frontmatter includes layout, title, permalink, category, chapter, episode, scene, jumbo, thumb, portrait, tags, search, excerpt_separator, id, slug, name, type, size, ac, hp, abilities, challenge" },
        { "name": "cr_guidance_used", "description": "monster_statblock.py was invoked for CR 5 rather than hand-computed stats; AC/HP/attack fall within its returned ranges" },
        { "name": "fits_theme", "description": "type/description/special_abilities are specifically undead/crypt-themed, not generic" }
      ]
    },
    {
      "id": 1,
      "prompt": "Generate a monster for my campaign.",
      "expected_output": "No active campaign is set, so the skill reports the no_active_campaign error and tells the user to run scripts/use-campaign first, without writing any draft.",
      "files": [],
      "assertions": [
        { "name": "no_draft_written", "description": "No file is created under any campaigns/*/_drafts/monster/" },
        { "name": "clear_error", "description": "Response tells the user to run scripts/use-campaign, matching the no_active_campaign error message" }
      ]
    },
    {
      "id": 2,
      "prompt": "Generate a swamp beast for the party to fight, no CR given.",
      "expected_output": "No CR is mentioned, so the skill assumes CR 3, says so in its response, and still generates and writes a complete draft without blocking on a clarifying question.",
      "files": [],
      "assertions": [
        { "name": "states_assumption", "description": "Response explicitly states it assumed CR 3" },
        { "name": "no_blocking_question", "description": "The skill does not stop to ask the user for a CR before generating" },
        { "name": "draft_written", "description": "A monster draft is still written despite no CR being given" }
      ]
    }
  ]
}
```

- [ ] **Step 4: Validate the eval JSON parses**

Run: `python3 -c "import json; json.load(open('ai/skills/monster-generator/evals/evals.json'))" && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ai/skills/monster-generator/SKILL.md ai/skills/monster-generator/references/ ai/skills/monster-generator/evals/
git commit -m "$(cat <<'EOF'
feat(skills): add monster-generator skill

Generates a D&D 5e monster stat block matching _layouts/monster.html's
structured frontmatter fields exactly, grounded in monster_statblock.py's
CR guidance, writing directly into the active campaign's draft pipeline.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: `magic-generator` skill files

**Files:**
- Create: `ai/skills/magic-generator/SKILL.md`
- Create: `ai/skills/magic-generator/references/magic-item-building.md`
- Create: `ai/skills/magic-generator/evals/evals.json`

**Interfaces:**
- Consumes: `magic_item_rarity.py`'s CLI (`--party-level <n>` or `--rarity <name>`) from Task 3. `shared/write_draft.py`'s CLI contract (same as Task 4). The `magic-item` promotion mapping from Task 1 (so this skill's documented `scripts/promote-draft magic-item <slug>` step actually works). Optionally `shared/dnd5eapi_client.py`'s CLI (`python3 dnd5eapi_client.py magic-items/<index>`).
- Produces: nothing consumed by later tasks (this skill is a leaf).

- [ ] **Step 1: Write `SKILL.md`**

Create `ai/skills/magic-generator/SKILL.md`:

```markdown
---
name: magic-generator
description: Generate a D&D 5e magic item and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a magic item, artifact, enchanted weapon, or piece of loot for their campaign. Triggers on requests like "give my party a magic sword," "generate a rare wondrous item," or "I need a boss reward for the finale." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Magic Item Generator

Generate a level-appropriate, story-appropriate D&D 5e magic item and
write it as a draft in the active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve rarity and narrative context

- If the user states a rarity (e.g. "a rare wondrous item"), use it
  directly. If they state a party level instead, use that. If neither is
  given, assume a level 5 party and say so in your response — don't block
  on asking, unlike `encounter-generator`.
- Narrative context (what this item is, who made it, why the party is
  finding it) comes from whatever the user already said.

### Step 3: Compute rarity guidance

\`\`\`bash
python3 <skill-path>/scripts/magic_item_rarity.py --party-level <level>
\`\`\`

or, if the user gave an explicit rarity:

\`\`\`bash
python3 <skill-path>/scripts/magic_item_rarity.py --rarity <rarity>
\`\`\`

The party-level form returns `eligible_rarities`, a `recommended_rarity`,
and `typically_requires_attunement` per eligible rarity. The rarity form
returns that rarity's `minimum_level` and `typically_requires_attunement`.
Use `recommended_rarity` (party-level form) unless the narrative calls for
a lower-rarity item on purpose (not every found item needs to be the best
the party can handle). Don't invent a rarity outside what the script
confirms is level-appropriate.

### Step 4: Design the item

Read `references/magic-item-building.md` for property-budget guidance at
the chosen rarity, and attunement norms. Optionally look up an existing
SRD item for inspiration:

\`\`\`bash
python3 <repo-root>/shared/dnd5eapi_client.py magic-items/<index>
\`\`\`

(e.g. `magic-items/bag-of-holding`; skip this if you're inventing an
original item.)

### Step 5: Write the draft

Build the frontmatter with these exact keys (there is no existing FastAPI
generator for this kind — this schema is the standard for this skill):

\`\`\`json
{
  "layout": "reward",
  "title": "<title>",
  "permalink": "/magic-items/:slug",
  "category": "magic-item",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/reward-thumb.png",
  "portrait": "/assets/images/placeholders/reward-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": ""
}
\`\`\`

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Then write the body as Markdown prose covering: the item's name and
rarity, whether it requires attunement (and by whom, if restricted), its
mechanical properties, and flavor/history tied to the narrative context
from Step 2. Don't dump the raw rarity-guidance numbers into the body —
this is a narrative page for the DM to read at the table, not a data
sheet.

Pipe it to the shared writer:

\`\`\`bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
\`\`\`

Where `<json payload>` is:

\`\`\`json
{
  "kind": "magic-item",
  "campaign": "<active-campaign>",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
\`\`\`

Use the `<active-campaign>` value already resolved in Step 1 — don't rely
on `write_draft.py`'s `.active-campaign`/cwd-based auto-resolution, since
campaign directories are git submodules and a cwd inside one could resolve
the wrong repo root.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/magic-item/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft magic-item <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Rarity must match power level.** Always use
  `magic_item_rarity.py`'s guidance — a legendary-tier item handed to a
  level 3 party breaks the campaign's balance.
- **Story fit matters as much as rarity fit.** An item that doesn't
  connect to the narrative context (who made it, why it's here) reads as
  generic loot.
- **Give the item a limitation or cost**, not just a bonus — a charge
  limit, a quirk, a drawback on a failed save, or a reason it's dangerous
  to overuse — so it creates interesting choices at the table rather than
  being a flat upgrade.
```

- [ ] **Step 2: Write `references/magic-item-building.md`**

Create `ai/skills/magic-generator/references/magic-item-building.md`:

```markdown
# Magic Item Building Reference

Guidance for choosing rarity and budgeting properties once
`scripts/magic_item_rarity.py` confirms what's level-appropriate.

## Rarity by Party Level

| Rarity | Minimum Level | Typically Requires Attunement |
|---|---|---|
| Common | 1 | No |
| Uncommon | 1 | No |
| Rare | 5 | Yes |
| Very Rare | 11 | Yes |
| Legendary | 17 | Yes |

"Typically" means per-item, not universal — a +1 weapon (uncommon) never
requires attunement; a wondrous rare item sometimes doesn't either. Decide
per item, using the script's guidance as the default assumption rather
than an absolute rule.

## Property Budget by Rarity

- **Common**: a single minor, mostly non-combat effect (a self-lighting
  torch, a mess-kit that never needs cleaning). No numeric bonus.
- **Uncommon**: one clear combat or utility benefit — a flat +1 to
  attack/damage/AC/a save, or a single reusable limited-use effect (a
  handful of charges per day).
- **Rare**: a +1 or +2 numeric bonus *plus* one distinct secondary
  property (a triggered effect, a limited-use spell, a passive
  resistance) — not two full-strength benefits stacked freely.
- **Very Rare**: a +2 or +3 numeric bonus plus a meaningful secondary
  property, or two moderate secondary properties without a numeric bonus.
- **Legendary**: a +3 numeric bonus plus a signature, story-relevant
  property that could justify a whole quest arc on its own — this is the
  rarity where the item itself is a plot device, not just gear.

Don't stack two "Rare-tier" properties onto a Common item to make it feel
special — reach for the next rarity tier instead, using the party-level
guidance to confirm it's appropriate.

## Attunement and Limitations

Every item at Rare or above should have at least one of:
- An attunement requirement, optionally restricted to a class/alignment/
  race for a story reason.
- A charge limit or recharge condition (e.g. "3 charges, regains 1d3 at
  dawn").
- A drawback on overuse, a failed save, or a specific trigger (curses,
  backlash damage, an attention-drawing effect).

A magic item with no limitation of any kind is a power-creep risk
regardless of rarity — give the DM a lever to pull if the item turns out
to be too strong at the table.
```

- [ ] **Step 3: Write `evals/evals.json`**

Create `ai/skills/magic-generator/evals/evals.json`:

```json
{
  "skill_name": "magic-generator",
  "evals": [
    {
      "id": 0,
      "prompt": "My level 8 party just defeated a lich. Generate a rare magic item as their reward.",
      "expected_output": "A written draft at campaigns/<active-campaign>/_drafts/magic-item/<slug>.md for a rare item tied to the lich encounter, with a numeric bonus plus one secondary property, an attunement note, and all required frontmatter keys.",
      "files": [],
      "assertions": [
        { "name": "draft_written", "description": "A file exists at campaigns/<active-campaign>/_drafts/magic-item/<slug>.md" },
        { "name": "valid_frontmatter", "description": "Frontmatter includes layout, title, permalink, category, chapter, episode, scene, jumbo, thumb, portrait, tags, search, excerpt_separator, id, slug" },
        { "name": "rarity_guidance_used", "description": "magic_item_rarity.py was invoked for rare/level 8 rather than hand-picked, and the item's power level matches rare-tier guidance" },
        { "name": "fits_theme", "description": "Item name/flavor are specifically tied to the lich encounter, not generic" },
        { "name": "has_limitation", "description": "Body describes at least one limitation (attunement, charges, or a drawback)" }
      ]
    },
    {
      "id": 1,
      "prompt": "Generate a magic item for my campaign.",
      "expected_output": "No active campaign is set, so the skill reports the no_active_campaign error and tells the user to run scripts/use-campaign first, without writing any draft.",
      "files": [],
      "assertions": [
        { "name": "no_draft_written", "description": "No file is created under any campaigns/*/_drafts/magic-item/" },
        { "name": "clear_error", "description": "Response tells the user to run scripts/use-campaign, matching the no_active_campaign error message" }
      ]
    },
    {
      "id": 2,
      "prompt": "Generate a magic ring for the party to find, no level or rarity given.",
      "expected_output": "No level or rarity is mentioned, so the skill assumes a level 5 party, says so in its response, and still generates and writes a complete draft without blocking on a clarifying question.",
      "files": [],
      "assertions": [
        { "name": "states_assumption", "description": "Response explicitly states it assumed a level 5 party" },
        { "name": "no_blocking_question", "description": "The skill does not stop to ask the user for level/rarity before generating" },
        { "name": "draft_written", "description": "A magic item draft is still written despite no level/rarity being given" }
      ]
    }
  ]
}
```

- [ ] **Step 4: Validate the eval JSON parses**

Run: `python3 -c "import json; json.load(open('ai/skills/magic-generator/evals/evals.json'))" && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add ai/skills/magic-generator/SKILL.md ai/skills/magic-generator/references/ ai/skills/magic-generator/evals/
git commit -m "$(cat <<'EOF'
feat(skills): add magic-generator skill

Generates a D&D 5e magic item under the reused reward layout, grounded in
magic_item_rarity.py's DMG rarity-by-level guidance, writing directly into
the active campaign's draft pipeline. Completes Phase 1 of the AI Skills
initiative alongside encounter-generator, location-generator, and
monster-generator.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Full verification pass

Run every affected test suite together to confirm nothing regressed across the three new skills and the `services/llm_api` change.

**Files:** none (verification only).

**Interfaces:** none.

- [ ] **Step 1: Run the new skill test suites**

```bash
cd ai/skills/monster-generator && python3 -m pytest tests/ -v
cd ../magic-generator && python3 -m pytest tests/ -v
```

Expected: all tests from Tasks 2 and 3 pass (12 + 10 = 22 passed total).

- [ ] **Step 2: Run the existing skill test suites (regression check)**

```bash
cd ai/skills/encounter-generator && python3 -m pytest tests/ -v
```

Expected: all pre-existing tests still pass (no changes were made to `encounter-generator`).

- [ ] **Step 3: Run the shared module test suite (regression check)**

```bash
python3 -m pytest shared/tests/ -v
```

Expected: all pre-existing `write_draft.py` tests still pass (no changes were made to `shared/`).

- [ ] **Step 4: Run the full `services/llm_api` test suite**

```bash
cd services/llm_api && pytest
```

Expected: all tests pass, including the new `test_promotion_mapping.py` from Task 1 and every pre-existing test (no regressions from the one-line `PROMOTION_RULES` addition).

- [ ] **Step 5: Validate all three new evals.json files parse and match the existing skill's shape**

```bash
python3 -c "
import json
for name in ['location-generator', 'monster-generator', 'magic-generator']:
    path = f'ai/skills/{name}/evals/evals.json'
    data = json.load(open(path))
    assert data['skill_name'] == name, f'{path}: skill_name mismatch'
    assert len(data['evals']) >= 3, f'{path}: expected at least 3 evals'
    print(f'{path}: OK ({len(data[\"evals\"])} evals)')
"
```

Expected: three `OK` lines, one per skill, no assertion errors.

No commit for this task — it's a verification-only pass over work already committed in Tasks 1-6. If any step fails, fix the regression in the task that introduced it and re-run this task's steps from the top.
