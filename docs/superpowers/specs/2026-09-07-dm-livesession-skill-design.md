# DM Livesession Skill — Design

## Context

This is Phase 4 of the AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md`), building on
Phase 3's memory model
(`docs/superpowers/specs/2026-09-07-dm-orchestrator-skill-design.md`):

- **Phase 1 — Generator skills** (shipped): `encounter-generator`,
  `location-generator`, `monster-generator`, `magic-generator`.
- **Phase 2 — Reference skills** (shipped): `dm-guide`, `players-handbook`.
- **Phase 3 — `dm-orchestrator`, batch mode** (shipped): builds and
  maintains `campaign.yml` (outline + threads + npcs + `content_index`),
  invokes Phase 1 skills to fill scenes on request.
- **Phase 4 — `dm-livesession`** (this spec): delivers a campaign
  turn-by-turn, live. Two independent audiences, matching `campaign.yml`'s
  `mode`:
  - **`player` mode** — the solo player who generated their own campaign
    to play through themselves. dm-livesession is their DM: it narrates
    scenes, reacts to their actions, and must never spoil anything ahead
    of where they've actually reached.
  - **`dm` mode** — the DM running a live session for other human players.
    dm-livesession is a co-pilot: a stateless query/lookup tool the DM
    consults mid-session ("what's next," "remind me who this NPC is,"
    "roll initiative for these monsters"). The DM already sees everything
    in `dm` mode — there is no spoiler rule here.

dm-livesession never generates encounter/location/monster/magic-item
content itself, and never writes `campaign.yml` — that file stays
exclusively owned by `dm-orchestrator`. In `player` mode, when a scene
needs content that hasn't been generated yet, dm-livesession invokes
`dm-orchestrator`'s existing fill workflow (not the Phase 1 generator
skills directly) and re-reads `campaign.yml` afterward. `dm` mode never
triggers generation at all — a DM running a live session is expected to
have already filled what they need via `dm-orchestrator` ahead of time.

## File Layout

```
ai/skills/dm-livesession/
  SKILL.md
  scripts/
    session_state.py    # read/write campaigns/<campaign>/session.yml (player mode only)
    dice.py              # general NdM+K notation roller (initiative, damage, checks)
  references/
    live-narration.md   # story hooks, puzzles, unreliable narrators, NPC agendas — judgement guidance
  evals/
    evals.json
  tests/
    test_session_state.py
    test_dice.py
```

Same shape as every existing skill: self-contained under `ai/skills/`, a
hand-rolled stdlib-only script per concern, a `references/` file for
judgement-heavy guidance, `evals/evals.json` for behavior coverage.
`session_state.py` mirrors `ai/skills/dm-orchestrator/scripts/campaign_memory.py`'s
style exactly — hand-rolled YAML parse/write via `read`/`write` CLI
subcommands emitting JSON, no PyYAML dependency.

Nothing in `dm-orchestrator`, `shared/`, `party_state.py`, or any Phase 1/2
skill changes. `campaign.yml`'s schema is untouched — no new fields are
added to it for this phase. Any narrative richness dm-livesession needs
(NPC agendas, unreliable-narrator texture) is derived live, at
narration time, from what's already in `campaign.yml` (`role`,
`disposition`) plus judgement — never persisted back into it.

## Two Workflows, One Skill

Both workflows live under one `SKILL.md`, branching on `campaign.yml`'s
`mode` field (read via `dm-orchestrator`'s existing
`campaign_memory.py read`, unchanged) exactly the way `dm-orchestrator`
itself branches on `mode`:

- **Workflow 1 — Player Session** (`mode: player`): stateful. Owns a new
  file, `session.yml`, exclusively.
- **Workflow 2 — DM Co-pilot** (`mode: dm`): stateless. Read-only queries
  over `campaign.yml`, `content_index`, generated drafts, and `party.yml`.
  Never reads or writes `session.yml`.

A campaign's `mode` is fixed for its lifetime (enforced by
`campaign_memory.py`), so a given campaign only ever exercises one of
these two workflows — dm-livesession itself does not need to guard against
a campaign switching modes mid-story, but it does need to refuse an
obviously mismatched request (see Error Handling).

## Session Memory: `session.yml` (player mode only)

Lives beside `campaign.yml` and `party.yml`, at
`campaigns/<campaign>/session.yml`, written by `session_state.py`.

```yaml
current_position:
  beat: "01.01.02"              # chapter.episode.scene, matches campaign.yml's beat format

