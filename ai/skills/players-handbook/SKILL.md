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
