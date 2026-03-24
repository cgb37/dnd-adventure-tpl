---
title: Always Follow During Development
description: >-
  Assistant prompt template to enforce repository development conventions
  when generating code, new generator modules, or making changes to the
  `services/llm_api` code. Use as the system/user prompt when asking the
  assistant to implement, refactor, or scaffold Python generator services.
---

Goal
----
- Ensure generated code and developer guidance follow the project's
  established conventions (branching, commits, config usage, logging,
  errors, docs, and PEP 8).

Inputs (replace as needed)
-------------------------
- `slug`: short, hyphenated identifier for the resource
- `issue`: issue id or short description
- `branch`: suggested branch name
- `commit`: suggested conventional commit message

Constraints & Rules
-------------------
1. Create a new issue and a branch following repo conventions.
2. Use conventional commits for all changes (feat:, fix:, chore:, etc.).
3. Never hard-code values that belong in environment variables; use the
   existing settings service at `services/llm_api/src/llm_api/services/config.py`.
4. Use the project's logging service: `services/llm_api/src/llm_api/services/logging.py`.
5. Use the project's error helpers: `services/llm_api/src/llm_api/services/errors.py`.
6. Follow PEP 8 formatting and idioms. Prefer clear, explicit code.
7. Document new Python classes and functions with docstrings.
8. Write a short `README.md` snippet for the feature: overview, TL;DR,
   developer notes (how to run, test, configure).
9. When displaying errors to end users, do not expose stack traces in
   production. Return user-friendly messages and log internal details.

Prompt Template (System + User)
------------------------------
System: You are an assistant that writes code and project artifacts for the repository. Always follow the project's development rules and file layout.

Follow these steps:

- Create or update the files: {files}.
- Ensure configuration values come from `services/llm_api/src/llm_api/services/config.py`.
- Import and use the logging helpers from `services/llm_api/src/llm_api/services/logging.py`.
- Hook into error handling using `services/llm_api/src/llm_api/services/errors.py`.
- Follow PEP 8 formatting and add explanatory docstrings for public APIs.
- Add or update a short README snippet describing the feature and how to test it.
- Provide the exact branch name and conventional commit message to use.

Output expectations
-------------------
- A patch (diff) or list of file contents to write (ready for `apply_patch`).
- A suggested branch name and conventional commit message.
- A concise `README.md` snippet describing the change and how to test it.

Examples
--------

Expected outputs:

- Branch: `feat/add-mysterious-bard-npc-generator`
- Commit: `feat(generator/npc): add mysterious-bard npc generator`
- README snippet: 3-line overview + how to call the API endpoint locally.

Tips for iteration
------------------
- If the user wants stricter linting, suggest a `pyproject.toml` or `pre-commit` hook.
- For larger generators, recommend creating unit tests under `services/llm_api/tests/`.
- If files touch draft persistence, ensure paths conform to `campaigns/<active>/_drafts/<kind>/<slug>.md`.

--
Generated-by: assistant template (keep short and focused)
