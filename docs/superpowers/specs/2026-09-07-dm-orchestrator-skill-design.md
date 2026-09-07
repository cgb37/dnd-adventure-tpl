# DM Orchestrator Skill (Batch Mode) — Design

## Context

This is Phase 3 of the AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md`), decomposed as
follows:

- **Phase 1 — Generator skills** (shipped): `encounter-generator`,
  `location-generator`, `monster-generator`, `magic-generator`. Each writes
  directly into the active campaign's draft pipeline via
  `shared/write_draft.py`.
- **Phase 2 — Reference skills** (shipped): `dm-guide`, `players-handbook`.
  Abbreviated rules/lookup skills for chat Q&A and cheat-sheet generation.
- **Phase 3 — `dm-orchestrator`, batch mode** (this spec): generates a
  campaign outline, calls Phase 1 skills to fill in content on request, and
  introduces the full campaign memory model referenced (but deliberately not
  built) by every Phase 1/2 spec.
- **Phase 4 — `dm-orchestrator`, live session mode**: interactive
  turn-by-turn DM loop (story hooks, puzzles, unreliable narrators,
  individual agendas) built on this phase's memory model. Out of scope here.

The project serves two distinct end users, and this phase must serve both:
a **DM** iteratively building a campaign (wants to see and edit the outline,
review generated content before running a session), and a **player** who
will experience the campaign through the future `dm-livesession` skill
(Phase 4) and must never see spoilers — not the outline, not generated
scene content, not even which scenes exist yet.

`dm-orchestrator` does not generate encounter/location/monster/magic-item
content itself. It orchestrates: it builds and maintains the campaign
outline and memory, and it invokes the four Phase 1 skills — following
their existing `SKILL.md` instructions the same way a human user would ask
for them directly — supplying richer narrative context than a human
typically would, drawn from memory. No Phase 1/2 skill's code changes as
part of this spec.

## File Layout

```
ai/skills/dm-orchestrator/
  SKILL.md
  scripts/
    campaign_memory.py    # read/write campaigns/<campaign>/campaign.yml
    outline_scope.py      # parse a scope phrase ("chapter 2", "the next part") against an outline
  references/
    outline-building.md   # pacing/sizing guidance, hook-planting, tagging scenes with `needs`
  evals/
    evals.json
  tests/
    test_campaign_memory.py
    test_outline_scope.py
```

Same shape as every Phase 1 skill: self-contained under `ai/skills/`, a
hand-rolled stdlib-only script per concern, a `references/` file for
judgement-heavy guidance, and `evals/evals.json` for behavior coverage.
`campaign_memory.py` mirrors `ai/skills/encounter-generator/scripts/party_state.py`'s
style — hand-rolled YAML parse/write via `read`/`write` CLI subcommands
emitting JSON — rather than reusing `shared/write_draft.py`, since
`campaign.yml` is orchestrator state, never a Jekyll draft and never
promoted.

Nothing in `shared/`, `party_state.py`, or the four Phase 1 skills' scripts
changes. `party.yml` stays exactly as it is — `dm-orchestrator` reads it via
the existing `party_state.py` CLI, the same way `encounter-generator` does.

## Campaign Memory: `campaign.yml`

Lives beside `party.yml`, at `campaigns/<campaign>/campaign.yml`, written by
`campaign_memory.py` (hand-rolled YAML, same rationale as `party_state.py`:
no PyYAML dependency, only the exact shapes below are ever produced or
parsed).

```yaml
mode: dm                       # dm | player — fixed for the campaign's lifetime
premise: "A cursed harvest festival draws travelers to a town that never lets them leave."
scope: "3 chapters, short"

outline:
  - chapter: "01"
    title: "The Festival Gates"
    episodes:
      - episode: "01"
        title: "Arrival"
        scenes:
          - scene: "01"
            premise: "The party arrives as the gates seal behind them."
            needs: [location]
            status: planned      # planned | filled
          - scene: "02"
            premise: "A frightened local begs them to find her missing brother."
            needs: [encounter]
            status: planned

threads:
  - id: missing-caravan
    summary: "A caravan vanished on the north road three days ago."
    status: introduced           # introduced | advancing | resolved

npcs:
  - name: "Captain Elena"
    role: "town guard captain"
    disposition: "suspicious of outsiders"
    last_seen: "chapter 01, episode 01"

content_index:
  - beat: "01.01.02"             # chapter.episode.scene
    kind: encounter
    slug: "missing-brother-ambush"
    path: "campaigns/<campaign>/_drafts/encounter/missing-brother-ambush.md"
