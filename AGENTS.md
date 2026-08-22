<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->
<!-- Managed by agent: keep sections and order; edit content, not structure -->
<!-- Last updated: 2026-08-21 | Last verified: never -->

# AGENTS.md

**Precedence:** the **closest `AGENTS.md`** to the files you're changing wins. Root holds global defaults only.

## Commands
> Source: package.json, Gemfile, services/llm_api/pyproject.toml — verified against repo

<!-- AGENTS-GENERATED:START commands -->
| Task | Command |
|------|---------|
| Jekyll build | `bundle exec jekyll build` (outputs to `_site/`) |
| Jekyll dev server | `bundle exec jekyll serve` (localhost:4000) or `./jekyll-serve.sh` |
| Jekyll build for Playwright | `bundle exec jekyll build --destination _site-ui` |
| UI tests (full, Docker + Jekyll + Playwright) | `npm run test:ui` |
| UI tests (headed) | `npm run test:ui:headed` |
| Single UI test file | `npx playwright test tests/ui/chatbot.spec.cjs` |
| LLM API install | `cd services/llm_api && pip install -e ".[dev]"` |
| LLM API dev server | `cd services/llm_api && uvicorn llm_api.app:create_app --factory --reload --port 8000` |
| LLM API unit tests | `cd services/llm_api && pytest` |
| Docker (full stack) | `npm run start:docker:dub` (docker compose up --build) |
| Activate campaign | `./scripts/use-campaign <name>` |
| Promote draft → published | `./scripts/promote-draft` |
| Smoke-test LLM API | `./scripts/smoke-api` |
<!-- AGENTS-GENERATED:END commands -->

> This is a static Jekyll UI (Ruby) + FastAPI LLM service (Python), not a TypeScript project — Playwright/npm scripts exist only for browser test orchestration and releases.

## Response Style
- Answer first, elaborate only if needed. No sycophantic openers ("Great question!", "Absolutely!").
- For yes/no or status questions, lead with the answer.
- Skip preamble. Match response length to task complexity.

## Workflow
1. **Before coding**: Read nearest `AGENTS.md` + check Golden Samples for the area you're touching
2. **After each change**: Run the smallest relevant check (`bundle exec jekyll build`, single Playwright spec, or `pytest` in `services/llm_api/`)
3. **Before committing**: Run full test suite if changes affect >2 files or touch shared code
4. **Before claiming done**: Run verification and **show output as evidence** — never say "try again", "should work now", "tested", "verified", or "all green" without pasted command output in the same turn

## File Map
<!-- AGENTS-GENERATED:START filemap -->
```
services/llm_api/  → FastAPI LLM service (routes/, generators/, services/)
_layouts/          → Jekyll layouts (default.html, split.html, chapter.html, etc.)
_includes/         → Jekyll includes (chatbot_shell.html, etc.)
assets/css/        → chatbot.css and other styles
assets/js/         → chatbot-widget.js (vanilla ES2020, no build step)
campaigns/         → per-campaign content; _pages/_posts symlinked from active campaign
scripts/           → use-campaign, promote-draft, smoke-api, release.sh
tests/ui/          → Playwright UI tests (*.spec.cjs)
docs/              → documentation
_data/, _plugins/, _frontmattertpls/, _prompts/ → Jekyll config/data/templates
```
<!-- AGENTS-GENERATED:END filemap -->

## Architecture
- Static Jekyll UI + FastAPI LLM service. LLM API writes Markdown drafts to `campaigns/<name>/_drafts/<kind>/<slug>.md`; `scripts/promote-draft` moves a draft to `campaigns/<name>/_pages/`.
- `.active-campaign` names the current campaign; `scripts/use-campaign` symlinks that campaign's `_pages`/`_posts` into the repo root for Jekyll.
- Chatbot widget gating lives in `_layouts/default.html` and `_config.yml` (`chatbot.enabled_layouts`, `enabled_url_prefixes`, `disabled_url_prefixes`, `disabled_urls`); the widget itself is `assets/js/chatbot-widget.js` + `_includes/chatbot_shell.html`, calling `/v1/meta/providers`, `/v1/meta/generators`, `/v1/chat`, `/v1/generate/{kind}`, `/v1/promote/{kind}/{slug}` on the LLM API.
- LLM API auth: `X-API-Key` header on `/v1/*`; `RELAX_AUTH_ON_LOCALHOST=true` skips auth for localhost during dev. Provider chosen via env (`mock` default, `ollama`, `openai`, `anthropic`, `gemini`, `openrouter`).

