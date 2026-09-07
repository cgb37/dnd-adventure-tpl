---
name: magic-generator
description: Generate a D&D 5e magic item and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a magic item, artifact, enchanted weapon, or piece of loot for their campaign. Triggers on requests like "give my party a magic sword," "generate a rare wondrous item," or "I need a boss reward for the finale." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Magic Item Generator

Generate a level-appropriate, story-appropriate D&D 5e magic item and
write it as a draft in the active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve rarity and narrative context

- If the user states a rarity (e.g. "a rare wondrous item"), use it
  directly. If they state a party level instead, use that. If neither is
  given, assume a level 5 party and say so in your response — don't block
  on asking, unlike `encounter-generator`.
- Narrative context (what this item is, who made it, why the party is
  finding it) comes from whatever the user already said.

### Step 3: Compute rarity guidance

```bash
python3 <skill-path>/scripts/magic_item_rarity.py --party-level <level>
```

or, if the user gave an explicit rarity:

```bash
python3 <skill-path>/scripts/magic_item_rarity.py --rarity <rarity>
```

The party-level form returns `eligible_rarities`, a `recommended_rarity`,
and `typically_requires_attunement` per eligible rarity. The rarity form
returns that rarity's `minimum_level` and `typically_requires_attunement`.
Use `recommended_rarity` (party-level form) unless the narrative calls for
a lower-rarity item on purpose (not every found item needs to be the best
the party can handle). Don't invent a rarity outside what the script
confirms is level-appropriate.

### Step 4: Design the item

Read `references/magic-item-building.md` for property-budget guidance at
the chosen rarity, and attunement norms. Optionally look up an existing
SRD item for inspiration:

```bash
python3 <repo-root>/shared/dnd5eapi_client.py magic-items/<index>
```

(e.g. `magic-items/bag-of-holding`; skip this if you're inventing an
original item.)

### Step 5: Write the draft

Build the frontmatter with these exact keys (there is no existing FastAPI
generator for this kind — this schema is the standard for this skill):

```json
{
  "layout": "reward",
  "title": "<title>",
  "permalink": "/magic-items/:slug",
  "category": "magic-item",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "reward-thumb.png",
  "portrait": "reward-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": ""
}
```

`thumb`/`portrait` are bare filenames, not a full path — the layout
prepends `/assets/images/` itself.

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Then write the body as Markdown prose covering: the item's name and
rarity, whether it requires attunement (and by whom, if restricted), its
mechanical properties, and flavor/history tied to the narrative context
from Step 2. Don't dump the raw rarity-guidance numbers into the body —
this is a narrative page for the DM to read at the table, not a data
sheet.

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "magic-item",
  "campaign": "<active-campaign>",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
```

Use the `<active-campaign>` value already resolved in Step 1 — don't rely
on `write_draft.py`'s `.active-campaign`/cwd-based auto-resolution, since
campaign directories are git submodules and a cwd inside one could resolve
the wrong repo root.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/magic-item/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft magic-item <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Rarity must match power level.** Always use
  `magic_item_rarity.py`'s guidance — a legendary-tier item handed to a
  level 3 party breaks the campaign's balance.
- **Story fit matters as much as rarity fit.** An item that doesn't
  connect to the narrative context (who made it, why it's here) reads as
  generic loot.
- **Give the item a limitation or cost**, not just a bonus — a charge
  limit, a quirk, a drawback on a failed save, or a reason it's dangerous
  to overuse — so it creates interesting choices at the table rather than
  being a flat upgrade.
