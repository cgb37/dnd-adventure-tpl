## Plan: Fix missing `summary` validation in NPC generator

TL;DR - The LLM sometimes returns an empty `summary` string which fails `NpcOutput` validation (summary is required). Recommended fix: make the model reliably produce a non-empty `summary` (prompt + template change) and add a robust fallback/retry path that fills a summary when the model returns empty.

**Steps**
1. Reproduce locally: call the endpoint with the failing payload and capture the raw model responses and the parsed JSON that failed validation. *Depends on step 2 for context.*
2. Strengthen the prompt: update both the generator-level user prompt and the prompt template to explicitly require a non-empty `summary` (include an example and format). *Parallelizable with step 3.*
3. Add a parsing fallback in `run_generation` (or wrapper around the agent run): when pydantic_ai parsing fails due to missing `summary`, perform one retry with a short clarifying instruction ("Provide a one-paragraph markdown summary for the NPC; do not change other fields"). If the retry still fails, synthesize a `summary` from other returned fields (e.g., take first paragraph of `backstory` or `description`) before raising. *Blocks step 4 until implemented.*
4. Optionally relax `NpcOutput.summary` validation to allow a shorter/minimal summary (e.g., min_length=1 -> allow whitespace-trimmed fallback) while the prompt/fallback improvements take effect. This is a temporary mitigation only. *Parallel with step 2 or step 3.*
5. Add telemetry/logging: when a retry or synthesized summary is used, log an event including the provider_response_id and which fallback was used.
6. Tests & verification: add a unit test for the generator that simulates a model response missing `summary` and asserts that the endpoint either returns a valid `NpcOutput` after fallback or returns a clear 4xx/5xx with logged reason. Then manual test with `curl` and run `npm run test:ui` (or `scripts/smoke-api`) to confirm end-to-end.

**Relevant files**
- [services/llm_api/src/llm_api/generators/npc.py](services/llm_api/src/llm_api/generators/npc.py) — generator code and `NpcOutput` model usage; update legacy `user_prompt` and structured prompts here.
- [services/llm_api/src/llm_api/generators/base.py](services/llm_api/src/llm_api/generators/base.py) — `run_generation` wrapper; add retry/fallback handling here.
- [_prompts/ai-rpg-npc-generator.txt](_prompts/ai-rpg-npc-generator.txt) — prompt template; add explicit `summary` instruction and an example.
- [services/llm_api/src/llm_api/services/config.py](services/llm_api/src/llm_api/services/config.py) — add config knobs for `generation.retry_on_parse_failure` and `generation.max_parse_retries` if desired.

**Verification**
1. Reproduce failure: `curl -X POST http://localhost:8000/v1/generate/npc -H 'X-API-Key: <key>' -H 'Content-Type: application/json' -d '{"campaign":"rpg-theForsakenCrown","slug":"test","fields":{"type":"2nd level paladin"}}'` and confirm original error (missing `summary`).
2. After changes, repeat `curl` and verify 200 with `summary` non-empty.
3. Run unit test that mocks model responses: one returning `summary: ""` and assert fallback/ retry occurred and final output is valid.
4. Run `npm run test:ui` or `scripts/smoke-api` to ensure no regressions in the UI flow.

**Decisions / Assumptions**
- Prefer improving prompts and adding targeted retry/fallback over permanently loosening schema constraints.
- Fallback summary synthesis will use other returned fields (description/backstory) as a last resort.
- Telemetry is important to catch provider regressions (models skipping fields).

**Further Considerations**
1. Do you want to implement a single clarifying retry (simpler) or a multi-attempt retry with progressively stronger instructions (more robust but more cost)? Recommend single clarifying retry + synthesis fallback as balanced approach.
2. If you prefer a short-term quick patch, I can instead relax `NpcOutput.summary` validation immediately and schedule prompt/fallback work next.


## Plan: Add OpenRouter provider client

TL;DR - Add a first-class `openrouter` provider implementation and wire it into the providers factory so the API can use OpenRouter as an additional model source. Implement streaming support and expose `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` in config and docker-compose. Default model mapping will allow a configurable alias (you requested `openrouter api for google/gemini-2.5-flash` as the initial mapping).

