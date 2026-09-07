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

If they confirm a replacement, **the replacement keeps the existing
campaign's `mode`.** A new outline cannot flip a campaign from `dm` to
`player` or back — `mode` is fixed for the campaign's lifetime, and Step
7's write will refuse with `mode_immutable` if the payload disagrees. Carry
the existing `mode` forward into the new structure and skip Step 3. If the
user actually wants the other mode, tell them so plainly: they need to
start a new campaign for the other mode (a different campaign under
`campaigns/`, selected with `scripts/use-campaign`) — the same thing
`campaign_memory.py`'s `mode_immutable` message says.

If it returns an `error` with code `invalid_campaign_memory`, stop and
relay it. The file exists but is unreadable — that is *not* "no campaign
yet", and replacing it would destroy recoverable work. Never guess-repair
it; ask the user to fix or remove it.

### Step 3: Resolve mode

Skip this step entirely when replacing an existing outline (Step 2) — that
campaign's `mode` is already settled and carries forward unchanged.

For a brand-new campaign, infer from phrasing: "I'm running this for my group" → `dm`; "generate a
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
`magic`, any combination, or `[]`) inferred from that premise.

Set each scene's initial `status` from its `needs`:

- `needs` is **non-empty** → `status: planned`. There is content to generate.
- `needs` is **`[]`** (a pure roleplay/dialogue beat) → `status: filled`,
  written that way from the start. There is nothing for any Phase 1 skill to
  generate, so the scene is complete the moment it is written. **Never write
  an empty-`needs` scene as `planned`** — fill only ever flips a scene to
  `filled` after generating something for it, so a `planned` scene with
  nothing to generate would stay `planned` forever and permanently park "the
  next part" on itself.

Seed `threads` with any hooks the outline introduces. Leave `npcs` and `content_index` empty — nothing has been
generated yet.

### Step 7: Write to memory

Build the full structure (`mode`, `premise`, `scope`, `outline`, `threads`,
`npcs: []`, `content_index: []`) and write it:

```bash
echo '<json payload>' | python3 <skill-path>/scripts/campaign_memory.py write --campaign <active-campaign>
```

On a `mode_immutable` error, relay it directly and stop. This is a real,
permanent outcome when replacing an existing outline (Step 2) with a
payload whose `mode` differs from the campaign's settled one — retrying or
re-reading will never make it succeed. The only resolution is to keep the
existing `mode`, or start a new campaign for the other mode. Do not rewrite
the payload's `mode` to match without telling the user what happened.

On an `invalid_campaign_memory` error, relay it and stop — the existing
file is unreadable and must be fixed by hand.

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

### Step 1: Resolve active campaign and read memory (redacted)

Same active-campaign resolution as Workflow 1, Step 1. Then read the
**redacted** memory — always, in both modes, as the first read:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign> --redact
```

`--redact` returns only `mode`, the outline's chapter/episode/scene
numbering with each scene's `needs` and `status`, and `content_index`
reduced to `(beat, kind)`. That is everything Steps 2 and 3 need, and it
cannot leak a title, premise, thread, NPC, or draft path into your context
in `player` mode. Read the campaign's `mode` from this response.

If `mode` is `dm`, re-run the same command **without** `--redact` and use
that full structure for the rest of this workflow — a DM is meant to see
their own campaign. In `player` mode, keep working from the redacted
structure; the full read happens later and narrowly, in Step 4.

If it returns `{"found": false}` or has no `outline`, stop and tell the
user to generate an outline first. If it returns an `error` with code
`invalid_campaign_memory`, relay it and stop — do not attempt a repair or a
write.

### Step 2: Resolve scope

Pass the outline and the user's scope phrase to the resolver:

```bash
echo '<outline json>' | python3 <skill-path>/scripts/outline_scope.py "<scope phrase>"
```

If `matches` is `null`, the scope didn't match anything in the outline.
This is the one place fill asks a clarifying question in **both** modes.

- **`dm`**: list the valid chapters/episodes (numbers and titles) and ask
  which was meant.
- **`player`**: say only that that part doesn't exist yet, and ask what
  they meant. Do **not** list the chapters/episodes that do exist, with or
  without titles — how far the campaign runs is itself a spoiler.

### Step 3: Filter already-filled scenes

For each matched scene, check `content_index` for a row matching
`(beat, kind)` for every entry in that scene's `needs`. If every `needs`
entry (including an empty list) is already covered, skip the scene. Track
how many were skipped. Scenes with `needs: []` are written `filled` at
outline time (Workflow 1, Step 6) and are vacuously covered here, so they
are always skipped — there is nothing to generate for them.

### Step 4: Generate remaining scenes

If any scene survived Step 3 and you are in `player` mode, **now** read the
full (non-redacted) memory — not before:

```bash
python3 <skill-path>/scripts/campaign_memory.py read --campaign <active-campaign>
```

Use it only to build generation context for the specific scenes that
survived Step 3 (you need their real premises, thread summaries, and NPCs
to invoke the Phase 1 skills at all — that is the point of this step), and
only to construct the updated payload you write back in 4.3. None of it
reaches the user: Step 5's `player`-mode report is still counts only. If
Step 3 skipped every matched scene, there is nothing to generate and no
reason to do this read at all.

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
- Outline already exists (Workflow 1) → stop, confirm before replacing. A
  replacement inherits the existing campaign's `mode`; it can never change
  it.
- No outline yet (Workflow 2) → stop, tell the user to generate one first.
- Scope matches nothing (Workflow 2) → ask a clarifying question — the only
  question fill ever asks in `player` mode.
- A Phase 1 skill invocation fails for one scene → skip it, continue the
  rest of the batch, report the failure at the end.
- `campaign_memory.py` reports an error (`mode_immutable`,
  `invalid_campaign_memory`, `invalid_input`) → relay it directly. Never
  guess a fix or silently retry.
  - `mode_immutable` → the campaign's `mode` is settled for its lifetime.
    Permanent, not transient: keep the existing mode, or start a new
    campaign for the other one.
  - `invalid_campaign_memory` → `campaign.yml` exists but could not be
    parsed. Stop. This is **not** the same as no campaign yet, so never
    treat it as a green light to write a fresh outline over the file, and
    never guess-repair it — ask the user to fix or remove it.

## Tips for Good Output

- **The spoiler rule is absolute, not a suggestion.** A `player`-mode
  response that leaks even one scene title has failed regardless of how
  good the generated content is. `read --redact` exists so that in
  `player` mode you don't even *hold* the outline's spoilers until the
  moment you have to generate against them.
- **Context injection is what makes filled scenes feel connected**, not
  generic. A generic-sounding encounter is a sign you didn't actually pull
  the relevant threads/NPCs from memory before invoking
  `encounter-generator`.
- **An outline is a plan, not a commitment.** In `dm` mode, treat outline
  edit requests as normal — rewrite the affected part of the structure and
  write it back, same as Workflow 1.
