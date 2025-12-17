---
description: 'Consolidated Core Python Coding Conventions'
applyTo: '**/*.py'
---

# Core Python Development Standards

> **Scope:** Applies to all Python projects unless explicitly overridden. This document consolidates style, structure, configuration, testing, and utilities into a single enforceable standard.

---

## 1) Style & Formatting
- Follow **PEP 8** for style, **PEP 257** for docstrings.
- Indent with 4 spaces. UTF-8 encoding for source files.
- Max line length: 100 (79 for narrow contexts).
- Tools (required):
  - **black** for formatting
  - **ruff** for lint + import order
  - **mypy** for typing
- Standardize rules via `pyproject.toml`.

---

## 2) Typing & Documentation
- Use type hints everywhere (`def func(x: str) -> int:`).
- Prefer `typing` / `typing_extensions` constructs (e.g., `Literal`, `Protocol`).
- Enable `from __future__ import annotations` for forward references.
- Docstrings: Google or NumPy style (be consistent).
- Comments explain **why**, not **what**.

---

## 3) Structure & Organization
- Keep files under ~300 lines; split large ones into focused modules.
- Module layout: docstring → imports → constants → helpers → main classes/functions → entry point.
- Function design:
  - Single-responsibility, 10–20 lines typical.
  - Pure functions when possible (no side effects).
  - Compose complexity from smaller helpers.
- Imports: stdlib → third-party → local; no wildcards.

---

## 4) Configuration & Constants
- Separate config from business logic.
- Constants: `UPPER_CASE: Final` with sensible defaults.
- Load secrets via environment or secret manager, never hardcoded.
- Use `pydantic-settings` (or equivalent) for typed, validated config.
- Validate configuration at startup; fail fast on errors.
- Provide `.env.example` for local dev.

---

## 5) Error Handling
- Use specific exception types; define a project-level hierarchy.
- Wrap third-party exceptions at module boundaries.
- Provide descriptive, actionable error messages.
- Use EAFP (`try/except`) for I/O, but avoid broad `except Exception`.
- Reserve `None` for “no value” cases, not for errors.

---

## 6) Logging
- Use `logging.getLogger(__name__)` per module.
- Levels: `DEBUG` (dev), `INFO` (milestones), `WARNING` (degraded), `ERROR` (failures), `CRITICAL` (system).
- Never log secrets, tokens, or PII. Redact sensitive keys.
- Use structured logs (JSON) in services; add correlation/request IDs.
- Default level: `WARNING` in prod, `INFO` staging, `DEBUG` dev.

---

## 7) Security Guidelines
- Validate and sanitize all external input (explicit allow-lists preferred).
- Database: use parameterized queries / ORM; prevent SQL injection.
- HTTP: always set timeouts; TLS verification on; retries with backoff + jitter.
- Filesystem: safe path joins; context managers; permissions restricted.
- Serialization: prefer JSON; avoid `pickle` for untrusted input.
- Cryptography: use vetted libs (`cryptography`, `secrets`); never roll your own.
- Automation: run `bandit` and `pip/uv audit` in CI; block on severe findings.
- Disallowed APIs: `eval`, `exec`, `pickle` (untrusted), `assert` in prod code.

---

## 8) Testing
- Use **pytest**; mirror source structure under `tests/`.
- One test file per source module.
- Test critical paths, edge cases, boundary conditions, invalid types.
- Parametrize where possible; fixtures for setup/teardown.
- Structure: Arrange → Act → Assert.
- Minimum coverage: **85%**; higher for critical modules.
- Use markers: `@pytest.mark.slow`, `@pytest.mark.integration`.

---

## 9) Utilities & Helpers
- Place helpers in `utils/` or `helpers/`, grouped by domain (`string_utils.py`, `date_utils.py`).
- Helpers should be:
  - Pure functions when possible
  - Well-named, small, and focused
  - Doc-stringed and typed
  - Testable in isolation
- Validate inputs; return consistent types.
- Avoid global state.

---

## 10) Async & Concurrency
- In async code, never block; use async-aware libraries for I/O.
- All awaits involving I/O must set explicit timeouts.
- CPU-bound tasks → thread/process pools.
- Protect shared state; avoid global mutability.

---

## 11) Resource Management & Performance
- Always use context managers for files, sockets, DB connections.
- Cap request sizes; validate content types; stream large payloads.
- Profile before optimizing; document trade-offs.
- Cache carefully with clear invalidation strategies.

---

## 12) Maintainability & DRY
- Apply the “3-touch rule”: if logic is duplicated 3+ times, extract a shared utility.
- Prefer composition over inheritance.
- Keep modules cohesive; refactor long functions/classes proactively.
- Use TODOs with owner + date + intent.

---

## 13) Documentation & DevEx
- README: quickstart, runbook, common tasks.
- API/docs: MkDocs or Sphinx, auto-build in CI.
- Update docs for new modules, flags, or user-facing changes.
- Use Conventional Commits for clarity.

---

## 14) CI/CD & Quality Gates
- Pipeline stages: lint → format check → type check → test → security scan → build.
- Block merges on failures.
- Pre-commit hooks required (`ruff`, `black`, `mypy`, `pytest`, `bandit`, `pip-audit`).
- Artifacts must be reproducible and signed if containerized.

---