```

Field notes:

- `mode` gates every user-facing behavior described below and cannot be
  changed once set — `campaign_memory.py`'s write path rejects a `mode`
  value that differs from what's already on disk, so this is enforced at
  the script level, not left to `SKILL.md` prose.
- `needs` is a list (a scene can require more than one Phase 1 skill, e.g.
  `[location, encounter]`). Valid values: `location`, `encounter`,
  `monster`, `magic`. Reference skills (`dm-guide`, `players-handbook`) are
  never tagged in `needs` and are never invoked by `dm-orchestrator` — per
  the concept doc they're player/DM rules lookups, not scene content
  generators.
- A scene's `status` becomes `filled` once every `needs` entry has a
  matching `content_index` row (matched on `(beat, kind)`).
- `content_index` treats `(beat, kind)` as a unique key: writing a second
  entry for the same key replaces it rather than appending a duplicate,
  even if a caller bug tries.
- `threads`/`npcs` are best-effort running context, not a strict schema
  Claude must fully populate — they exist so later generation can reference
  earlier content, not as a data-integrity contract.

## Workflow 1: Outline Generation

Triggered by a request like *"start a new campaign about a cursed harvest
festival, 3 chapters"*.

1. **Resolve active campaign** from `.active-campaign`. If missing, stop and
   tell the user to run `scripts/use-campaign` first — identical to every
   existing skill. `dm-orchestrator` never creates a campaign; campaign
   submodules are added to `.gitmodules` and checked out entirely outside
   any skill's scope, the same assumption `party_state.py` already makes.
2. **Check for an existing outline** via `campaign_memory.py read`. If one
   exists, stop and ask whether to replace it or use a different campaign —
   never silently overwrite.
3. **Resolve `mode`** — infer from phrasing ("I'm running this for my
   group" → `dm`; "generate a campaign for me to play" → `player`); ask
   directly only if genuinely ambiguous: *"Are you running this campaign as
   the DM, or is this for you to play through yourself?"*
4. **Resolve party context** by reusing `party_state.py read` unchanged
   (ask once and write it if missing, exactly as `encounter-generator`
   does).
5. **Resolve premise + scope** from what the user already said; only ask if
   either is genuinely absent.
6. **Design the outline** — read `references/outline-building.md` for
   pacing guidance (episodes per chapter, scenes per episode, when to plant
   vs. pay off a thread). Produce chapters → episodes → scenes, each scene
   with a one-line premise and a `needs` tag inferred from that premise at
   build time (e.g. "ambushed at the bridge" → `needs: [encounter]`). Seed
   `threads` with any hooks introduced; leave `npcs`/`content_index` empty.
7. **Write to memory** via `campaign_memory.py write`.
8. **Report to the user, mode-gated:**
   - `mode: dm` — show the full outline (chapter/episode/scene titles and
     one-line premises, not raw YAML) and say `dm-orchestrator` can fill in
     any chapter/episode once approved, or take edits first.
   - `mode: player` — no chapter/episode/scene titles or premises are ever
     shown. Response is limited to confirmation: *"Your campaign is ready.
     dm-livesession will guide you through it — no spoilers here."* There is
     no human checkpoint on outline quality in this mode; it relies entirely
     on `references/outline-building.md` guidance and model judgement.

No drafts are written in this workflow — only `campaign.yml`.

## Workflow 2: Fill

Triggered by a request like *"generate chapter 2"*, *"fill in episode
1.3"*, or (in `player` mode) *"get the next part ready"*.

1. **Resolve active campaign + read `campaign.yml`.** No `outline` yet →
   stop, tell the user to generate one first.
2. **Resolve scope** via `outline_scope.py`, which parses the request
   against the outline structure: `"chapter 2"` → all scenes under chapter
   `02`; `"episode 1.3"` → chapter `01`/episode `03`'s scenes; `"the next
   part"` → the first `status: planned` scene(s) in outline order. A scope
   that matches nothing in the outline is the one place fill asks a
   clarifying question in **both** modes — naming which chapters/episodes
   exist doesn't spoil anything.
3. **Filter already-filled scenes** — for each matched scene, skip any
   whose every `needs` entry already has a `content_index` row. Report the
   skip (`dm`: named; `player`: a count only, e.g. "2 already ready").
4. **For each remaining scene, for each tag in `needs`:** build inline
   context from `campaign.yml` — the scene's own premise, `threads` at
   `introduced`/`advancing` status, and `npcs` with a `last_seen` at or
   before this chapter — and invoke the matching Phase 1 skill
   (`encounter-generator`, `location-generator`, `monster-generator`, or
   `magic-generator`) with that context plus party info, exactly as if a
   user had asked for it directly but with richer narrative detail
   supplied.
5. **Immediately after each successful generation** (not batched to the end
   of the fill request): record a `content_index` row, flip the scene's
   `status` to `filled` once all its `needs` are covered, best-effort update
   `npcs`/`threads` if the generated content plausibly introduces a new
   named NPC or advances/resolves a thread, and write `campaign_memory.py`
   back to disk. Writing incrementally per scene (rather than once at the
   end) means a mid-batch failure never leaves memory lagging behind what's
   actually on disk — every draft that was successfully written is always
   reflected in `campaign.yml`, whether or not later scenes in the same
   request fail.
