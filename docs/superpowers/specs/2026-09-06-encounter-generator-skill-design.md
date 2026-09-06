# Encounter Generator Skill — Design

## Context

This is Phase 1 of a larger AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md`), decomposed as
follows:

- **Phase 1 — Generator skills** (parallel, independent): `encounter-generator`,
  `location-generator`, `monster-generator`, `magic-generator`. Each follows
  the existing `ai/skills/rpg-character-gen` pattern (SKILL.md + references/ +
  structured output), CR/level-aware. **This spec covers the first of these,
  `encounter-generator`, which establishes the shared pattern.**
- **Phase 2 — Reference skills**: `dm-guide`, `players-handbook`. Abbreviated
  rules/lookup skills, different shape than the generators.
- **Phase 3 — `dm-orchestrator`, batch mode**: generates a campaign outline,
  calls Phase 1 skills to fill in content, introduces the full campaign
  memory model.
- **Phase 4 — `dm-orchestrator`, live session mode**: interactive turn-by-turn
  DM loop (story hooks, puzzles, unreliable narrators, individual agendas)
  built on the Phase 3 memory model.

Unlike `rpg-character-gen` (which outputs standalone JSON for a person to
paste), `encounter-generator` writes directly into the campaign draft
pipeline, the same target the existing FastAPI generator
(`services/llm_api/src/llm_api/generators/encounter.py`) writes to. A future
task will align that FastAPI generator to match the richer output this skill
produces — out of scope here.

## File Layout

```
ai/skills/_shared/
  write_draft.py          # shared: build frontmatter, compute deterministic id, write .md draft

ai/skills/encounter-generator/
  SKILL.md
  scripts/
    encounter_budget.py   # party level+size+difficulty -> XP budget, per-monster CR suggestions
  references/
    encounter-building.md # XP thresholds by level, multi-monster multiplier, terrain/tactics guidance
  evals/
    evals.json
```

`_shared/` sits alongside per-skill directories. Later Phase 1 skills
(`location-generator`, `monster-generator`, `magic-generator`) import the same
`write_draft.py` rather than reimplementing draft-writing logic. This is the
one intentional cross-skill dependency — everything else about each skill
stays self-contained, matching the `rpg-character-gen` convention.

## Party State (low-friction inputs)

To avoid asking for party level/size on every request, each campaign gets a
small state file:

```
campaigns/<campaign>/party.yml
```

```yaml
level: 5
size: 4
composition:
  - class: bard
  - class: barbarian
  - class: wizard
  - class: cleric
```

This is a **lightweight seed**, not the full campaign-memory system planned
for Phase 3 (`dm-orchestrator`). Phase 3 may extend or absorb this file into
a richer memory model; this spec only commits to level/size/composition.

## Workflow

1. Resolve active campaign from `.active-campaign` (same convention as
   `active_campaign.get_active_campaign()` in the FastAPI service). If
   missing, surface the same guidance: "run `scripts/use-campaign` first."
2. Read `campaigns/<campaign>/party.yml` for level/size/composition. If
   missing or incomplete, ask once, then write the file so future runs don't
   ask again.
3. Difficulty defaults to `medium` unless the user specifies otherwise.
   Narrative context (where/why this fight happens) comes from whatever the
   user already said in the request; only ask if genuinely absent (e.g. a
   bare "generate an encounter").
4. Run `scripts/encounter_budget.py --level N --party-size N --difficulty X`
   → a deterministic XP budget plus a CR spend-down suggestion, computed from
   `references/encounter-building.md`'s tables.
5. Claude selects/reskins monsters against that budget — pulling from
   `rpg-character-gen/references/npc-stat-blocks.md`'s CR table where it
   fits, inventing appropriately-costed creatures otherwise — and writes the
   narrative, terrain, and tactical notes to fit the story context given.
6. Compose frontmatter using the same required keys as the existing
   `EncounterDraft.required_yaml_keys()` (`layout`, `title`, `permalink`,
   `category`, `chapter`, `episode`, `scene`, `jumbo`, `thumb`, `portrait`,
   `tags`, `search`, `excerpt_separator`, `id`, `slug`) plus a Markdown body.
7. Call `_shared/write_draft.py` with `kind="encounter"`, campaign, slug,
   title, frontmatter, body → writes
   `campaigns/<campaign>/_drafts/encounter/<slug>.md`, matching the exact
   format `drafts.write_draft()` produces today (front-matter block, `# Title`,
   body), ready for `scripts/promote-draft`.
8. The deterministic id uses the same formula as the FastAPI service:
   `uuid5(UUID_NAMESPACE, f"{kind}:{campaign}:{slug}")`, so ids stay
   consistent regardless of which path (skill or API) generated a given
   draft.

## Output Schema (encounter JSON, before rendering to Markdown)

```json
{
  "title": "Encounter title",
  "slug": "kebab-slug",
  "difficulty": "easy | medium | hard | deadly",
  "xp_budget": 0,
  "party_context": { "level": 0, "size": 0 },
  "setting": "Where this happens, tied to the story",
  "monsters": [
    {
      "name": "...",
      "cr": "1/4",
      "count": 1,
      "role": "brute | skirmisher | controller | ...",
      "notes": "reskin/tactics for this fight"
    }
  ],
  "tactics": "How the encounter plays out, environmental features, escalation",
  "treasure": "optional loot/reward tied to the CR budget",
  "tags": ["..."]
}
```

This is rendered into the Markdown body as narrative/tactical prose — not a
raw data dump. `xp_budget` and `party_context` are internal bookkeeping used
to sanity-check the encounter, not necessarily surfaced verbatim to players.

## Error Handling

- No active campaign → surface the same error message path uses today
  (`no_active_campaign`, "Run scripts/use-campaign first"). Don't guess a
  campaign.
- `party.yml` missing or partial → ask once, then persist it. Never silently
  assume level/size.
- `write_draft.py` failures (e.g. can't create `_drafts/` dir) surface the
  underlying error rather than failing silently, matching
  `drafts.write_draft()`'s existing behavior.

## Testing

- `scripts/encounter_budget.py` is a pure calculator (inputs → XP numbers),
  unit-testable directly, same as `rpg-character-gen/scripts/dice_roller.py`.
- `ai/skills/_shared/write_draft.py` gets its own test since every Phase 1
  skill will depend on it — a bug there breaks all of them.
- Skill-level testing follows the existing convention:
  `ai/skills/encounter-generator/evals/evals.json`, mirroring the shape of
  `rpg-character-gen/evals/evals.json` (prompt → expected output →
  assertions). Minimum coverage:
  - A normal request with an existing `party.yml`.
  - A request with no active campaign (expect the guidance message, no
    draft written).
  - A request where `party.yml` doesn't exist yet (expect one clarifying
    question, then a `party.yml` written for next time).

## Out of Scope (deferred to later phases)

- Aligning the existing FastAPI `encounter.py` generator to this richer
  schema/output.
- The full campaign memory model (Phase 3) — `party.yml` is a narrow seed,
  not a general-purpose memory store.
- `location-generator`, `monster-generator`, `magic-generator` — each gets
  its own brainstorm once this pattern is validated, reusing
  `_shared/write_draft.py`.
- `dm-guide`, `players-handbook`, `dm-orchestrator` (Phases 2–4).
