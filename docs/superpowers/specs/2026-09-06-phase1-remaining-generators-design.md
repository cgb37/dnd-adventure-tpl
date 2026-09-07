# Phase 1 Remaining Generator Skills — Design (location, monster, magic)

## Context

Phase 1 of the AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md` and
`docs/superpowers/specs/2026-09-06-encounter-generator-skill-design.md`) is
`encounter-generator`, `location-generator`, `monster-generator`,
`magic-generator`. `encounter-generator` is built and validates the shared
pattern: `SKILL.md` + `scripts/` + `references/` + `evals/evals.json`,
resolving the active campaign, and writing drafts via `shared/write_draft.py`.

This spec covers the three remaining Phase 1 skills. They are independent,
parallel, and share essentially all their infrastructure with
`encounter-generator` — the only real per-skill decisions are output schema,
the domain-specific script, and the reference doc — so one spec covers all
three, but each ships as its own self-contained skill directory and can be
implemented/tested/shipped independently.

Unlike `encounter-generator` (which writes a prose Markdown body under a
generic layout), `location-generator` and `monster-generator` target Jekyll
layouts (`_layouts/location.html`, `_layouts/monster.html`) that render
**structured frontmatter fields** directly (tables, lists, nested objects).
This was confirmed against the real layouts and real content examples:
`campaigns/rpg-theForsakenCrown/_pages/locations/whispering-woods.html` and
`.../_pages/monsters/green-dragon-wyrmling.html`. `magic-generator` has no
existing layout or FastAPI generator precedent; it reuses the existing,
currently-unused `reward.html` layout with a prose body, matching
`encounter-generator`'s simpler shape.

## Shared File Layout (per skill)

```
ai/skills/<name>-generator/
  SKILL.md
  scripts/
    <domain>_<calc>.py   # pure calculator, unit-testable, same shape as encounter_budget.py
  references/
    <domain>-building.md
  evals/
    evals.json