6. **If a generator invocation fails for one scene**, do not add a
   `content_index` row for it, do not abort the remaining scenes in scope,
   and report the failure at the end.
7. **Final report, mode-gated:**
   - `dm` — every scene generated (title + kind + draft path), every scene
     skipped (named), every scene that failed (named + reason). This is a
     review list for the DM to check via `scripts/promote-draft`.
   - `player` — counts only: generated / already-ready / failed. No titles,
     premises, or paths, ever.

`dm-orchestrator` never runs `git` inside the campaign submodule and never
calls `scripts/promote-draft` itself — drafts are left for the user to
review and promote, identical to how every Phase 1 skill already behaves.

## Error Handling

| Case | Handling |
|---|---|
| No active campaign | Stop; tell the user to run `scripts/use-campaign` first. |
| `outline` already exists, user asks to generate a new one | Stop; name the existing premise; ask to confirm replacing it or switch campaigns. |
| Fill requested with no `outline` yet | Stop; tell the user to generate an outline first. |
| Scope matches nothing in the outline | Stop; relay valid scopes (`dm`: list them; `player`: "that part doesn't exist yet" only). |
| A Phase 1 skill invocation fails for one scene mid-batch | Skip that scene's `content_index` row, continue with the rest of the batch, write memory incrementally (per Workflow 2 step 5), report the failure at the end. |
| `campaign.yml` fails to parse | Relay a clear `invalid_campaign_memory`-style error and stop — never guess-repair the file, matching `write_draft.py`'s existing error posture. |
| User tries to change `mode` after outline creation | Refuse at the script level; explain mode is fixed for the campaign's lifetime; point to starting a new campaign for the other mode. |
| Duplicate/conflicting `content_index` writes | `(beat, kind)` is a unique key in `campaign_memory.py`'s write path — a repeat write replaces rather than appends. |

All errors surface to the user exactly as they do in every existing skill —
relayed directly, no silent retry, no guessed fix.

## Testing

Follows the exact conventions of `test_party_state.py`/
`test_encounter_budget.py`: direct-import unit tests for pure functions
plus CLI round-trip tests via `subprocess.run`. No new test framework.

`test_campaign_memory.py`:
- Round-trip write/read of a full structure (outline + threads + npcs +
  content_index) — exact equality.
- Missing file → `read` returns `{"found": false}`.
- Malformed file → `read` fails clearly rather than returning a
  partial/wrong structure.
- `content_index` write with a repeated `(beat, kind)` key replaces, never
  duplicates.
- Writing a different `mode` onto an existing campaign is rejected.
- CLI shape: `write`/`read` subcommands round-trip via `subprocess.run`.

`test_outline_scope.py`:
- Exact matches: `"chapter 2"`, `"episode 1.3"`, `"scene 01.02.01"` resolve
  to the right beat(s) against a fixed sample outline.
- `"everything in chapter 1"` resolves to every scene under chapter `01`.
- `"the next part"` resolves to the first `status: planned` scene in
  outline order.
- No-match input (e.g. `"chapter 9"` against a 3-chapter outline) returns an
  explicit not-found result rather than raising or guessing.
- Each matched scene's current `status` is reported correctly so the fill
  workflow can filter on it (the scope resolver itself does not implement
  the skip logic — that's Workflow 2 step 3's responsibility).

**Regression check:** re-run `shared/tests/`, and the `tests/` suites for
`encounter-generator`, `monster-generator`, `magic-generator` — all should
be unaffected, since nothing in this design touches `shared/`,
`party_state.py`, or any Phase 1 skill's code.

**Not covered by automated tests** (same posture as every existing skill):
the quality of generated outlines and injected context is judged by
`evals/evals.json` scenarios, not unit tests — e.g. "premise + 3-chapter
scope produces a coherent outline with sensible `needs` tags," and
critically, "`player`-mode outline and fill responses never echo scene
titles, premises, or paths into chat." That last scenario is the spoiler
guarantee for the player-facing use case and should be treated as a
release-blocking eval, not a nice-to-have.

## Out of Scope (deferred to Phase 4 or later)

- `dm-livesession` (Phase 4) — the interactive turn-by-turn loop that
  actually delivers `player`-mode content to the player without spoilers.
  This spec only guarantees that outline/fill responses never leak
  spoilers in chat; it does not implement session delivery.
- Teaching `dm-guide`/`players-handbook` or any Phase 1 skill to read
  `campaign.yml` directly — `dm-orchestrator` injects relevant context
  inline per invocation instead, so no shipped skill needs to change.
- Editing an existing outline in place (adding/removing/reordering
  chapters after generation) beyond the "replace the whole outline"
  confirmation in Workflow 1 step 2.
- Multi-campaign or cross-campaign memory (threads/NPCs shared across
  separate campaign submodules).
- Auto-committing or auto-promoting generated drafts — identical to every
  existing skill, this remains a manual step via `scripts/promote-draft`.
