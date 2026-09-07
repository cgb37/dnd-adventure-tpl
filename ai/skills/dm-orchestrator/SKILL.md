---
name: dm-orchestrator
description: Generate and maintain a D&D 5e campaign outline (chapters/episodes/scenes), and fill in that outline's content by invoking the encounter-generator, location-generator, monster-generator, and magic-generator skills. Use this skill whenever someone wants to start a new campaign, plan out a campaign's structure, or asks to "generate chapter 2," "fill in the next part," or "get my campaign ready to play." Distinguishes DM users (who see and approve the outline and generated content) from player users (who must get zero spoilers - no outline, scene, or draft details are ever shown in chat). This is Phase 3 "batch mode"; live turn-by-turn session delivery is a separate future skill (dm-livesession).
---

# DM Orchestrator (Batch Mode)

Maintain a campaign's outline and generated content by orchestrating the
Phase 1 generator skills. This skill never generates encounter, location,
monster, or magic-item content itself — it invokes those skills the same
way a human user would ask for them, supplying richer narrative context
than a human typically would.

## Read This First: Mode Rules

Every campaign has a `mode`, set once at outline creation and fixed for the
campaign's lifetime:

- **`dm`** — the user is running this campaign for others. Show the full
  outline, ask for approval/edits, and report exactly what was generated
  (titles, kinds, draft paths) after every fill request.
