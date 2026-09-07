# players-handbook Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `players-handbook` AI skill — the second Phase 2 skill of the AI Skills initiative — which answers player-facing D&D rules questions (actions/bonus actions/reactions from the player's seat, skill checks, spellcasting basics) from local reference tables (falling back to the existing shared, cached 2014 SRD API client for anything not covered locally) and can compile a fixed player quick-reference cheat-sheet into the active campaign's draft pipeline.

**Architecture:** Same shape as the already-shipped `dm-guide` skill, reusing its infrastructure with no new Python module: two condensed reference files (`player-actions.md`, `spellcasting-basics.md`) are the fast, offline, primary path for Q&A, with the existing `shared/dnd5eapi_client.py` (already endpoint-agnostic) as fallback for anything not covered locally, plus a `SKILL.md` tying the workflow together and an `evals.json` for skill-level testing. The cheat-sheet output is always compiled from the local reference files only (never API-fetched) and written via the existing `shared/write_draft.py`, using a new `playernote` Jekyll layout (this skill's one piece of new non-content code) that mirrors the existing `dmnote` layout but without its DM-only connotation.

**Tech Stack:** Markdown content files, a Jekyll HTML layout (Liquid templating, matching the repo's existing `_layouts/dmnote.html` pattern), JSON for the evals file. No new Python code.

**Spec:** [docs/superpowers/specs/2026-09-06-players-handbook-skill-design.md](../specs/2026-09-06-players-handbook-skill-design.md)

## Global Constraints

- No new Python module — `shared/dnd5eapi_client.py`'s `fetch()` is already generic across SRD endpoints (`spells/*`, `rules/*`, `equipment/*`, ...) and needs no changes for this skill to use it.
- The cheat-sheet Markdown body is fixed, campaign-agnostic content compiled only from `player-actions.md` and `spellcasting-basics.md` — never API-fetched, never campaign-tailored.
- Cheat-sheet frontmatter must use `layout: playernote` (new layout added by this plan), `category: players-handbook`, `permalink: /players-handbook/:slug`, and always overwrite `campaigns/<campaign>/_drafts/players-handbook/quick-reference.md` on every request (no promoted-page check).
- No active campaign → surface the same `no_active_campaign` error path as `dm-guide`/`encounter-generator` ("Run scripts/use-campaign first"). This applies only to the cheat-sheet workflow — the Q&A workflow has no campaign dependency.
- `playernote.html` must mirror `dmnote.html`'s structure exactly (same `side_by_side` base layout, same title/jumbo/content block shape) — the only difference is the file name/purpose, not the markup.

---

## Task 1: `playernote` Jekyll layout

**Files:**
- Create: `_layouts/playernote.html`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Task 3's `SKILL.md` cheat-sheet frontmatter, which sets `layout: playernote`): a Jekyll layout Jekyll can resolve by that name. No code interface — this is template markup only.

- [ ] **Step 1: Read the existing `dmnote` layout to confirm the exact structure to mirror**

Run: `cat _layouts/dmnote.html`

Expected output (for reference — this is the file this task's new layout must structurally match):

```html
---
layout: side_by_side
---

<!-- Additional dmnote-specific content can go here -->
<div class="phb">
    <div class="container">
        <div class="row">
            <div class="col-12 text-center">
                <h1>{{ page.title }}</h1>
            </div>
        </div>
        <div class="row">
            <div class="col-12">
                <div>{{ page.jumbo }}</div>
            </div>
        </div>
        <div class="row">
            {{ content }}
        </div>
    </div>
</div>
```

- [ ] **Step 2: Create `_layouts/playernote.html`**

Create `_layouts/playernote.html` with the same structure, substituting only the comment to describe this layout's own purpose:

```html
---
layout: side_by_side
---

<!-- Additional playernote-specific content can go here -->
<div class="phb">
    <div class="container">
        <div class="row">
            <div class="col-12 text-center">
                <h1>{{ page.title }}</h1>
            </div>
        </div>
        <div class="row">
            <div class="col-12">
                <div>{{ page.jumbo }}</div>
            </div>
        </div>
        <div class="row">
            {{ content }}
        </div>
    </div>
</div>
```

- [ ] **Step 3: Verify the Jekyll site still builds with the new layout present**

Run: `bundle exec jekyll build`
Expected: build succeeds with no errors (the layout isn't referenced by any page yet, so this just confirms it doesn't break the build by being present).

- [ ] **Step 4: Commit**

```bash
git add _layouts/playernote.html
git commit -m "feat(layouts): add playernote layout for player-facing reference pages"
```

---

## Task 2: players-handbook reference content

**Files:**
- Create: `ai/skills/players-handbook/references/player-actions.md`
- Create: `ai/skills/players-handbook/references/spellcasting-basics.md`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces (used by Task 3's `SKILL.md` workflow and Task 4's evals): condensed rules content Claude reads directly and (for the cheat-sheet path) renders verbatim into the draft body. No code interface.

- [ ] **Step 1: Write `player-actions.md`**

Create `ai/skills/players-handbook/references/player-actions.md`:

```markdown
# Player Actions Reference

Quick rulings for "what can I do on my turn" and "does this give me
advantage" questions from the player's seat — not a full rules reprint.
If a question isn't covered here, fall back to `dnd5eapi_client.py` (see
SKILL.md).

## Your Turn

On your turn you get one action, one move (up to your speed, which you
can split before/after your action), and one bonus action (only if a
feature or spell grants one) — in any order you like.

## Actions You Can Take

- **Attack** — make a melee or ranged attack.
- **Cast a Spell** — most spells with a casting time of "1 action."
- **Dash** — gain extra movement equal to your speed this turn.
- **Disengage** — your movement this turn doesn't provoke opportunity
  attacks.
- **Dodge** — until the start of your next turn, any attack roll against
  you has disadvantage if you can see the attacker, and you have
  advantage on Dexterity saving throws.
- **Help** — help another creature's ability check (they get advantage
  on their next check for that task) or help an ally's attack roll
  against a creature within 5 ft. of you (their next attack against that
  target has advantage), provided you're actually capable of assisting.
- **Hide** — make a Dexterity (Stealth) check to try to hide.
- **Ready** — pick a trigger and an action/movement to take when it
  happens; using it later takes your reaction.
- **Search** — make a Wisdom (Perception) or Intelligence
  (Investigation) check to find something.
- **Use an Object** — interact with a second object this turn beyond the
  one free interaction you already get (e.g. drawing a weapon,
  drinking a potion).

## Bonus Actions

You only have a bonus action if a specific class feature, spell, or
other effect grants one (e.g. a Rogue's Cunning Action, Two-Weapon
Fighting's off-hand attack, a spell that says "1 bonus action"). You get
at most one bonus action per turn no matter how many features would
grant one — pick which one to use.

## Reactions

You get one reaction per round, which refreshes at the start of your own
turn. You spend it on another creature's turn when its trigger occurs —
most commonly an opportunity attack (see below), or an action you
readied on your own prior turn.

## Opportunity Attacks

If a hostile creature you can see moves out of your reach (within 5 ft.,
or your weapon's reach) without using the Disengage action, you can use
your reaction to make one melee attack against it as it leaves. You
don't get one if the creature teleports, is forced to move (e.g.
shoved), or moves in a way that never leaves your reach.

## Ability Checks & Skills

A check succeeds if `d20 + ability modifier + proficiency bonus (if
you're proficient in the relevant skill) >= DC`. Your DM sets the DC;
typical DCs run from 5 (very easy) to 30 (nearly impossible), with 15 a
common "moderately hard" target.

## Advantage & Disadvantage

- Roll two d20s: take the higher for advantage, the lower for
  disadvantage.
- They never stack — any number of advantage sources plus any number of
  disadvantage sources still cancels down to a single net advantage,
  disadvantage, or (if they fully cancel) a flat roll.
- Ways you can gain advantage: an ally helps you, you attack a prone
  target in melee, you attack a target that can't see you.
- Ways you can end up with disadvantage: attacking a prone target at
  range, attacking while restrained or prone yourself, making a ranged
  attack while a hostile creature is within 5 ft. of you (unless a
  feature says otherwise), attacking at long range with a ranged weapon.
```

- [ ] **Step 2: Write `spellcasting-basics.md`**

Create `ai/skills/players-handbook/references/spellcasting-basics.md`:

```markdown
# Spellcasting Basics Reference

Quick rulings for "can I cast this" and "how does this spell mechanic
work" questions from the player's seat. If a question isn't covered
here (e.g. what a specific spell does), fall back to
`dnd5eapi_client.py` (see SKILL.md) to look up that spell.

## Spell Slots

Casting a leveled spell (not a cantrip) uses one spell slot of that
spell's level or higher — casting it using a higher-level slot generally
makes the spell more powerful ("upcasting"), per that spell's own
description. Cantrips (level 0 spells) never use a slot and can be cast
at will. Spell slots are expended when you cast the spell, and are
regained on a long rest (some class features regain some slots on a
short rest instead — check your class features).

## Casting Time

- **1 action**: the most common casting time — uses your action for the
  turn, same as any other action.
- **1 bonus action**: uses your bonus action instead, leaving your
  action free for something else (e.g. an attack, if a feature allows
  it).
- **1 reaction**: cast in response to a trigger the spell specifies
  (e.g. Shield), using your reaction for the round.
- **Longer casting times** (e.g. 1 minute, 10 minutes): you must spend
  the entire time casting, generally in a safe/uninterrupted setting,
  or the casting fails and the slot is wasted.

You can only cast one spell with a casting time other than a reaction
per turn — casting a second one that turn (even as a bonus action) isn't
allowed if you already cast a "1 action" spell that turn, and vice
versa.

## Components

A spell's description lists which of these it needs; missing a required
component (without a substitute like a spellcasting focus, where
allowed) means you can't cast it:

- **V (Verbal)**: you must be able to speak. Being silenced blocks this.
- **S (Somatic)**: you need a free hand to gesture. Both hands full
  (e.g. a two-handed weapon and no spellcasting focus) blocks this.
- **M (Material)**: you need the specified material(s), consumed if the
  spell says so — otherwise a spellcasting focus or component pouch
  substitutes for any material component that has no listed cost and
  isn't consumed.

## Concentration

Spells marked "Concentration" require you to actively concentrate to
keep their effect running:

- You can only concentrate on one such spell at a time — casting a
  second concentration spell ends the first one immediately.
- Taking damage while concentrating forces a Constitution saving throw
  (DC 10, or half the damage taken if higher) to maintain it.
- Being incapacitated, or reduced to 0 HP, ends concentration
  automatically.
- Concentration also ends if you willingly stop it, or (per most such
  spells) if you're no longer able to see/reach the target/area as the
  spell requires.

## Ritual Casting

A spell tagged "Ritual" can be cast without expending a spell slot by
taking 10 extra minutes beyond its normal casting time — but only if you
have that spell prepared/known specifically as available for ritual
casting (check your class's ritual-casting rules) and it's actually
tagged as a ritual spell.

## Spell Attack Rolls & Save DCs

- **Spell attack roll**: `d20 + spellcasting ability modifier +
  proficiency bonus`, compared against the target's AC, same as a
  weapon attack roll.
- **Spell save DC**: `8 + spellcasting ability modifier + proficiency
  bonus` — the target rolls against this DC for any saving throw the
  spell calls for.

## Known vs. Prepared Casters

- **Known casters** (e.g. Sorcerer, Bard, Warlock) can cast any spell
  on their fixed "known spells" list without changing it between casts.
- **Prepared casters** (e.g. Cleric, Druid, Wizard) choose a subset of
  their available spells to have "prepared" — usually re-chosen after a
  long rest — and can only cast spells currently prepared (cantrips are
  always available regardless of preparation).
```

- [ ] **Step 3: Commit**

```bash
git add ai/skills/players-handbook/references/player-actions.md ai/skills/players-handbook/references/spellcasting-basics.md
git commit -m "docs(skills): add players-handbook player-actions and spellcasting-basics references"
```

---

## Task 3: `SKILL.md` — the players-handbook skill definition

**Files:**
- Create: `ai/skills/players-handbook/SKILL.md`

**Interfaces:**
- Consumes: `shared/dnd5eapi_client.py` (pre-existing, from the `dm-guide` plan), `references/player-actions.md` and `references/spellcasting-basics.md` (Task 2), `shared/write_draft.py` (pre-existing, from the `encounter-generator` plan), `_layouts/playernote.html` (Task 1).
- Produces: the skill's triggering description and workflow — this is what Claude reads to decide when and how to use the skill. No code interface.

- [ ] **Step 1: Write the skill definition**

Create `ai/skills/players-handbook/SKILL.md`:

```markdown
---
name: players-handbook
description: Answer D&D 5e player-facing rules questions (actions/bonus actions/reactions on your turn, opportunity attacks, ability checks and advantage/disadvantage, spell slots, casting time, components, concentration, ritual casting, spell attack rolls and save DCs, known vs. prepared casters, and similar player-side rulings) and, on request, compile a player quick-reference cheat-sheet page into the active campaign. Use this skill whenever a player asks how their turn works, what their character can do, how a spellcasting mechanic works, or asks for a quick-reference sheet at the table. This is a rules-lookup skill for the player's perspective, not a DM adjudication tool (use dm-guide for that) and not a content generator — use encounter-generator/location-generator/monster-generator/rpg-character-gen instead for creating encounters, locations, monsters, or characters.
---

# Players Handbook

Answer D&D 5e rules questions from the player's perspective, and compile
a fixed player quick-reference cheat-sheet into the active campaign on
request.

## Workflow: Answering a Rules Question

### Step 1: Check local references first

Read `references/player-actions.md` (turn structure, actions, bonus
actions, reactions, opportunity attacks, ability checks, advantage &
disadvantage) and `references/spellcasting-basics.md` (spell slots,
casting time, components, concentration, ritual casting, spell attack
rolls & save DCs, known vs. prepared casters). If the question is
covered there, answer directly from that content — no network call
needed.

### Step 2: Fall back to the SRD API for anything not covered locally

If the local references don't cover the question, call the shared API
client:

```bash
python3 <repo-root>/shared/dnd5eapi_client.py <relevant-endpoint>
```

Pick `<relevant-endpoint>` based on the question — the 2014 SRD API
organizes content by resource type, so a specific spell is
`spells/<spell-slug>` (e.g. `spells/fireball`), a piece of equipment is
`equipment/<equipment-slug>`, and a rules section is
`rules/<rules-slug>`. If you're unsure of the exact endpoint slug, try
your best guess; on a 404 (`"not_found"`), try the resource type with no
sub-path (e.g. `spells`) to see the list of available entries, or answer
from your own best judgment instead of guessing repeatedly.

Answer the question using the JSON response.

### Step 3: If the API call fails, don't block the answer

If the client exits non-zero (its stdout is `{"error": {"code": "...",
"message": "..."}}`), tell the user the rules API couldn't be reached —
relay the error message plainly — and then still answer the question
from your own knowledge and best judgment. Never refuse to answer a
rules question just because the API lookup failed.

This entire workflow has no dependency on an active campaign — it works
the same with or without one set.

## Workflow: Compiling the Player Quick-Reference Cheat-Sheet

Triggered by requests like "give me a player quick reference" or
"compile the player handbook page."

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is
empty, stop and tell the user to run `scripts/use-campaign <name>` first
— don't guess a campaign, and don't write anything.

### Step 2: Compile the fixed content

Render **both** `references/player-actions.md` and
`references/spellcasting-basics.md` into one Markdown body, covering
every section in both files. This content is the same every time —
don't tailor it to the current campaign or fetch anything from the SRD
API for this path; the committed cheat-sheet should never depend on
network availability.

### Step 3: Write the draft

Build the frontmatter with these exact keys:

```json
{
  "layout": "playernote",
  "title": "Player Quick Reference",
  "permalink": "/players-handbook/:slug",
  "category": "players-handbook",
  "jumbo": "",
  "search": true,
  "excerpt_separator": ""
}
```

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.) `layout: playernote` uses this repo's
`_layouts/playernote.html`, a player-facing page layout.

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "players-handbook",
  "slug": "quick-reference",
  "title": "Player Quick Reference",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
```

This **always overwrites**
`campaigns/<campaign>/_drafts/players-handbook/quick-reference.md` —
there's no promoted-page check, so re-running this on a campaign that
already promoted a previous cheat-sheet will still overwrite the draft
(it won't touch anything already promoted to `_pages/`).

On success, tell the user the draft is ready and that
`scripts/promote-draft players-handbook quick-reference` will publish
it.

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
git add ai/skills/players-handbook/SKILL.md
git commit -m "feat(skills): define players-handbook skill workflow"
```

---

## Task 4: players-handbook evals

**Files:**
- Create: `ai/skills/players-handbook/evals/evals.json`

**Interfaces:**
- Consumes: nothing (content file describing expected end-to-end skill behavior, mirroring `ai/skills/dm-guide/evals/evals.json`'s shape).
- Produces: nothing consumed by later tasks — this is the last task in the plan.

- [ ] **Step 1: Write the evals file**

Create `ai/skills/players-handbook/evals/evals.json`:

```json
{
  "skill_name": "players-handbook",
  "evals": [
    {
      "id": 0,
      "prompt": "It's my turn in combat. My rogue already used their bonus action on Cunning Action to Disengage. Can I still take the Attack action normally?",
      "expected_output": "An answer explaining that a bonus action is independent of your action - using Cunning Action as your bonus action doesn't consume or restrict your action for the turn, so the Attack action is still available, sourced from references/player-actions.md without calling the SRD API.",
      "files": [],
      "assertions": [
        { "name": "answered_locally", "description": "The Bonus Actions section in references/player-actions.md is used; dnd5eapi_client.py is not invoked" },
        { "name": "mechanically_correct", "description": "Response confirms the action and bonus action are independent and both are usable on the same turn" }
      ]
    },
    {
      "id": 1,
      "prompt": "What exactly does the Fireball spell do - damage, area, save?",
      "expected_output": "An answer giving Fireball's damage, area of effect, and saving throw, sourced from calling dnd5eapi_client.py against the spells/fireball endpoint since specific spell details aren't in the local reference files, falling back to best judgment with a stated API-unreachable caveat only if the call fails.",
      "files": [],
      "assertions": [
        { "name": "api_fallback_used", "description": "dnd5eapi_client.py is called against a spells/* endpoint since spell-specific details are not in references/spellcasting-basics.md" },
        { "name": "graceful_fallback_if_used", "description": "If the API call failed, the response still answers the question and states the API was unreachable rather than refusing to answer" }
      ]
    },
    {
      "id": 2,
      "prompt": "Compile the player quick reference for my campaign.",
      "expected_output": "A draft written to campaigns/<active-campaign>/_drafts/players-handbook/quick-reference.md with layout: playernote frontmatter and a body covering every section from both player-actions.md and spellcasting-basics.md.",
      "files": [],
      "assertions": [
        { "name": "draft_written", "description": "A file exists at campaigns/<active-campaign>/_drafts/players-handbook/quick-reference.md" },
        { "name": "correct_layout", "description": "Frontmatter includes layout: playernote, category: players-handbook, permalink: /players-handbook/:slug" },
        { "name": "content_complete", "description": "Body includes content from both reference files' sections, not a partial subset" }
      ]
    },
    {
      "id": 3,
      "prompt": "Compile the player quick reference.",
      "expected_output": "No active campaign is set, so the skill reports the no_active_campaign error and tells the user to run scripts/use-campaign first, without writing any draft.",
      "files": [],
      "assertions": [
        { "name": "no_draft_written", "description": "No file is created under any campaigns/*/_drafts/players-handbook/" },
        { "name": "clear_error", "description": "Response tells the user to run scripts/use-campaign, matching the no_active_campaign error message" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add ai/skills/players-handbook/evals/evals.json
git commit -m "test(skills): add players-handbook evals"
```

---

## Final Verification

- [ ] **Run the Jekyll build to confirm the new layout and content don't break anything**

```bash
bundle exec jekyll build
```

Expected: build succeeds with no errors.

- [ ] **Sanity-check the SRD client is reachable from the new skill's expected working directory (no real network call)**

```bash
mkdir -p /tmp/players-handbook-smoke-test && cd /tmp/players-handbook-smoke-test
mkdir -p .cache/dnd5eapi
echo '{"index": "fireball", "name": "Fireball"}' > .cache/dnd5eapi/spells-fireball.json
git init -q
python3 <repo-root>/shared/dnd5eapi_client.py spells/fireball
cd - && rm -rf /tmp/players-handbook-smoke-test
```

Expected: prints `{"index": "fireball", "name": "Fireball"}` with no
network access attempted (the cache file satisfies the request) —
confirms `dnd5eapi_client.py` works unmodified for a `spells/*` endpoint,
not just the `rules/*` endpoints `dm-guide` exercises.

- [ ] **Verify all four task files exist**

```bash
ls _layouts/playernote.html \
   ai/skills/players-handbook/references/player-actions.md \
   ai/skills/players-handbook/references/spellcasting-basics.md \
   ai/skills/players-handbook/SKILL.md \
   ai/skills/players-handbook/evals/evals.json
```

Expected: all five paths print with no "No such file" errors.

---

## Self-Review Notes

- **Spec coverage:** New `playernote` layout (Task 1), local-first Q&A
  with generic-client API fallback across `spells/*`/`equipment/*`/`rules/*`
  (Task 3), fixed cheat-sheet content and layout (Task 3), no new Python
  module since `dnd5eapi_client.py` is already generic (confirmed by the
  Task 4 eval exercising a `spells/*` endpoint it wasn't originally
  written against), error handling for both workflows (Task 3), and
  testing via evals (Task 4) are all covered. The spec's "Out of Scope"
  items (changes to `dnd5eapi_client.py` itself, campaign-tailored
  cheat-sheets, character-sheet content, other Phase 1/3/4 skills) are
  intentionally not tasked here.
- **Placeholder scan:** No TBD/TODO markers; every step has runnable
  code or complete Markdown/HTML content.
- **Type consistency:** No new Python interfaces are introduced by this
  plan — `dnd5eapi_client.py`'s pre-existing `fetch(endpoint: str, *,
  cache_dir: Path | None = None) -> dict` and `Dnd5eApiError(code: str,
  message: str)` are referenced identically to how `dm-guide`'s
  `SKILL.md` already uses them, and `write_draft.py`'s JSON payload
  shape (`kind`, `slug`, `title`, `frontmatter`, `body`) matches both
  `dm-guide`'s and `encounter-generator`'s existing usage exactly.
