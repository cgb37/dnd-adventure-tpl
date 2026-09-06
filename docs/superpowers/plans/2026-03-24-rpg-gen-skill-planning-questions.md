Clarifying Questions
1. Scope — which character types and how do they relate to existing generators?

The existing npc generator produces simple output (name, summary, tags). The RPG skill produces deeply nested JSON for three types: player_character, combat_npc, roleplay_npc. Should we:

A) Add new kinds alongside existing ones (e.g., player, combat-npc, roleplay-npc) — keeping existing npc generator untouched
B) Replace the existing npc generator with the richer RPG skill-backed version
C) Something else?

1. C) the goal is to enhance and evole the npc.py generator so that it achieves the following goals:
- predictable, consistent, structured data - json
- save the data to a vector database so that an MCP server can be created in the future to access the generated data.
- output to yaml frontmatter and markup/markdown for use with the jekyll site generator.
- editable npcs that can be saved and change over time.
C, start simple, leave room for enhancements C, if it's not overly complex, otherwise A

3. -B) Port the logic into a Python module within llm_api
4 - B) Create standalone JSON schema files that Pydantic models are generated from
 5 - use existing layouts (e.g., npc), but create a key in the yaml frontmatter that uses the character, combat-npc, or roleplay-npc types
 6 - start with option B) Summarized/trimmed and embedded selectively based on request type and we will test its quality



2. Output format — JSON vs Jekyll draft

Existing generators return GeneratedDraft (YAML frontmatter + Markdown body) written to campaigns/<name>/_drafts/. The RPG skill outputs rich structured JSON (ability scores, spell slots, equipment arrays). Should the new generators:

A) Follow existing pattern — convert JSON to YAML frontmatter + Markdown body for Jekyll rendering
B) Return structured JSON as a new response shape (different from existing drafts)
C) Both — write a Jekyll draft AND return the structured JSON in the API response
3. Dice roller integration

The skill includes scripts/dice_roller.py for ability score generation (4d6-drop-lowest, standard array, point buy). Should we:

A) Call it as a subprocess from the adapter
B) Port the logic into a Python module within llm_api
C) Let the LLM handle ability score generation via the prompt (no dice roller)
4. Schema approach

The plan mentions generators/schemas/ for JSON schemas, but the existing pattern uses inline Pydantic models (e.g., NpcOutput). Should we:

A) Follow existing conventions — define Pydantic models inline (consistent)
B) Create standalone JSON schema files that Pydantic models are generated from
C) Both — Pydantic models as source of truth, export JSON schemas for documentation
5. Jekyll layouts

There are no character, combat-npc, or roleplay-npc layouts currently. Is creating new Jekyll layouts in scope, or should generated content use existing layouts (e.g., npc)?

6. Reference data embedding

The skill has ~4 large reference files (races-summary.md, classes-summary.md, npc-stat-blocks.md, npc-roleplay.md). Should these be:

A) Embedded in the system prompt sent to the LLM (large context, better output)
B) Summarized/trimmed and embedded selectively based on request type
C) Left out — rely on the LLM's training data for D&D knowledge