**Steps**
1. Design & config (non-blocking): add new settings to `services/llm_api/src/llm_api/services/config.py` for `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_DEFAULT_MODEL`. Add `.env.example` entries. *Parallelizable with step 2.*
2. Implement client module: create `services/llm_api/src/llm_api/providers/openrouter.py` implementing the provider interface used by existing providers (chat/send, optional streaming, error mapping, response_id extraction). Use `httpx.AsyncClient` with retries, timeouts, and exponential backoff. Support both non-streaming and streaming responses. *Depends on step 1 for config.*
3. Wire factory: update `services/llm_api/src/llm_api/providers/factory.py` to register `openrouter` and map `provider_override='openrouter'` to the new module. Ensure the agent builder accepts `output_type` and usage limits unchanged.
4. Model mapping: add mapping defaults for `OPENROUTER_DEFAULT_MODEL` and allow provider model names to be passed via existing `provider_override` mechanism. Document recommended model aliases (e.g., `gemini-2.5-flash`).
5. Docker & env: update `docker-compose.yml` (api service env) and `services/llm_api/.env.example` to include the new env vars. Ensure secrets are not committed.
6. Tests & smoke: add unit tests mocking `httpx` responses for both streaming and non-streaming flows. Add a `scripts/smoke-openrouter.sh` or extend `scripts/smoke-api` to optionally test `provider=openrouter` if `OPENROUTER_API_KEY` is present. *Parallel with step 7.*
7. Logging & telemetry: ensure provider logs include `provider_response_id` and `provider_name` but never the API key. Add a debug log when fallbacks or parse errors occur.
8. Docs & README: update `services/llm_api/README.md` and top-level README to document env vars, model recommendations, and quick `curl` example.

**Relevant files**
- [services/llm_api/src/llm_api/providers/factory.py](services/llm_api/src/llm_api/providers/factory.py) — add `openrouter` branch to factory.
- [services/llm_api/src/llm_api/providers/openrouter.py](services/llm_api/src/llm_api/providers/openrouter.py) — new client implementation.
- [services/llm_api/src/llm_api/services/config.py](services/llm_api/src/llm_api/services/config.py) — new env settings: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_DEFAULT_MODEL`.
- [services/llm_api/.env.example](services/llm_api/.env.example) — add example env entries.
- [docker-compose.yml](docker-compose.yml) — add env mapping for api service (optional; keep values empty by default).
- [services/llm_api/tests/test_providers_openrouter.py](services/llm_api/tests/test_providers_openrouter.py) — new unit tests for provider.
- [services/llm_api/README.md](services/llm_api/README.md) — update docs.

**Verification**
1. Unit tests: run pytest on `services/llm_api/tests/` to validate provider functions and streaming handling (mock `httpx` streams).
2. Smoke test (manual): with `OPENROUTER_API_KEY` set, run the API via docker compose and call a quick generate endpoint with `provider_override=openrouter` and confirm a 200 response and logged `provider_response_id`.
3. Integration test: run `npm run test:ui` (which starts the API) to verify UI flows are unaffected.
4. Edge tests: simulate rate limit and network errors and confirm retries/backoff behave as expected.

**Decisions / Assumptions**
- You asked for streaming support — implement now (SSE/chunked handling via `httpx` async iterators).
- Default model mapping will support your provided alias ("openrouter api for google/gemini-2.5-flash") but also accept explicit model names passed by callers.
- Treat OpenRouter as a first-class provider but do not replace existing providers; make it selectable via `provider_override` only.

**Further Considerations**
1. Model compatibility: OpenRouter may use different param names or streaming formats; tests must cover these differences. Option: if OpenRouter supports OpenAI-compatible endpoints in your deployment, reuse existing OpenAI client with minor adjustments.
2. Cost & rate limits: add monitoring for provider usage and set sensible defaults for timeouts and retry counts.
3. Rolling deployment: prefer PR with tests and README updates; we can feature-flag the provider behind a config until verified.
