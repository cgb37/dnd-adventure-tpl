---
name: dm-livesession
description: Run a live D&D 5e session turn-by-turn on top of an existing dm-orchestrator campaign. In a player-mode campaign, narrate scenes and react to the solo player's actions with a strict spoiler guarantee - nothing beyond the current bookmarked position is ever revealed. In a dm-mode campaign, act as a stateless co-pilot for a human DM running a live session for other players - answer "what's next," NPC lookups, content lookups, and ad-hoc dice rolls (initiative, damage, skill checks). Use this skill whenever someone wants to actually play through a campaign turn-by-turn, or wants live lookups/rolls during a session they're running. Never generates content itself - unprepped player-mode scenes trigger dm-orchestrator's fill workflow first.
---

# DM Livesession

Deliver an existing `dm-orchestrator` campaign live, turn-by-turn. This
skill never builds an outline and never generates encounter, location,
monster, or magic-item content itself - all of that already happened (or
happens on demand, via `dm-orchestrator`) before this skill narrates or
answers anything.

## Read This First: Mode Rules

Every campaign has a `mode`, fixed for its lifetime by `dm-orchestrator`:

- **`player`** — Workflow 1 applies. You are the solo player's DM. A
  strict spoiler guarantee applies: **never reveal any beat beyond
  `session.yml`'s `current_position`** - no title, premise, or `needs` tag
  for a future scene, under any circumstances.
- **`dm`** — Workflow 2 applies. You are a stateless co-pilot for a human
  DM running a live session for other people. There is no spoiler
  restriction - the DM already sees everything in this mode.

If a request doesn't match the campaign's actual mode (e.g. someone asks
for a co-pilot dice roll on a `player`-mode campaign, or a solo-play
narration on a `dm`-mode one), stop and say which mode this campaign
actually is - never silently serve the other workflow.

## Workflow 1: Player Session

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If missing, stop and tell the
user to run `scripts/use-campaign <name>` first.

### Step 2: Read campaign.yml, redacted

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign> --redact
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate a campaign via `dm-orchestrator` first. Confirm `mode` is
`player` - if it's `dm`, stop and say so (see Mode Rules).

The redacted read gives you the outline's chapter/episode/scene numbering
with each scene's `needs`/`status`, and `content_index` reduced to
`(beat, kind)`. That is everything the rest of this workflow needs
structurally; it never reveals a title or premise.

### Step 3: Read session.yml

```bash
python3 <skill-path>/scripts/session_state.py read --campaign <active-campaign>
```

If it returns `{"found": false}`, this is the first-ever session for this
campaign. Resolve the outline's first scene as the starting position by
resolving scope against the redacted outline from Step 2:

```bash
echo '<redacted outline json>' | python3 <repo-root>/ai/skills/dm-orchestrator/scripts/outline_scope.py "chapter 1"
```

Take the first scene in the result as `current_position`. Otherwise, use
`session.yml`'s existing `current_position`.

### Step 4: Check the current beat's readiness

Find the current beat's scene in the redacted outline (matching
`current_position`'s `beat`). For every tag in that scene's `needs`, check
whether `content_index` already has a matching `(beat, kind)` row.

If anything is missing, invoke the `dm-orchestrator` skill to fill just
this beat - a request like "fill in scene `<beat>`" - the same way a human
user would ask for it. Never invoke `encounter-generator`,
`location-generator`, `monster-generator`, or `magic-generator` directly.

