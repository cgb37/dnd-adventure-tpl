# dm-guide Skill — Design

## Context

This is the first skill of Phase 2 of the AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md` and Phase 1's
spec, `docs/superpowers/specs/2026-09-06-encounter-generator-skill-design.md`):

- **Phase 1 — Generator skills** (done for `encounter-generator`; not yet
  built for `location-generator`, `monster-generator`, `magic-generator`).
- **Phase 2 — Reference skills**: `dm-guide`, `players-handbook`.
  Abbreviated rules/lookup skills, a different shape than the generators —
  no draft-heavy workflow, no per-request budget math. **This spec covers
  the first of these, `dm-guide`, which also establishes a new shared
  pattern: an external SRD API client other skills can reuse.**
- **Phase 3 — `dm-orchestrator`, batch mode** and **Phase 4 —
  `dm-orchestrator`, live session mode**: unaffected by this spec.

`dm-guide` has two behaviors:

1. **Chat Q&A** — answer a DM's rules question directly in conversation.
   No file output, no campaign dependency.
2. **Cheat-sheet generation** — on request, compile a fixed, campaign-agnostic
   core-rules reference page into the active campaign's draft pipeline,
   the same target `encounter-generator` writes to
   (`shared/write_draft.py`).

## New Shared Dependency: `dnd5eapi_client.py`

The public 2014 SRD API at `https://www.dnd5eapi.co/api/2014/` (docs:
https://5e-bits.github.io/docs/introduction) hosts the same open SRD data
this repo already hand-transcribes into skill reference files. This spec
adds a **generic, cached, stdlib-only** client for it at
`shared/dnd5eapi_client.py` — a sibling of `shared/write_draft.py`, reached
by every skill via the same sys.path bootstrap (walk up to `.git`, add
`repo_root / "shared"` to `sys.path`).

**Generic, not rules-specific:** the client takes an arbitrary endpoint
path (e.g. `"rules/grappling"`, `"monsters/goblin"`, `"spells/fireball"`)
so `monster-generator`, `magic-generator`, and `players-handbook` can call
it later for their own endpoints without modifying this module. Wiring
those future skills to actually use it is out of scope here (see Out of
Scope).

**Local-first, API-supplemental:** `dm-guide`'s local reference markdown
(`core-adjudication.md`, `combat-mechanics.md`) stays the fast, offline,
primary path for the two rules areas this spec scopes. The API client is
called only for follow-up questions the local tables don't cover. A failed
API call (network error, timeout, 404, malformed response) never blocks an
answer — it degrades to "couldn't reach the rules API" plus Claude's own
best-effort judgment, matching the "never silently assume, but never hard-fail
a chat answer either" spirit of the rest of the skill.

**Caching, no expiry:** 2014 SRD content is static, so responses are cached
indefinitely to `<repo_root>/.cache/dnd5eapi/<endpoint-with-dashes>.json`
(e.g. `rules/grappling` → `rules-grappling.json`). A cache hit skips the
network call entirely. `.cache/` is added to `.gitignore` — it's a local
runtime cache, not committed content. Tests never hit the real network:
they pre-seed this cache directory with fixture JSON and assert cache-hit
behavior directly.

### Client Interface

```python
class Dnd5eApiError(Exception):
    def __init__(self, code: str, message: str): ...
    # .code, .message

def fetch(endpoint: str, *, cache_dir: Path | None = None) -> dict:
    """
    GET https://www.dnd5eapi.co/api/2014/<endpoint>.

    endpoint: path after /api/2014/, no leading slash (e.g. "rules/grappling").
    cache_dir: defaults to <repo_root>/.cache/dnd5eapi/. A cache hit at
      <cache_dir>/<endpoint with "/" -> "-">.json short-circuits the network
      call. A successful network response is written to that path before
      returning.

    Raises Dnd5eApiError on any failure:
      - "network_error"    - connection/timeout failure
      - "not_found"        - HTTP 404
      - "invalid_response" - non-2xx status other than 404, or malformed JSON
    """
```

CLI: `python3 dnd5eapi_client.py <endpoint>` → prints the JSON body on
success (exit 0), or `{"error": {"code": "...", "message": "..."}}` on
failure (exit 1). Same shape as `write_draft.py` and `encounter_budget.py`'s
CLIs. 5-second request timeout.

## File Layout

```
shared/
  dnd5eapi_client.py
  tests/
    test_dnd5eapi_client.py

ai/skills/dm-guide/
  SKILL.md
  references/
    core-adjudication.md   # DCs, advantage/disadvantage, conditions
                            # (grappled, prone, restrained, etc.), cover,
                            # resting, death saves
    combat-mechanics.md    # turn order/initiative, actions/bonus
                            # actions/reactions, opportunity attacks,
                            # multi-attack, ranged-in-melee, mounted combat
  evals/
    evals.json
```

No `ai/skills/dm-guide/scripts/` directory — there's no per-request
arithmetic like `encounter_budget.py`'s XP math. No `ai/skills/dm-guide/tests/`
either, since the skill introduces no local Python logic of its own; the
one piece of new code (`dnd5eapi_client.py`) is shared and tested under
`shared/tests/`.