## Heuristics (quick decisions)
<!-- AGENTS-GENERATED:START heuristics -->
| When | Do |
|------|-----|
| Adding env var | Add to `.env.example` first |
| Adding tests | Create in `tests/` directory |
| Running locally | Use `docker compose up` |
| Committing | Use Conventional Commits (feat:, fix:, docs:, etc.) |
| Unsure about pattern | Check `CLAUDE.md`/`AGENTS.md` and existing code in the area |
<!-- AGENTS-GENERATED:END heuristics -->

## Repository Settings
<!-- AGENTS-GENERATED:START repo-settings -->
- **Default branch:** `main`
- **Merge strategy:** squash, merge, rebase
<!-- AGENTS-GENERATED:END repo-settings -->

<!-- AGENTS-GENERATED:START ci-rules -->

<!-- AGENTS-GENERATED:END ci-rules -->

## Boundaries

### Always Do
- Run pre-commit checks before committing
- Add tests for new code paths
- Use conventional commit format: `type(scope): subject`
- Use **atomic commits** (one logical change per commit); preserve signatures, keep bisection useful
- **Show test output as evidence before claiming work is complete** — never say "try again", "should work now", "tested", "verified", or "all green" without pasted command output
- Before any edit, verify `pwd` resolves inside the intended repo worktree — not `.bare/`, not `~/.claude/skills/…`, not `~/.claude/plugins/cache/…` (those are read-only caches that get clobbered on update)
- For upstream dependency fixes: run **full** test suite, not just affected tests
- Force-push only with `--force-with-lease`

### Ask First
- Adding new dependencies
- Modifying CI/CD configuration
- Changing public API signatures
- Running full e2e test suites
- Repo-wide refactoring or rewrites
- Operations that touch >3 repos (produce a dry-run plan first)

### Never Do
- Commit secrets, credentials, or sensitive data
- Modify vendor/, node_modules/, or generated files
- Push directly to main/master branch — open a PR
- Merge a PR before all review threads are resolved
- Squash commits during merge or rebase unless the user explicitly asked
- Edit installed skill/plugin cache paths (`~/.claude/skills/`, `~/.claude/plugins/cache/`, `**/.bare/**`) — always the source worktree
- Reply to review comments with bare "Addressed" or "Fixed" — cite the resolving commit SHA
- Delete migration files or schema changes
- Use `secrets: inherit` in reusable GitHub Actions workflows (pass secrets explicitly)
- Commit package-lock.json without package.json changes
- Use any type without justification

## Contributing (for AI agents)
- **Comprehension**: Understand the problem before submitting code. Read the linked issue, understand *why* the change is needed, not just *what* to change.
- **Context**: Every PR must explain the trade-offs considered and link to the issue it addresses. Disclose AI assistance if the project requires it.
- **Continuity**: Respond to review feedback. Drive-by PRs without follow-up will be closed.

<!-- AGENTS-GENERATED:START module-boundaries -->

<!-- AGENTS-GENERATED:END module-boundaries -->

## Codebase State
<!-- AGENTS-GENERATED:START codebase-state -->
- No known deprecated code or CI pipeline as of this writing
<!-- AGENTS-GENERATED:END codebase-state -->

## Scoped AGENTS.md (MUST read when working in these directories)
<!-- AGENTS-GENERATED:START scope-index -->
- (No scoped AGENTS.md files yet)
<!-- AGENTS-GENERATED:END scope-index -->

> **Agents**: When you read or edit files in a listed directory, you **must** load its AGENTS.md first. It contains directory-specific conventions that override this root file.

## When instructions conflict
The nearest `AGENTS.md` wins. Explicit user prompts override files.
