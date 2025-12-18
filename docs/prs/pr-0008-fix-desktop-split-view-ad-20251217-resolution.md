# PR #0008 — Fixes desktop split-view and adds local development utilities

Merged: 2025-12-17  
Doc date: 20251217  
PR: https://github.com/cgb37/dnd-adventure-tpl/pull/8

## Resolution Summary

This PR fixes the chatbot layout in desktop split-view by implementing a viewport-sticky design for the chatbot panel and preventing the navbar from overlapping it. It also improves local development and testing ergonomics by adding a VS Code task to run UI tests, introducing a mock LLM provider and a wait-for-LLM readiness utility, and adjusting Docker/CORS settings to make UI tests reliable in local environments.

## PR description

<!-- pr-body:start -->
Enhances chatbot responsive layout in desktop split-view by ensuring viewport-sticky behavior and preventing navbar overlap. Adds a VS Code task for running UI tests and a mock provider for local development. Updates Docker setup for UI tests with relaxed CORS settings to aid local testing.

- Implements viewport-sticky design for the chatbot panel
- Fixes navbar alignment and behavior in split-view
- Adds waitForLlmApiReady utility function for ensuring LLM API readiness
- Introduces mock provider for easier development without external dependencies
- Updates Docker Compose and CORS for comprehensive local testing setup

Partially addresses Issue #7
<!-- pr-body:end -->

## Overview

The site's chatbot panel behaved inconsistently in desktop split-view: it could become detached from the viewport or be overlapped by the navbar depending on window size and scroll position. This PR makes small, focused front-end changes to ensure the chatbot remains visible and correctly positioned across layouts and adds developer utilities so contributors can run UI tests locally without depending on external LLM services. Changes touch CSS for layout, test utilities, Docker and local server configuration, and a small API surface to support a mock provider.

## Goals (what we built)

- Fix chatbot layout in desktop split-view by applying viewport-sticky styling and z-index adjustments
- Prevent navbar overlap with the chatbot panel across responsive layouts
- Add a `waitForLlmApiReady` test utility to stabilize UI tests that depend on LLM readiness
- Introduce a mock LLM provider to allow local development without external dependencies
- Add a VS Code task to run UI tests and make Docker/CORS adjustments to support local UI test runs

## Non-goals

- This PR does not change production LLM configuration or replace the production LLM provider
- It does not perform a wholesale UX redesign of the chatbot beyond layout and behavior fixes
- It does not attempt to lock down CI or production CORS policies (changes are targeted at local/test environments)

## Why this approach

The changes are intentionally small and targeted to reduce risk: visual layout fixes are implemented in CSS to avoid invasive JS changes, and local-development utilities (mock provider, VS Code task, Docker tweaks) allow contributors to run deterministic UI tests without relying on external services. This improves developer productivity while keeping production behavior unchanged.

## Implementation details

### Jekyll / site integration

- No layout templates were modified; changes are limited to asset styles and test/dev tooling so the site build remains unchanged.

### Front-end (JS/CSS)

- Updated `assets/css/chatbot.css` to implement a viewport-sticky layout for the chatbot panel and add z-index rules to prevent navbar overlap.
- Updated UI test `tests/ui/chatbot.spec.cjs` to assert layout behavior and to use the new `waitForLlmApiReady` helper for test stability.
- Added a `waitForLlmApiReady` utility to the test helpers so tests wait deterministically for the LLM mock to be ready before interacting with the UI.

### Backend / API (if applicable)

- Introduced a mock provider so local development can simulate LLM responses without external services.
- Small changes in `services/llm_api/src/llm_api/routes/meta.py` to support readiness checks and relax CORS for the test/dev environment (explicitly targeted for local testing only).

### Testing

- Updated and added UI tests in `tests/ui/chatbot.spec.cjs` to verify the chatbot remains visible and correctly positioned in desktop split-view and across window sizes.
- Test utilities include `waitForLlmApiReady` and usage notes for the mock provider to keep tests deterministic.

## How to validate

- Run unit and UI tests locally: `cd dnd-adventure-tpl && npm run test:ui` — all UI tests should pass and `tests/ui/chatbot.spec.cjs` should assert that the chatbot panel remains visible and is not overlapped by the navbar.
- Use the VS Code task: open the `Run UI tests (tpl)` task in the VS Code UI and run it to confirm the task works as expected.
- Start services with Docker (if using the Docker-based test environment): `docker compose up --build` and verify the relaxed CORS allows the UI tests to communicate with the mock LLM provider.
- Manually verify behavior: open the site in split-view (desktop) and confirm the chatbot panel stays clipped to the viewport and the navbar does not overlap it when scrolling or resizing.

## TODO list (execution plan)

- [x] Scaffold doc (2025-12-18)
- [x] Fill in Resolution Summary / Overview / Goals / Non-goals
- [x] Fill in Implementation details
- [x] Add validation commands and expected results
- [ ] Final pass for accuracy (author review & final proofreading)

## Security considerations

- Docker/CORS changes are restricted to the local/test compose configuration and should not be promoted to production; ensure these changes are clearly documented and gated.
- The mock provider should only be used for development and testing; verify that production deployments cannot load the mock provider by default.
- No new secrets are introduced by this PR; verify that any developer convenience tokens used locally are documented as ephemeral and not checked into the repository.
- Front-end changes are layout-only; verify input rendering paths remain sanitized to mitigate XSS risk.

## Diff summary (files changed)

```diff
+ .vscode/tasks.json                 # Adds "Run UI tests (tpl)" VS Code task
~ assets/css/chatbot.css             # Implements viewport-sticky layout and z-index fixes
~ docker-compose.yml                 # Relaxed CORS for UI test environment
+ docs/issue-7-fix-ui-fixes.md       # New documentation / notes for Issue #7 follow-ups
~ package.json                       # Adds / updates UI test scripts and dev deps
~ services/llm_api/src/llm_api/routes/meta.py  # Readiness hooks and dev CORS handling for mock provider
~ tests/ui/chatbot.spec.cjs          # Adds/updates UI tests and waitForLlmApiReady helper
```