## Q&A Workflow

1. Check whether the question is covered by `references/core-adjudication.md`
   or `references/combat-mechanics.md`. If so, answer directly from there —
   no network call.
2. If not covered locally, call `dnd5eapi_client.py fetch()` for the
   relevant endpoint (Claude picks the endpoint path based on the question,
   e.g. a rules-section slug) and answer using that response.
3. If `fetch()` raises `Dnd5eApiError`, tell the user the rules API
   couldn't be reached (surface `.message`) and still answer from
   Claude's own knowledge/best judgment rather than refusing to respond.

This path has no campaign dependency and works with no active campaign set.

## Cheat-Sheet Workflow

Triggered by requests like "give me a core-rules cheat sheet" / "compile
the DM reference page."

1. Resolve active campaign from `.active-campaign` at the repo root. If
   missing or empty, surface the same `no_active_campaign` error path as
   `encounter-generator` ("Run scripts/use-campaign first") and write
   nothing.
2. Render **both** reference files' tables into one Markdown body. This
   content is fixed and campaign-agnostic — not tailored per request, and
   not API-fetched (the committed cheat-sheet artifact never depends on
   network availability at generation time).
3. Build frontmatter:
   ```json
   {
     "layout": "dmnote",
     "title": "Core Rules Reference",
     "permalink": "/dm-guide/:slug",
     "category": "dm-guide",
     "jumbo": "",
     "search": true,
     "excerpt_separator": ""
   }
   ```
   (`id` and `slug` are filled in automatically by `write_draft.py`, as with
   `encounter-generator`.) `layout: dmnote` uses the existing
   `_layouts/dmnote.html` — a DM-only page layout already defined in this
   repo but not yet used by any generator or skill.
4. Call `shared/write_draft.py` with `kind="dm-guide"`, `slug="core-rules"`,
   the frontmatter above, and the rendered body. This **always overwrites**
   `campaigns/<campaign>/_drafts/dm-guide/core-rules.md` on every request —
   no promoted-page check, no versioning. Simplest behavior, matching
   `write_draft.py`'s existing write-always semantics for every other kind.

## Error Handling

- Q&A path: no active-campaign dependency, so no campaign-related errors.
  API failures degrade to a stated fallback (see Q&A Workflow step 3),
  never a hard failure.
- Cheat-sheet path: `no_active_campaign` surfaced identically to
  `encounter-generator`. `write_draft.py` failures (e.g. can't create
  `_drafts/` dir) surface the underlying error, matching existing
  behavior.
- `dnd5eapi_client.py` never raises anything other than `Dnd5eApiError` to
  its callers — network/timeout/HTTP/JSON-decode failures are all mapped
  to one of the three error codes listed in the Client Interface section.

## Testing

- `shared/tests/test_dnd5eapi_client.py`:
  - Cache hit: a pre-seeded fixture file under a temp `cache_dir` is
    returned without any network call (verify via a monkeypatched/blocked
    network layer, e.g. patching `urllib.request.urlopen` to raise if
    called).
  - Cache miss + successful fetch: mocked `urlopen` returns a JSON payload,
    which is both returned and written to `cache_dir`.
  - `not_found`: mocked 404 response maps to `Dnd5eApiError("not_found", ...)`.
  - `network_error`: mocked connection failure maps to
    `Dnd5eApiError("network_error", ...)`.
  - `invalid_response`: mocked malformed JSON body maps to
    `Dnd5eApiError("invalid_response", ...)`.
  - CLI success and CLI error (non-zero exit, JSON error body on stdout).
- `ai/skills/dm-guide/evals/evals.json`, mirroring
  `encounter-generator/evals/evals.json`'s shape (prompt → expected output →
  assertions). Minimum coverage:
  - A question answered entirely from local reference tables (no API call
    expected).
  - A question requiring the API fallback, with the API reachable.
  - A question requiring the API fallback, with the API unreachable
    (expect a stated fallback message, not a refusal or hard error).
  - Cheat-sheet generation with an active campaign (expect the draft file,
    correct frontmatter incl. `layout: dmnote`, both reference areas
    represented in the body).
  - Cheat-sheet generation with no active campaign (expect the
    `no_active_campaign` guidance, no draft written).

## Out of Scope (deferred to later work)

- Wiring `monster-generator`, `magic-generator`, or `players-handbook` to
  actually call `dnd5eapi_client.py` for their own endpoints — this spec
  only builds the generic client and `dm-guide`'s use of it.
- Campaign-tailored or on-demand-subset cheat-sheet generation — the
  cheat-sheet is a single fixed page per this spec.
- Any TTL/expiry or cache-invalidation logic for `dnd5eapi_client.py` — SRD
  content is static, so the cache has none.
- `players-handbook` itself (Phase 2's second skill) — gets its own
  brainstorm once this pattern (and the shared API client) is validated.
- `dm-orchestrator` (Phases 3-4).
