# Iteration 2 — LLM Draft Generation API (FastAPI + PydanticAI)

## Goal
Add a Python 3.12 FastAPI service that generates **draft Markdown** for campaign content using local LLMs (Ollama/Llama 3.2) and later hosted providers, writing output only into the **active campaign repo** under `campaigns/<active>/_drafts/`.

This iteration is intentionally “PR-friendly”: the API writes drafts to disk so they can be reviewed and promoted manually later.

## Constraints / Decisions
- **Framework**: FastAPI.
- **Language**: Python 3.12.
- **LLM orchestration**: PydanticAI.
- **Local LLM**: Ollama.
  - Host runs at `http://localhost:11434`.
  - When running in Docker, use `http://host.docker.internal:11434`.
- **Security**: require `X-API-Key` for `/v1/*` routes.
- **Output**: Markdown files written only to `_drafts` (never write into `_pages` / `_posts`).
- **Campaign selection**: must always use the template repo’s active campaign marker (`.active-campaign`).
- **Deterministic IDs**: UUIDv5 based on `{kind}:{campaign}:{slug}` with a committed namespace constant.
- **CORS**: allowlist (default `http://localhost:4000`).
- **Logging/observability**: JSON structured logs; request IDs; do not log prompts unless explicitly enabled.
- **Controls**: rate limiting + concurrency limiting; token limits via PydanticAI usage limits.

## Repository Integration
- Existing campaign switching is done by `scripts/use-campaign`, which:
  - symlinks `_pages` and `_posts` to `campaigns/<campaign>/_pages` and `_posts`
  - writes `.active-campaign`
- The new API must read `.active-campaign` and write drafts into:
  - `campaigns/<active>/_drafts/<kind>/<slug>.md`

## Endpoint Contract
### Health
- `GET /healthz`
  - Returns provider info and, when provider is `ollama`, a reachability check against `/api/tags`.

### Draft generation
- `POST /v1/generate/{kind}`
  - Requires header: `X-API-Key: <value>`
  - `{kind}` currently supports: `npc`, `monster`, `encounter`, `chapter`, `location`.

#### Request body (JSON)
```json
{
  "prompt": "string (required)",
  "title": "string (optional)",
  "slug": "string (optional)",
  "seed": 123 (optional),
  "constraints": { "any": "json" } (optional)
}
```

#### Response body (JSON)
Success (`201`):
```json
{
  "request_id": "<uuid>",
  "data": {
    "kind": "npc",
    "campaign": "rpg-theForsakenCrown",
    "slug": "some-slug",
    "id": "<uuidv5>",
    "draft_path": "campaigns/<active>/_drafts/npc/some-slug.md",
    "placeholders_used": true,
    "yaml_keys_present": ["layout", "title", "..."]
  }
}
```
Errors:
- `401 unauthorized` for missing/invalid API key
- `409` if no `.active-campaign`
- `413` if request exceeds size limit
- `429/507` for limit/usage-limit scenarios

## Draft File Format
- File name: `<slug>.md`
- Content:
  - YAML frontmatter (`--- ... ---`)
  - Markdown body
  - A `# <title>` heading is included at the top for readability.

## Dev / Run Modes
### Host Python (fast iteration)
- Run with `uvicorn` from the repo root.
- Point Ollama base URL to `http://localhost:11434`.

### Docker Compose (integration with Jekyll)
- `api` service uses Python 3.12 slim
- Must use `OLLAMA_BASE_URL=http://host.docker.internal:11434` to reach host Ollama.

## Key Env Vars
- `LLM_API_KEY` (required)
- `LLM_PROVIDER` (default: `ollama`)
- `OLLAMA_BASE_URL` (default in compose: `http://host.docker.internal:11434`)
- `OLLAMA_MODEL` (default: `llama3.2`)
- `CORS_ALLOW_ORIGINS` (comma-separated string)
- Limits:
  - `MAX_CONCURRENCY`
  - `MAX_CONCURRENCY_PER_PROVIDER`
  - `REQUESTS_PER_MINUTE`
  - `MAX_MODEL_REQUESTS_PER_GENERATION`
  - `MAX_OUTPUT_TOKENS`
  - `MAX_REQUEST_BYTES`

## Smoke Test Checklist
1. Ensure campaign is active (`.active-campaign` exists): `./scripts/use-campaign rpg-theForsakenCrown --bootstrap`
2. Start API (host or compose)
3. `GET /healthz` returns `ollama_reachable: true`
4. `POST /v1/generate/npc` returns `201` and a `draft_path`
5. File exists on disk at `draft_path`

## Notes / Known Gotchas
- If you have `OLLAMA_BASE_URL=http://localhost:11434` in your host environment, it can override compose defaults. For Docker, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` explicitly.
- `CORS_ALLOW_ORIGINS` must be a comma-separated string (not JSON), e.g. `http://localhost:4000`.
