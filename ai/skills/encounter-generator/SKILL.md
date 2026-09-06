---
name: encounter-generator
description: Generate a D&D 5e combat encounter and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate an encounter, ambush, fight, combat scenario, or "something to fight" for their campaign. Triggers on requests like "give my party an encounter," "I need a fight for the swamp chapter," or "generate a deadly encounter for level 8." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Encounter Generator

Generate a level-appropriate, story-appropriate D&D 5e combat encounter and
write it as a draft in the active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve party context (low friction)

Run:

```bash
python3 <skill-path>/scripts/party_state.py read --campaign <active-campaign>
```

- If it returns `level`/`size`/`composition`, use them — don't ask.
- If it returns `{"found": false}`, ask the user once for party level and
  size (and composition, if they want to share it), then write it so future
  requests don't ask again:

```bash
python3 <skill-path>/scripts/party_state.py write --campaign <active-campaign> \
    --level <level> --size <size> --classes <class1> <class2> ...
```

### Step 3: Resolve difficulty and narrative context

- Difficulty defaults to `medium` unless the user said otherwise.
- Narrative context (where/why this fight happens) comes from whatever the
  user already said. Only ask if the request is genuinely bare (e.g. just
  "generate an encounter" with no other detail).

### Step 4: Compute the XP budget

```bash
python3 <skill-path>/scripts/encounter_budget.py --level <level> \
    --party-size <size> --difficulty <difficulty>
```

This returns `total_xp_budget` and the `cr_to_xp` table. Do not compute
these numbers yourself — always use the script's output.

### Step 5: Design the encounter

Read `references/encounter-building.md` for the multiplier table, monster
role guidance, and how to fit the encounter to the story. Read
`../rpg-character-gen/references/npc-stat-blocks.md` for existing CR-rated
monster stat blocks and the CR Estimation Guidelines table for inventing new
ones.

Select/reskin monsters against the XP budget (applying the multiplier table
for multiple monsters), assign each a tactical role, and write the setting,
tactics, and optional treasure to fit the narrative context from Step 3.

### Step 6: Write the draft

Build the frontmatter with these exact keys (matching the existing FastAPI
encounter generator's schema):

```json
{
  "layout": "encounter",
  "title": "<title>",
  "permalink": "/encounters/:slug",
  "category": "encounter",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/encounter-thumb.png",
  "portrait": "/assets/images/placeholders/encounter-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": ""
}
```

(`id` and `slug` are filled in automatically by `write_draft.py` — don't set
them yourself.)

Then write the body as Markdown prose covering: setting, monsters and their
roles, tactics, and (optionally) treasure. Don't dump the raw budget numbers
into the body — this is a narrative page for the DM to read at the table,
not a data sheet.

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "encounter",
  "slug": "<kebab-case-slug>",
  "title": "<title>",
  "frontmatter": { "...": "as built above" },
  "body": "<markdown body>"
}
```

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/encounter/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft encounter <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Mechanical accuracy matters.** Always use `encounter_budget.py`'s
  numbers, never eyeball XP math — arithmetic errors here mean encounters
  that are meaningfully too easy or too hard at the table.
- **Story fit matters as much as CR fit.** A perfectly balanced encounter
  that ignores the campaign's plot and setting is a worse draft than a
  slightly generous one that clearly belongs in this story.
- **Give the DM something to react to**, not just monsters: at least one
  tactical environmental feature, and tactical notes describing how the
  fight actually unfolds.
