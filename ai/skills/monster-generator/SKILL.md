---
name: monster-generator
description: Generate a D&D 5e monster stat block and write it directly into the active campaign's draft pipeline as a Jekyll-ready page. Use this skill whenever someone asks to create, build, or generate a monster, creature, or beast for their campaign. Triggers on requests like "give me a monster for the swamp encounter," "generate a CR 5 undead," or "I need a boss creature for the finale." This writes a draft file (via scripts/promote-draft later) rather than returning standalone JSON.
---

# Monster Generator

Generate a CR-appropriate, story-appropriate D&D 5e monster stat block and
write it as a draft in the active campaign, ready for `scripts/promote-draft`.

## Workflow

### Step 1: Resolve the active campaign

Read `.active-campaign` at the repo root. If it doesn't exist or is empty,
stop and tell the user to run `scripts/use-campaign <name>` first — don't
guess a campaign.

### Step 2: Resolve the target CR and narrative context

- The user's request usually implies or states a CR (e.g. "a CR 5 undead,"
  "a boss for a level 12 party" — for the latter, pick a CR roughly equal
  to party level for a solo boss, per
  `../encounter-generator/references/encounter-building.md`'s multiplier
  guidance). If genuinely unstated, assume CR 3 (a common mid-tier threat)
  and say so in your response — don't block on asking.
- Narrative context (what this creature is, why it's here) comes from
  whatever the user already said.

### Step 3: Compute the stat-block guidance

```bash
python3 <skill-path>/scripts/monster_statblock.py --cr <cr>
```

This returns `proficiency_bonus`, `ac_range`, `hp_range`,
`attack_bonus_range`, and `damage_per_round_range` for the target CR. Do
not invent these numbers yourself — always use the script's output as the
band your stat block should land in. If you need an ability modifier for a
specific score, run:

```bash
python3 <skill-path>/scripts/monster_statblock.py --score <score>
```

`--cr` only accepts the exact values in
`references/monster-building.md`'s CR table (0, 1/8, 1/4, 1/2, 1, 2, 3, 5,
8, 12, 17, 20) — round the requested CR to the nearest of these before
calling the script, then adjust the numbers within the returned range to
taste for the exact CR requested.

### Step 4: Design the stat block

Read `references/monster-building.md` for how to turn the Step 3 ranges
into ability scores, actions, and special abilities appropriate for the
CR. Optionally look up an existing SRD monster for inspiration:

```bash
python3 <repo-root>/shared/dnd5eapi_client.py monsters/<index>
```

(e.g. `monsters/dire-wolf`; skip this if you're inventing something
original rather than reskinning a known creature.)

### Step 5: Write the draft

Build the frontmatter with these exact keys (matching the existing FastAPI
monster generator's schema):

```json
{
  "layout": "monster",
  "title": "<title>",
  "permalink": "/monsters/:slug",
  "category": "monster",
  "chapter": "<chapter, if known, else \"01\">",
  "episode": "<episode, if known, else \"01\">",
  "scene": "<scene, if known, else \"01\">",
  "jumbo": "",
  "thumb": "/assets/images/placeholders/monster-thumb.png",
  "portrait": "/assets/images/placeholders/monster-portrait.png",
  "tags": ["<relevant tags>"],
  "search": true,
  "excerpt_separator": "",
  "name": "<monster name>",
  "description": "<prose>",
  "type": "<Beast | Dragon | Undead | ...>",
  "size": "<Tiny | Small | Medium | Large | Huge | Gargantuan>",
  "ac": { "value": 0, "type": "natural armor" },
  "hp": "<N (XdY + Z)>",
  "hp_dice": "<XdY>",
  "speed": "<e.g. \"30 ft., fly 60 ft.\">",
  "abilities": {
    "strength": { "score": 0, "modifier": "+0" },
    "dexterity": { "score": 0, "modifier": "+0" },
    "constitution": { "score": 0, "modifier": "+0" },
    "intelligence": { "score": 0, "modifier": "+0" },
    "wisdom": { "score": 0, "modifier": "+0" },
    "charisma": { "score": 0, "modifier": "+0" }
  },
  "saving_throws": [{ "name": "dexterity", "modifier": "+0" }],
  "skills": "<e.g. \"Perception +4, Stealth +3\">",
  "senses": "<e.g. \"darkvision 60 ft., passive Perception 14\">",
  "languages": ["<language>"],
  "challenge": "<N (NNN XP)>",
  "special_abilities": [{ "name": "<name>", "description": "<description>" }],
  "actions": [
    {
      "name": "<name>",
      "type": "Melee Weapon Attack",
      "hit_bonus": "+0",
      "reach": "5 ft.",
      "target": "one target",
      "damage": [{ "type": "piercing", "dice": "1d10 + 2", "avg": 7 }]
    }
  ]
}
```

Notes on optional keys:
- `abilities.*.modifier` and any ability-check-derived numbers should come
  from `monster_statblock.py --score <score>`, not hand math.
- `challenge`'s XP comes from
  `../encounter-generator/scripts/encounter_budget.py`'s `cr_to_xp` table
  (run it with any valid `--level`/`--party-size`/`--difficulty` just to
  read the table, or read
  `../rpg-character-gen/references/npc-stat-blocks.md` directly) — don't
  invent the XP number.
- Include `spellcasting` (with `ability`, `dc`, `slots`, `spells`) only if
  the monster casts spells; omit the key entirely otherwise.
- Include `reactions`, `treasure`, `notes` only when applicable; omit
  otherwise.

(`id` and `slug` are filled in automatically by `write_draft.py` — don't
set them yourself.)

Pipe it to the shared writer:

```bash
echo '<json payload>' | python3 <repo-root>/shared/write_draft.py
```

Where `<json payload>` is:

```json
{
  "kind": "monster",
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
the wrong repo root. `body` is empty because `monster.html` renders every
field from frontmatter; don't duplicate content into a Markdown body.

On success this prints the draft's path (e.g.
`campaigns/<campaign>/_drafts/monster/<slug>.md`) and its id. Tell the
user the draft is ready and that `scripts/promote-draft monster <slug>`
will publish it when they're happy with it.

On error (e.g. `no_active_campaign`, `draft_write_failed`), relay the error
message directly — don't retry silently or guess a fix.

## Tips for Good Output

- **Mechanical accuracy matters.** Always ground AC/HP/attack/damage in
  `monster_statblock.py`'s ranges for the target CR — a monster that's
  meaningfully outside its CR band breaks encounter balance for anyone
  who uses it later.
- **Story fit matters as much as CR fit.** Tie type, abilities, and
  description to whatever context the user gave rather than generating a
  generic creature.
- **Give it at least one distinguishing special ability or tactic**, not
  just a bigger number than a mundane beast of the same size.
