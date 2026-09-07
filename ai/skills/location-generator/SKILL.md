---
name: location-generator
description: Generate a D&D 5e location (town, dungeon, wilderness site, ...) and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a location, place, dungeon, town, or area for their campaign. Triggers on requests like "give me a location for the swamp chapter," "generate a hidden temple," or "I need a town for the party to rest in." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Location Generator

Generate a story-appropriate D&D 5e location and write it as a draft in the
active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve narrative and calibration context

- Narrative context (where/why this location matters, what chapter it's
  in) comes from whatever the user already said. Only ask if the request
  is genuinely bare (e.g. just "generate a location").
- Party level, if the user mentions it (or it's obvious from context),
  calibrates challenge severity in Step 3. If no level is given, assume a
  level 5 party (a reasonable mid-campaign default) and say so in your
  response — don't block on asking for it, unlike `encounter-generator`
  (a location doesn't need the full party composition).

### Step 3: Design the location

Read `references/location-building.md` for DC/severity scaling by level and
guidance on tying secrets, plot hooks, and NPCs to the active story.

Write:
- `description`: prose covering the location's look, feel, and atmosphere.
- `challenges`: up to four categories (`traps`, `ambushes`, `puzzles`,
  `hazards`), each a bullet-list string (see Step 4's exact format) scaled
  to the party level from Step 2. Omit any category that doesn't fit this
  location rather than inventing filler.
- `secrets`, `plot_hooks`: tied to the campaign's story context from Step 2.
- `npcs`: named characters who can be found here, if any fit.
- `environmental_features`: at least one feature the party can interact
  with, not just scenery.
- `additional_notes`: guidance for the DM on customizing this location at
  the table.

### Step 4: Write the draft

Build the frontmatter with these exact keys (matching the existing FastAPI
location generator's schema):

```json
{
  "layout": "location",
  "title": "<title>",
  "permalink": "/locations/:slug",
  "category": "location",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/location-thumb.png",
  "portrait": "/assets/images/placeholders/location-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": "",
  "name": "<location name>",
  "type": "<location type, e.g. \"Enchanted Forest\">",
  "description": "<prose from Step 3>",
  "challenges": {
    "traps": "- Trap Name: description\n- Another Trap: description",
    "ambushes": "- Ambush description",
    "puzzles": "- Puzzle description",
    "hazards": "- Hazard description"
  },
  "secrets": ["<secret>", "..."],
  "plot_hooks": ["<hook>", "..."],
  "npcs": [{ "name": "<name>", "description": "<description>" }],
  "environmental_features": ["<feature>", "..."],
  "additional_notes": "<prose guidance for the DM>"
}
```

Each populated `challenges` category is a single string whose *content* is
a Markdown-style bullet list (one `- Name: description` per line, joined
with `\n`) — not a YAML list. Omit any `challenges` category, or the whole
`challenges` key, that doesn't apply. `additional_notes` is a single prose
string, not a list.

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "location",
  "campaign": "<active-campaign>",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": ""
}
```

Use the `<active-campaign>` value already resolved in Step 1 — don't rely
on `write_draft.py`'s `.active-campaign`/cwd-based auto-resolution, since
campaign directories are git submodules and a cwd inside one could resolve
the wrong repo root. `body` is empty because `location.html` renders every
field from frontmatter; don't duplicate content into a Markdown body.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/location/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft location <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Story fit matters most.** A location that doesn't connect to the
  campaign's plot, faction, or the party's current chapter reads as
  filler.
- **Give the DM something to react to** in `environmental_features` and
  `challenges`, not just atmosphere — at least one thing the party can
  use, trigger, or solve.
- **Match challenge severity to the party level** from Step 2 using
  `references/location-building.md`'s guidance — a level 1 party facing a
  DC 18 puzzle is a broken encounter, not a challenge.
