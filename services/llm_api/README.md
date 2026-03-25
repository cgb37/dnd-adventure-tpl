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
- `LLM_PROVIDER` one of `ollama`, `openai`, `anthropic`, `gemini`, `openrouter`, `mock`

Provider-specific:
- `OLLAMA_BASE_URL` (recommended in Docker: `http://host.docker.internal:11434`)
- `OLLAMA_MODEL` (e.g., `llama3.2`)
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`), `OPENROUTER_MODEL` (default `google/gemini-2.5-flash`)

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

Behavior:
- `APP_ENV` (default: `development`) — controls logging renderer and 500 error detail exposure
  - `development` → color-coded human-readable console output; `details.debug` included in 500 responses
  - `production` → structured JSON logs; `details` omitted from 500 responses

## API

All `/v1/*` endpoints require `X-API-Key: $LLM_API_KEY`.

### Chat endpoint

**POST /v1/chat** — Plain conversational chat. No draft is written; no active campaign required.

Request body:
```json
{
  "messages": [
    {"role": "user", "content": "Describe a goblin warcamp."}
  ],
  "provider": "openai"
}
```

Response (`200 OK`):
```json
{
  "request_id": "...",
  "data": {
    "message": {
      "role": "assistant",
      "content": "The goblin warcamp sprawls..."
    }
  }
}
```

Optional headers:
- `X-LLM-Provider: <provider>` — override the server's default provider for this request.
- `X-API-Key: <key>` — required unless `RELAX_AUTH_ON_LOCALHOST=true`.

Error codes: `no_user_message` (400), `provider_not_configured` (400), `rate_limited` (429).

### Generate endpoint

- `GET /healthz`
- `POST /v1/generate/{kind}` where `{kind}` in `npc|monster|encounter|chapter|location`

**Example — generate NPC via OpenRouter (Gemini 2.5 Flash):**
```bash
# Set OPENROUTER_API_KEY in .env or export it, then:
curl -X POST 'http://localhost:8000/v1/generate/npc' \
  -H 'X-API-Key: your_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "campaign": "my-campaign",
    "slug": "gemini-paladin",
    "fields": {},
    "provider": "openrouter"
  }'
```
