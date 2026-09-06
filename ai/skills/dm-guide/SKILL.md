---
name: dm-guide
description: Answer D&D 5e DM rules questions (ability checks, conditions, cover, resting, death saves, turn order, actions/bonus actions/reactions, opportunity attacks, multiattack, mounted combat, and similar rulings) and, on request, compile a core-rules cheat-sheet page into the active campaign. Use this skill whenever a DM asks how a rule works, what a condition does, what DC to use, or asks for a quick-reference sheet at the table. This is a rules-lookup skill, not a content generator — use encounter-generator/location-generator/monster-generator/rpg-character-gen instead for creating encounters, locations, monsters, or characters.
---

# DM Guide

Answer D&D 5e rules questions for the DM, and compile a fixed core-rules
cheat-sheet into the active campaign on request.

## Workflow: Answering a Rules Question

### Step 1: Check local references first

Read `references/core-adjudication.md` (ability checks/DCs, advantage &
disadvantage, conditions, cover, resting, death saves) and
`references/combat-mechanics.md` (turn order, actions/bonus
actions/reactions, opportunity attacks, multiattack, ranged-in-melee,
mounted combat). If the question is covered there, answer directly from
that content — no network call needed.

### Step 2: Fall back to the SRD API for anything not covered locally

If the local references don't cover the question, call the shared API
client:

```bash
python3 <repo-root>/shared/dnd5eapi_client.py rules/<relevant-endpoint>
```

Pick `<relevant-endpoint>` based on the question — the 2014 SRD API's
rules endpoints are organized by rule section (e.g. `rules/grappling`,
`rules/mounted-combat`). If you're unsure of the exact endpoint slug, try
your best guess; on a 404 (`"not_found"`), try `rules` (no sub-path) to
see the list of available sections, or answer from your own best
judgment instead of guessing repeatedly.

Answer the question using the JSON response.

### Step 3: If the API call fails, don't block the answer

If the client exits non-zero (its stdout is `{"error": {"code": "...",
"message": "..."}}`), tell the user the rules API couldn't be reached —
relay the error message plainly — and then still answer the question
from your own knowledge and best judgment. Never refuse to answer a rules
question just because the API lookup failed.

This entire workflow has no dependency on an active campaign — it works
the same with or without one set.

## Workflow: Compiling the Core-Rules Cheat-Sheet

Triggered by requests like "give me a core-rules cheat sheet" or "compile
the DM reference page."

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is
empty, stop and tell the user to run `scripts/use-campaign <name>` first
— don't guess a campaign, and don't write anything.

### Step 2: Compile the fixed content

Render **both** `references/core-adjudication.md` and
`references/combat-mechanics.md` into one Markdown body, covering every
section in both files. This content is the same every time — don't
tailor it to the current campaign or fetch anything from the SRD API for
this path; the committed cheat-sheet should never depend on network
availability.

### Step 3: Write the draft

Build the frontmatter with these exact keys:

```json
{
  "layout": "dmnote",
  "title": "Core Rules Reference",
  "permalink": "/dm-guide/:slug",
  "category": "dm-guide",
  "jumbo": "",
  "search": true,
  "excerpt_separator": ""
}
```

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.) `layout: dmnote` uses this repo's existing
`_layouts/dmnote.html`, a DM-only page layout.

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "dm-guide",
  "slug": "core-rules",
  "title": "Core Rules Reference",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
```

This **always overwrites** `campaigns/<campaign>/_drafts/dm-guide/core-rules.md`
— there's no promoted-page check, so re-running this on a campaign that
already promoted a previous cheat-sheet will still overwrite the draft
(it won't touch anything already promoted to `_pages/`).

On success, tell the user the draft is ready and that
`scripts/promote-draft dm-guide core-rules` will publish it.

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