- **`player`** — the user will experience this campaign themselves, later,
  through the `dm-livesession` skill. **Never show outline content, scene
  premises, chapter/episode/scene titles, or draft file paths in chat under
  any circumstances in this mode.** Responses are limited to confirmations
  and counts (e.g. "Your campaign is ready," "2 scenes generated, 1 already
  ready"). If you catch yourself about to describe what a scene is about in
  `player` mode, stop — that is a spoiler.

Never allow a user to change an existing campaign's `mode`.
`scripts/campaign_memory.py`'s write path enforces this and returns a
`mode_immutable` error if you try — relay that error rather than working
around it.

## Workflow 1: Generate an Outline

Triggered by requests like "start a new campaign about a cursed harvest
festival, 3 chapters" or "generate a campaign for me to play, 1 chapter."

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If missing or empty, stop and
tell the user to run `scripts/use-campaign <name>` first — don't guess.
`dm-orchestrator` never creates a campaign; campaign submodules are added
to `.gitmodules` and checked out entirely outside this skill's scope.

### Step 2: Check for an existing outline

Run:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns a structure with a non-empty `outline` (not `{"found":
false}`), stop. Tell the user a campaign already exists (name its premise)
and ask whether to replace it or use a different campaign. Never overwrite
silently.

### Step 3: Resolve mode

Infer from phrasing: "I'm running this for my group" → `dm`; "generate a
campaign for me to play" → `player`. Ask directly only if genuinely
ambiguous: "Are you running this campaign as the DM, or is this for you to
play through yourself?"

### Step 4: Resolve party context

Run the existing party-state script (unchanged, shared with
`encounter-generator`):

```bash
python3 <repo-root>/ai/skills/encounter-generator/scripts/party_state.py read --campaign <active-campaign>
```

If missing, ask once for level/size/composition and write it via that same
script's `write` subcommand, exactly as `encounter-generator` does.

### Step 5: Resolve premise and scope

Take both directly from what the user already said. Only ask if either is
genuinely absent (e.g. a bare "start a new campaign").

### Step 6: Design the outline

Read `references/outline-building.md` for sizing, pacing, and `needs`-
tagging guidance. Produce chapters → episodes → scenes. Every scene gets a
one-line `premise` and a `needs` list (`location`, `encounter`, `monster`,
`magic`, any combination, or `[]`) inferred from that premise. Every scene
starts with `status: planned`. Seed `threads` with any hooks the outline
introduces. Leave `npcs` and `content_index` empty — nothing has been
generated yet.

### Step 7: Write to memory

Build the full structure (`mode`, `premise`, `scope`, `outline`, `threads`,
`npcs: []`, `content_index: []`) and write it:

```bash
echo '<json payload>' | python3 <skill-path>/scripts/campaign_memory.py write --campaign <active-campaign>
```

On a `mode_immutable` error, relay it directly — this shouldn't happen in
this workflow (Step 2 already checked for an existing outline), so treat it
as a signal something changed concurrently and re-read before retrying.

### Step 8: Report to the user (mode-gated)

- **`dm`**: show the outline — every chapter/episode/scene title and
  one-line premise, in order — as readable prose or a nested list, not raw
  YAML. Say the user can ask for edits, or ask `dm-orchestrator` to fill in
  any chapter/episode once they're happy.
- **`player`**: show nothing about the outline's content. Respond only:
  "Your campaign is ready. dm-livesession will guide you through it — no
  spoilers here." There is no edit loop in this mode.

## Workflow 2: Fill In Content

Triggered by requests like "generate chapter 2," "fill in episode 1.3," or
(in `player` mode) "get the next part ready."

### Step 1: Resolve active campaign and read memory

Same active-campaign resolution as Workflow 1, Step 1. Then:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign>
```

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate an outline first.

### Step 2: Resolve scope

Pass the outline and the user's scope phrase to the resolver:

```bash
echo '<outline json>' | python3 <skill-path>/scripts/outline_scope.py "<scope phrase>"
```

If `matches` is `null`, the scope didn't match anything in the outline.
This is the one place fill asks a clarifying question in **both** modes —
naming which chapters/episodes exist doesn't spoil anything. In `dm` mode,
list the valid chapters/episodes; in `player` mode, say "that part doesn't
exist yet" without listing titles.

### Step 3: Filter already-filled scenes

For each matched scene, check `content_index` for a row matching
`(beat, kind)` for every entry in that scene's `needs`. If every `needs`
entry (including an empty list) is already covered, skip the scene. Track
how many were skipped.

### Step 4: Generate remaining scenes

For each remaining scene, for each tag in its `needs` list:

1. Build inline narrative context from memory: the scene's own `premise`,
   every thread in `threads` with `status` `introduced` or `advancing`, and
   every NPC in `npcs` whose `last_seen` is at or before this scene's
   chapter.
2. Invoke the matching skill with that context plus the resolved party
   info, as if a user had asked for it directly but with this richer
   detail supplied:
   - `needs` entry `encounter` → invoke `encounter-generator`
   - `needs` entry `location` → invoke `location-generator`
   - `needs` entry `monster` → invoke `monster-generator`
   - `needs` entry `magic` → invoke `magic-generator`
3. **Immediately after that invocation succeeds** (before moving to the
   next `needs` entry or scene): record a `content_index` row (`beat`,
   `kind`, `slug`, `path` — read the path from the invoked skill's
   response), update the scene's `status` to `filled` if every `needs`
   entry for it is now covered, best-effort update `npcs`/`threads` if the
   generated content plausibly introduces a new named NPC or advances/
   resolves a thread, and write memory back:

   ```bash
   echo '<updated campaign.yml json>' | python3 <skill-path>/scripts/campaign_memory.py write --campaign <active-campaign>
   ```

   Writing after every successful generation (not once at the end of the
   whole fill request) means a later failure in the same batch never
   leaves memory behind what's actually on disk.
4. If an invocation fails, do not record a `content_index` row for it, do
   not abort the rest of the batch, and note the failure for the final
   report.

### Step 5: Report to the user (mode-gated)

- **`dm`**: list every scene generated (title, kind, draft path), every
  scene skipped (named, "already generated"), and every scene that failed
  (named, with why). This is the DM's review list before running
  `scripts/promote-draft` on anything they like.
- **`player`**: counts only — "X generated, Y already ready, Z couldn't be
  generated." No titles, premises, or paths, ever.

Never call `scripts/promote-draft` yourself, and never run `git` inside the
campaign submodule — drafts are left for the user to review and promote,
exactly as every Phase 1 skill already behaves.

## Error Handling

- No active campaign → stop, tell the user to run `scripts/use-campaign`
  first. Never guess a campaign.
- Outline already exists (Workflow 1) → stop, confirm before replacing.
- No outline yet (Workflow 2) → stop, tell the user to generate one first.
- Scope matches nothing (Workflow 2) → ask a clarifying question — the only
  question fill ever asks in `player` mode.
- A Phase 1 skill invocation fails for one scene → skip it, continue the
  rest of the batch, report the failure at the end.
- `campaign_memory.py` reports an error (`mode_immutable`,
  `invalid_input`) → relay it directly. Never guess a fix or silently
  retry.

## Tips for Good Output

- **The spoiler rule is absolute, not a suggestion.** A `player`-mode
  response that leaks even one scene title has failed regardless of how
  good the generated content is.
- **Context injection is what makes filled scenes feel connected**, not
  generic. A generic-sounding encounter is a sign you didn't actually pull
  the relevant threads/NPCs from memory before invoking
  `encounter-generator`.
- **An outline is a plan, not a commitment.** In `dm` mode, treat outline
  edit requests as normal — rewrite the affected part of the structure and
  write it back, same as Workflow 1.
