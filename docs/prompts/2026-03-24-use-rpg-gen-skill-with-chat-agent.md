# RPG Character Generator Skill with Chat Agent — First-pass Plan

Goal
----
Enable the Python `generators` modules to produce structured JSON player
characters and NPCs by leveraging the `rpg-character-gen` AI skill
(`ai/skills/rpg-character-gen/SKILL.md`). This is a lightweight, iterable
plan for a model-assisted implementation.

Plan (first pass)
------------------

1) Quick review
	 - Inspect `services/llm_api/src/llm_api/generators/` and
		 `ai/skills/rpg-character-gen/SKILL.md` to extract expected fields and
		 examples. Capture any immediate mismatches.

2) Define a minimal schema
	 - Create JSON schemas for `player_character`, `combat_npc`, and
		 `roleplay_npc` that map to the skill's output shapes.
	 - Store schemas at
		 `services/llm_api/src/llm_api/generators/schemas/`.

3) Adapter module
	 - Add `services/llm_api/src/llm_api/generators/adapter_rpg_skill.py`.
	 - Responsibilities:
		 - Accept generator inputs (kind, level/CR, constraints).
		 - Construct prompts / call the `rpg-character-gen` skill (or mock it).
		 - Normalize and validate the skill response against the schema.
		 - Return normalized JSON plus optional YAML front-matter for drafts.

4) Wire generators to the adapter
	 - Update `npc.py`, `monster.py`, and `location.py` (or add `player.py`) to
		 call the adapter instead of inlining generation logic.
	 - When persisting drafts, ensure path pattern
		 `campaigns/<active>/_drafts/<kind>/<slug>.md` is used.

5) Prompts & templates
	 - Add/adjust templates under `_prompts/` and document usage in
		 `docs/prompts/` (follow `docs/prompts/always-follow-dev.prompt.md`).

6) Integrations & safety
	 - Use `services/llm_api/src/llm_api/services/config.py` for env values.
	 - Use `services/llm_api/src/llm_api/services/logging.py` and
		 `services/llm_api/src/llm_api/services/errors.py` for logging and
		 user-safe error handling.

7) Tests
	 - Add unit tests under `services/llm_api/tests/` to:
		 - Validate adapter output against schemas using mock skill responses.
		 - Verify draft file creation and front-matter structure.

8) Docs & examples
	 - Add README snippets showing how to invoke the generators and how to
		 run tests locally (brief examples and cURL/uvicorn commands).

9) Lint & CI
	 - Ensure PEP 8 compliance and add a CI job that runs tests and linting.

10) Iterate with the model
	 - Run a refinement pass with the `rpg-character-gen` skill to tune
		 prompts, extend schemas (edge cases), and expand tests.

Next steps
----------
- I can start Step 1 (quick repo review) and extract the exact field names
	expected by the existing `generators` modules. Reply "start review" to
	proceed and I'll scan the relevant files now.


