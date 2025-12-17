# `llm_api` (Iteration 2)

FastAPI service that generates *draft-only* D&D campaign content using PydanticAI and pluggable LLM providers.

## Key behaviors
- Writes Markdown drafts into the **active campaign content repo** only: `campaigns/<active>/_drafts/<kind>/<slug>.md`
- Stable IDs: UUIDv5 computed from `{kind}:{campaign}:{slug}` using a committed namespace constant
- Security: `X-API-Key` required for `/v1/*`
- CORS: allow `http://localhost:4000`
- Prompts/content are **not** logged unless `DEBUG_PROMPTS=true`

## Environment variables
Required:
- `LLM_API_KEY` (value expected in `X-API-Key` header)
- `LLM_PROVIDER` one of `ollama`, `openai`, `anthropic`, `gemini`, `mock`

Provider-specific:
- `OLLAMA_BASE_URL` (recommended in Docker: `http://host.docker.internal:11434`)
- `OLLAMA_MODEL` (e.g., `llama3.2`)
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`

Limits/budgets:
- `MAX_CONCURRENCY` (default: 4)
- `MAX_CONCURRENCY_PER_PROVIDER` (default: 2)
- `REQUESTS_PER_MINUTE` (default: 30)
- `MAX_OUTPUT_TOKENS` (default: 1200)

Logging:
- `LOG_LEVEL` (default: `INFO`)
- `DEBUG_PROMPTS` (default: `false`)

## Run (local)
From repo root:
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -e services/llm_api[dev]`
- `uvicorn llm_api.app:app --reload --port 8000`

## API
- `GET /healthz`
- `POST /v1/generate/{kind}` where `{kind}` in `npc|monster|encounter|chapter|location`

All `/v1/*` endpoints require `X-API-Key: $LLM_API_KEY`.