event_log:
  - beat: "01.01.01"
    summary: "Party arrived as the gates sealed; agreed to help the frightened local find her brother."

delivered_beats: ["01.01.01"]   # scenes actually experienced live in a session
```

Field notes:

- `current_position` is the single bookmark: the next beat the player has
  not yet resolved. dm-livesession never narrates ahead of it.
- `event_log` is a short, DM-style recap — one summary sentence per
  resolved beat, written by Claude, not a raw transcript. It exists so a
  later session ("remind me what happened last time") has continuity
  without re-reading `campaign.yml`'s spoiler-bearing premises.
- `delivered_beats` is deliberately distinct from `campaign.yml`'s
  `status: filled`. `filled` means content was *generated*; `delivered`
  means the player actually *played through* it live. A beat can be
  `filled` (dm-orchestrator pre-generated it) but not yet `delivered`.
- `session.yml` is small on purpose — it is a bookmark plus a log, not a
  duplicate of `campaign.yml`'s outline/threads/npcs. Everything else
  needed to narrate is re-read from `campaign.yml` fresh each turn.
- On a brand-new campaign with no `session.yml` yet, treat this as
  `current_position` = the outline's first scene, empty `event_log`, empty
  `delivered_beats` — created on first write, not required to pre-exist.

## Workflow 1: Player Session

Triggered by any message in a `player`-mode campaign once an outline
exists — "let's play," a stated in-character action, or simply continuing
a prior session.

1. **Resolve active campaign.** Read `.active-campaign`; if missing, stop
   and tell the user to run `scripts/use-campaign` first.
2. **Read `campaign.yml`** via `campaign_memory.py read`. No outline yet →
   stop, tell the user to generate one via `dm-orchestrator` first.
   Confirm `mode: player` — see Error Handling for a mode mismatch.
3. **Read `session.yml`** via `session_state.py read`. Missing → treat as
   first-ever session (position = outline's first scene, empty log).
4. **Check the current beat's readiness.** If any tag in the current
   scene's `needs` lacks a matching `content_index` entry in
   `campaign.yml`, invoke `dm-orchestrator`'s fill workflow scoped to just
   that beat (never the Phase 1 generator skills directly — dm-livesession
   does not generate content itself), then re-read `campaign.yml`. If the
   fill call fails, see Error Handling — do not narrate a scene with
   missing content.
5. **Narrate the scene.** Use the beat's generated content
   (location/encounter/monster/magic drafts referenced by
   `content_index`) plus `references/live-narration.md` for story hooks,
   puzzle delivery, NPC voice, and unreliable-narrator technique. Never
   reveal any beat beyond `current_position` — no titles, premises, or
   `needs` tags for future scenes, matching `dm-orchestrator`'s existing
   player-mode spoiler rule.
6. **React to the player's action:**
   - **On-script** (the action resolves or meaningfully advances the
     current beat): narrate the outcome, append a summary to `event_log`,
     add the beat to `delivered_beats`, advance `current_position` to the
     next `planned` scene in outline order, write `session.yml`.
   - **Off-script** (the player does something the outline didn't
     anticipate — ignores a hook, attacks an unintended NPC, wanders off
     the planned path): improvise the consequence narratively using
     judgement and `references/live-narration.md`. Do not call
     `dm-orchestrator` to patch the outline, and do not advance
     `current_position` or write `session.yml` — state stays put until the
     scene resolves back onto or near a planned beat.
7. **Recap requests** ("what happened last time," "remind me where we
   are") are answered from `session.yml`'s `event_log`/`current_position`
   only — never by reading ahead in `campaign.yml`'s outline.

## Workflow 2: DM Co-pilot

Triggered by any query in a `dm`-mode campaign during or around a live
session — "what's next," "remind me who Captain Elena is," "roll
initiative for these three monsters."

1. **Resolve active campaign + read `campaign.yml`.** No outline yet →
   stop, tell the user to generate one via `dm-orchestrator` first.
   Confirm `mode: dm` — see Error Handling for a mismatch.
2. **Answer directly from existing data** — no spoiler restriction applies
   in `dm` mode:
   - "What's next" → the next `planned` scene(s) in outline order, by
     title and premise.
   - NPC lookups → the matching `npcs` entry.
   - Content lookups → the relevant generated draft via `content_index`.
   - Ad-hoc dice requests (initiative, damage, a skill check for an NPC)
     → the new `scripts/dice.py`, a general `NdM+K` notation roller.
     `shared/dice_roller.py` only generates ability scores and cannot
     parse arbitrary dice notation, so this skill ships its own
     self-contained roller instead. This is a calculator call, not
     persisted state — no combat tracker, no initiative order maintained
     across turns.
3. **Never write anything.** `session.yml` does not exist for `dm`-mode
   campaigns; this workflow never creates or touches it.

## Error Handling

| Case | Handling |
|---|---|
| No active campaign | Stop; tell the user to run `scripts/use-campaign` first. |
| No `outline` in `campaign.yml` yet | Stop; tell the user to generate one via `dm-orchestrator` first. |
| Player-mode request against a `dm`-mode campaign, or vice versa | Stop; state the campaign's actual mode; do not attempt to serve the wrong workflow. |
| Current beat needs generation and the `dm-orchestrator` fill call fails | Stall gracefully in-narrative (e.g. "you pause at the door") rather than breaking the fourth wall; do not advance `current_position` or write `session.yml`. |
| `session.yml` missing on first-ever player session | Not an error — default to the outline's first scene, empty log; created on first write. |
| `session.yml` fails to parse | Relay a clear error and stop, same posture as `campaign_memory.py` with a malformed `campaign.yml` — never guess-repair. |
| Off-script player action | Not an error — improvise narratively per Workflow 1 step 6; no structural write. |
| DM-mode query with no matching data (e.g. NPC name not found) | Say so plainly; no spoiler concern in this mode, so the response can be direct. |

## Testing

Follows the exact conventions of `test_campaign_memory.py`: direct-import
unit tests for pure functions plus CLI round-trip tests via
`subprocess.run`. No new test framework.

`test_session_state.py`:
- Round-trip write/read of a full structure (`current_position`,
  `event_log`, `delivered_beats`) — exact equality.
- Missing file → `read` returns a first-scene default (not an error).
- Malformed file → `read` fails clearly rather than returning a
  partial/wrong structure.
- Appending to `event_log`/`delivered_beats` via `write` extends rather
  than overwrites prior entries.
- CLI shape: `write`/`read` subcommands round-trip via `subprocess.run`.

**Regression check:** re-run `shared/tests/` and `dm-orchestrator`'s test
suite (`test_campaign_memory.py`, `test_outline_scope.py`) — both should
be unaffected, since nothing in this design touches `dm-orchestrator`'s
code or `campaign.yml`'s schema.

**Not covered by automated tests** (same posture as every existing
skill): narration quality is judged by `evals/evals.json`, not unit tests.
Two scenarios should be treated as release-blocking, mirroring
`dm-orchestrator`'s spoiler eval:
- Player-mode narration of beat N never reveals beat N+1's (or later)
  title, premise, or `needs` tags.
- An off-script player action gets improvised in-character, never
  refused, railroaded back on-script, or answered with a meta "that's not
  part of the outline."

## Out of Scope

- **Live combat mechanics** (initiative order, HP/condition tracking,
  turn prompts) — dm-livesession stays narrative-only for combat in both
  modes. `dm`-mode dice rolls are ad-hoc calculator calls, not persisted
  combat state. A structured combat tracker is deferred to a later phase
  if ever needed.
- **On-the-fly generation bypassing `dm-orchestrator`** — dm-livesession
  never calls the Phase 1 generator skills directly; all generation goes
  through `dm-orchestrator`'s fill workflow, even mid-session.
- **Live outline editing** — off-script play never causes
  `dm-orchestrator` to insert or restructure outline scenes mid-session.
  The outline is fixed once generated; only `session.yml`'s bookmark and
  log move.
- **`campaign.yml` schema changes** — no new fields (e.g. NPC `agenda`,
  per-thread `revealed` flags) are added to `campaign.yml` for this phase.
  Narrative richness is derived live from existing fields, not persisted.
- **`session.yml` for `dm` mode** — the co-pilot workflow is entirely
  stateless; it never creates or reads a session file. The human DM
  remains the source of truth for what actually happened at the table.
- **Multi-player-mode sessions** — `player` mode assumes a single solo
  player experiencing their own campaign, consistent with how
  `dm-orchestrator` frames `player` mode. Multiple simultaneous players
  in one `player`-mode campaign is not addressed here.