```

All three reuse `shared/write_draft.py` (frontmatter render + deterministic
id + file write) via the same sys.path bootstrap `encounter-generator`
established (walk up to `.git`, add `repo_root / "shared"` to `sys.path`, or
invoke as a subprocess CLI — same convention). `monster-generator` and
`magic-generator` may additionally use the existing
`shared/dnd5eapi_client.py` to pull a canonical SRD monster/item as an
optional reskin base.

## Shared Workflow Shape

1. Resolve the active campaign from `.active-campaign` (identical to
   `encounter-generator` Step 1 — same error message on missing/empty).
2. Resolve any optional calibration context (party level, if relevant to the
   skill — see below). None of these three skills *require* the full
   `party.yml` composition the way `encounter-generator` does; only level is
   ever used, and only to calibrate difficulty/rarity/CR guidance, never to
   block generation.
3. Run the skill's domain script for any numbers that must be exact
   (DC ranges, CR-to-stat guidance, rarity-by-level) — Claude never eyeballs
   these, same rule as `encounter_budget.py`.
4. Claude authors the content against the skill's reference doc, fit to
   whatever story/narrative context the user already gave.
5. Build frontmatter with the skill's exact required keys (below), pipe the
   JSON payload to `shared/write_draft.py` exactly as `encounter-generator`
   does, using the campaign resolved in step 1 (not write_draft.py's own
   auto-resolution).
6. Report the draft path and id, and mention `scripts/promote-draft <kind>
   <slug>`.

## Shared Error Handling

Identical to `encounter-generator`:
- No active campaign → relay `no_active_campaign` guidance verbatim, never
  guess a campaign.
- `write_draft.py` failures → relay the underlying error, never retry
  silently or guess a fix.
- Missing optional calibration context (e.g. no party level) → proceed with
  a reasonable stated default (see per-skill sections) rather than blocking;
  these are calibration hints, not hard requirements like `encounter-generator`'s
  party composition.

## location-generator

**Output schema** — matches `_layouts/location.html` field-for-field:

```json
{
  "name": "...",
  "type": "... (e.g. \"Enchanted Forest\")",
  "description": "prose",
  "challenges": {
    "traps": "multi-line string, one `- Name: description` bullet per line",
    "ambushes": "same shape",
    "puzzles": "same shape",
    "hazards": "same shape"
  },
  "secrets": ["..."],
  "plot_hooks": ["..."],
  "npcs": [{"name": "...", "description": "..."}],
  "environmental_features": ["..."],
  "additional_notes": "prose string (NOT a list — the layout renders it as a scalar with `{{ page.additional_notes }}`; the real example file stores it as a list, which is inconsistent with the layout and not to be copied)"
}
```

`challenges.*` fields are stored as YAML block-scalar strings whose *content*
is a Markdown-style bullet list (matching `whispering-woods.html`'s
convention exactly, since `location.html`'s Liquid does
`{{ ... | split: '\n' }}` on them, not YAML list iteration).

**Frontmatter base keys** (same convention as `encounter-generator`):
`layout: location`, `permalink: /locations/:slug`, `category: location`,
plus the usual `chapter`/`episode`/`scene`/`jumbo`/`thumb`/`portrait`/`tags`/
`search`/`excerpt_separator` (id/slug filled in by `write_draft.py`).

**No script.** No numeric budget system is needed for a location. Party
level, if the user or an existing `party.yml` supplies it, is used only to
scale trap/hazard DCs and damage dice per the reference doc's guidance — it
is optional context, read but never required, and location-generator never
writes `party.yml` (only `encounter-generator` owns writing that file).

**Reference:** `references/location-building.md` — DC/severity scaling
bands by party level (reusing the spirit of `encounter-building.md`'s
threshold tables), guidance for tying secrets/plot hooks/NPCs to the active
campaign's story, and environmental-feature ideas by terrain type.

## monster-generator

**Output schema** — matches `_layouts/monster.html` field-for-field (per
`green-dragon-wyrmling.html`):

```json
{
  "name": "...",
  "description": "prose",
  "type": "... (Beast, Dragon, Undead, ...)",
  "size": "Tiny | Small | Medium | Large | Huge | Gargantuan",
  "ac": {"value": 0, "type": "natural armor | ..."},
  "hp": "N (XdY + Z)",
  "hp_dice": "XdY",
  "speed": "30 ft., fly 60 ft., ...",
  "abilities": {
    "strength": {"score": 0, "modifier": "+0"},
    "dexterity": {"score": 0, "modifier": "+0"},
    "constitution": {"score": 0, "modifier": "+0"},
    "intelligence": {"score": 0, "modifier": "+0"},
    "wisdom": {"score": 0, "modifier": "+0"},
    "charisma": {"score": 0, "modifier": "+0"}
  },
  "saving_throws": [{"name": "dexterity", "modifier": "+0"}],
  "skills": "Perception +4, Stealth +3",
  "senses": "darkvision 60 ft., passive Perception 14",
  "languages": ["..."],
  "challenge": "N (XP)",
  "special_abilities": [{"name": "...", "description": "..."}],
  "spellcasting": {
    "ability": "... (omit block entirely if non-caster)",
    "dc": 0,
    "slots": {"level_1": 0},
    "spells": {"cantrips": ["..."], "level_1": ["..."]}
  },
  "actions": [{
    "name": "...", "type": "Melee Weapon Attack", "hit_bonus": "+0",
    "reach": "5 ft.", "target": "one target",
    "damage": [{"type": "piercing", "dice": "1d10 + 2", "avg": 7}]
  }],
  "reactions": [{"name": "...", "description": "..."}],
  "treasure": "optional prose",
  "notes": "optional prose"
}
```

Non-caster monsters omit the `spellcasting` key entirely (the layout renders
blank headers either way — a known, accepted cosmetic gap, not addressed by
this spec). `reactions`, `treasure`, `notes` are omitted when not
applicable.

**Frontmatter base keys:** `layout: monster`, `permalink: /monsters/:slug`,
`category: monster`, plus the usual set.

**Script:** `scripts/monster_statblock.py` — given `--cr <CR>`, returns the
DMG CR-guideline numbers (approx AC/HP/attack-bonus/damage-per-round range,
proficiency bonus) from the same table as
`rpg-character-gen/references/npc-stat-blocks.md`'s "CR Estimation
Guidelines", plus an ability-score-to-modifier helper
(`score_to_modifier(score) -> "+N"/"-N"`). Claude never computes these by
hand — same rule as `encounter_budget.py`.

**Reference:** `references/monster-building.md` — how to turn the CR
numbers into a full stat block (choosing type/size/abilities to fit a CR
band, when to add special abilities/legendary actions/spellcasting as CR
rises, damage-type variety for encounter design).

**Optional:** use `shared/dnd5eapi_client.py` (`monsters/{index}`) to pull a
canonical SRD monster as a reskin base when the user names one (e.g. "a
shadow-touched dire wolf").

## magic-generator

No existing FastAPI generator (`dispatch.py`'s `SUPPORTED_KINDS` has no
`"magic"` entry) or dedicated Jekyll layout exists for magic items. The only
precedent is the generic, currently-unused `reward.html` layout
(`_frontmattertpls/reward.yml`, `campaigns/.../_pages/rewards/reward-*.md`),
which is a bare `title`/`jumbo`/`thumb`/`search` stub with no structured
body. This spec **reuses `reward.html`** rather than building a new Jekyll
layout (out of scope) — matching `encounter-generator`'s simpler
prose-Markdown-body shape, not the structured-frontmatter shape of location/
monster.

**Frontmatter base keys:** `layout: reward`, `permalink: /magic-items/:slug`,
`category: magic-item`, plus the usual `chapter`/`episode`/`scene`/`jumbo`/
`thumb`/`portrait`/`tags`/`search`/`excerpt_separator` set.

**Body:** Markdown prose covering item name, rarity, attunement requirement
(if any), mechanical properties, and flavor/history — narrative page for a
DM to read at the table, same spirit as `encounter-generator`'s body
guidance ("don't dump raw budget numbers, write prose").

**Script:** `scripts/magic_item_rarity.py` — given `--party-level <N>` (or
an explicit `--rarity` override), returns the DMG rarity-by-level guidance
(common/uncommon/rare/very rare/legendary) and typical attunement
expectations at that rarity. Claude never guesses rarity-vs-level
appropriateness by eye.

**Reference:** `references/magic-item-building.md` — rarity table,
attunement norms, and a property-budget guide (how many/how strong bonuses
are appropriate at each rarity) to avoid overpowered items.

**Optional:** use `shared/dnd5eapi_client.py` (`magic-items/{index}`) to
pull an existing SRD item as inspiration/reskin base.

## Testing

- Each domain script (`monster_statblock.py`, `magic_item_rarity.py`) gets a
  direct unit test — pure calculator, same shape as
  `shared/tests/` for `encounter_budget.py`. `location-generator` has no
  script, so no corresponding test.
- Each skill gets `evals/evals.json` mirroring
  `encounter-generator/evals/evals.json`'s shape (prompt → expected output →
  assertions), minimum coverage:
  - A normal request with an active campaign.
  - A request with no active campaign (expect the guidance message, no
    draft written).
  - (`monster-generator`, `magic-generator` only) A request with no party
    level available (expect a stated default, not a blocking question —
    unlike `encounter-generator`, these skills don't gate on party info).

## Out of Scope

- Aligning the existing FastAPI `location.py`/`monster.py` generators
  (currently `TBD`-stub, mock-provider-only) to these richer schemas.
- A FastAPI route/generator for magic items — `dispatch.py`'s
  `SUPPORTED_KINDS` is unchanged by this spec.
- A new dedicated magic-item Jekyll layout — `reward.html` is reused as-is.
- Fixing `additional_notes`'s list-vs-scalar inconsistency in the existing
  `whispering-woods.html` example content.
- `dm-orchestrator` (Phases 3–4) and any campaign memory model.
- Consolidating the pre-existing `dice_roller.py` /
  `services/llm_api/.../drafts.py` duplication (already noted as
  out-of-scope in the `encounter-generator` spec).