If the fill fails, stall gracefully in-narrative (e.g. "you pause at the
door for a moment") rather than breaking the fourth wall, and stop - do
not advance `current_position` or write `session.yml`. Otherwise, re-run
Step 2's redacted read to confirm the beat is now covered before
continuing.

### Step 5: Read the current beat's content, unredacted

Only once Step 4 confirms the current beat is ready:

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign>
```

From the full structure, extract only what this beat needs into a fresh
working note: the current scene's `premise`, its `content_index` entries'
draft paths (read those files), every thread in `threads` at `introduced`
or `advancing` status, and every NPC in `npcs` whose `last_seen` is at or
before this beat's chapter. Then disregard everything else in that read -
no other scene's title, premise, or `needs` tag from this response may
reach anything you say, in this turn or any later one.

### Step 6: Narrate

Using the content gathered in Step 5 plus `references/live-narration.md`
for hooks, puzzle pacing, NPC agenda/unreliable-narrator judgement, and
the spoiler boundary, narrate the scene and respond to whatever the player
says next.

### Step 7: React to the player's action

- **On-script** (the action resolves or meaningfully advances the current
  beat): determine the next planned scene by resolving `"the next part"`
  against the redacted outline (same CLI as Step 3), then write:

  ```bash
  echo '{"current_position": {"beat": "<next beat>"}, "event_log": [{"beat": "<current beat>", "summary": "<one-sentence recap>"}], "delivered_beats": ["<current beat>"]}' | python3 <skill-path>/scripts/session_state.py write --campaign <active-campaign>
  ```

- **Off-script** (the player does something the outline didn't
  anticipate): improvise the consequence per `references/live-narration.md`.
  Do not call `dm-orchestrator` to edit the outline, and do not write
  `session.yml` - `current_position` stays where it is until play resolves
  back onto a planned beat.

### Step 8: Recap requests

Answer "what happened last time" / "where are we" purely from
`session.yml`'s `event_log` and `current_position` - never from the
outline beyond that point.

## Workflow 2: DM Co-pilot

Stateless. Never reads or writes `session.yml`.

### Step 1: Resolve the active campaign and read campaign.yml

Same active-campaign resolution as Workflow 1, Step 1. Then read the full
(non-redacted) memory immediately - there is no spoiler concern in `dm`
mode:

```bash
python3 <repo-root>/ai/skills/dm-orchestrator/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate a campaign via `dm-orchestrator` first. Confirm `mode` is
`dm` - if it's `player`, stop and say so (see Mode Rules).

### Step 2: Answer the query directly

- **"What's next"**: resolve `"the next part"` against the outline (same
  `outline_scope.py` CLI as Workflow 1), report the matched scene(s) by
  title and premise.
- **NPC lookup**: find the matching entry in `npcs` and report it.
- **Content lookup**: find the matching `content_index` entry and read
  that draft file directly.
- **Rules/monster lookup for something not already generated**: query
  `shared/dnd5eapi_client.py`, e.g.
  `python3 <repo-root>/shared/dnd5eapi_client.py monsters/goblin`.
- **Ad-hoc dice roll** (initiative, damage, a skill check): run
  `python3 <skill-path>/scripts/dice.py "<notation>"`, e.g.
  `python3 <skill-path>/scripts/dice.py "1d20+3"`. This is a stateless
  single-roll calculator call - no initiative order or combat state is
  tracked across turns.
- **No match** (e.g. an NPC name that doesn't exist): say so plainly.
  There is no spoiler concern in this mode, so be direct.

### Step 3: Never write anything

This workflow never creates, reads, or modifies `session.yml`, and never
writes `campaign.yml`.

## Error Handling

| Case | Handling |
|---|---|
| No active campaign | Stop; tell the user to run `scripts/use-campaign` first. |
| No `outline` in `campaign.yml` yet | Stop; tell the user to generate one via `dm-orchestrator` first. |
| Request's implied workflow doesn't match the campaign's actual `mode` | Stop; state the campaign's actual mode; do not serve the wrong workflow. |
| Current beat needs generation and the `dm-orchestrator` fill fails | Stall gracefully in-narrative; do not advance `current_position` or write `session.yml`. |
| `session.yml` missing on first-ever player session | Not an error - default to the outline's first scene, empty log; created on first write. |
| `session.yml` fails to parse (`invalid_session_state`) | Relay the error and stop - never guess-repair. |
| Off-script player action | Not an error - improvise per Workflow 1 Step 7; no structural write. |
| DM-mode query with no matching data | Say so plainly - no spoiler concern in this mode. |
| Invalid dice notation | Relay `dice.py`'s `invalid_dice_notation` error and ask for a valid expression (e.g. "1d20+3"). |
