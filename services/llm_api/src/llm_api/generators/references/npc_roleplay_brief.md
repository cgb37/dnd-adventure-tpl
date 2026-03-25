<!-- Trimmed from ai/skills/rpg-character-gen/references/ for LLM prompt embedding -->

# Roleplay NPC Reference — Brief

## Personality Framework (all 5 for major NPCs)

1. **Motivation** — Survival, Wealth, Power, Knowledge, Relationships, Ideology, Legacy, Redemption
2. **Traits** — 2–3 from: Temperament (cheerful, stoic, anxious, suspicious) + Social style (talkative, blunt, formal, evasive) + Quirk (collects oddities, speaks in proverbs, hums constantly)
3. **Distinguishing Feature** — One memorable physical detail: scar, distinctive voice, habitual gesture, clothing signature
4. **Secret/Complication** — Hidden allegiance, shameful past, forbidden knowledge, conflicted loyalty, curse
5. **Relationship to Party** — Quest giver, Ally, Obstacle, Information source, Moral challenge

## NPC Complexity Tiers
- **Tier 1 (background):** Name + occupation + 1 trait. No stat block.
- **Tier 2 (recurring):** Name + occupation + 2–3 traits + motivation + speech pattern. Optional simple stat block.
- **Tier 3 (major):** Full framework, detailed backstory, relationships, full stat block, multiple plot hooks.

## Speech Patterns
- Formal/archaic: "I beseech thee…"
- Blunt: "No. Pay up or leave."
- Nervous/rambling: "Oh, well, you see, the thing is…"
- Scholarly: "The parallels to the Third Dynasty are striking."
- Street/slang: "Look mate, I ain't got all day."
- Cryptic/poetic: "The river knows the stone's secret."

## Output Structure (roleplay_npc JSON)
Required: `character_type`, `identity` (name, race, occupation, alignment), `personality` (traits, ideals, bonds, flaws), `appearance` (description), `relationships` (name, relationship, attitude), `plot_hooks` (hook, tier: minor/major/campaign).
Optional: `personality.mannerisms`, `personality.speech_pattern`, `personality.motivation`, `appearance.distinguishing_features`, `secrets`, `stat_block`.
