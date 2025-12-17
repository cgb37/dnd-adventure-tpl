`````prompt
````markdown
# Iteration Documentation Prompt (Standard)

You are writing a **developer-facing** iteration document for the `dnd-adventure-tpl` repo.

## Naming convention
- The output document filename should follow:
  - `docs/issue-<issueNumber>-iteration-<iterationNumber>-<short-kebab-slug>.md`

## Required header metadata
At the top of the document:
- Title line: `# Issue #<N> — Iteration <I> — <Short Title>`
- `Issue:` link (GitHub URL)
- `Branch:` backticked branch name

## Audience + tone
- Audience: maintainers/developers.
- Be concise, factual, and specific.
- Prefer “what changed / where / why” over narrative.

## Required sections
Use these sections, in this order (headers can be adjusted slightly, but keep all sections present):

1) **Overview**
- 2–4 sentences describing what was built and where it shows up in the product.

2) **Goals (what we built)**
- Bulleted list.

3) **Non-goals**
- Bulleted list.

4) **Why this approach**
- Short rationale sections (2–6 bullets total).

5) **Implementation details**
- Group by layer (Jekyll, JS, API, tests) as appropriate.
- Call out key config toggles / gating logic.
- Mention any known tradeoffs.

6) **How to validate**
- Exact commands to run (build/test) and what success looks like.

7) **TODO list (execution plan)**
- Include the checklist you used while implementing.
- Mark items as done (e.g., `[x]`) or remaining (`[ ]`).

8) **Security considerations**
- List any security-relevant behavior:
  - auth expectations
  - secret handling
  - CORS / origin assumptions
  - XSS considerations
  - file write safety (path traversal, overwrite prevention)

9) **.env / environment variables added**
- List env vars added in this iteration, or explicitly state `None`.

10) **Diagram (optional but encouraged)**
- Include a diagram if it clarifies the architecture.
- Prefer Mermaid (` ```mermaid `) when appropriate.

11) **Diff summary (files changed)**  (MUST BE LAST)
- Provide a diff-style list using a fenced `diff` code block.
- Prefer:
  - `+ path` for added
  - `~ path` for modified
  - `- path` for deleted
  - for renames, show as `- old` and `+ new`

## Extra rules
- Keep “Diff summary” at the bottom.
- Do not include file contents; only reference file paths.
- If something wasn’t changed, don’t mention it.

````

`````