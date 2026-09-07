# players-handbook Skill — Design

## Context

Second skill of Phase 2 of the AI Skills initiative (see
`docs/superpowers/concepts/2026-09-06-ai-skills-concept.md` and Phase 2's
first spec, `docs/superpowers/specs/2026-09-06-dm-guide-skill-design.md`,
which shipped `dm-guide` and the shared `dnd5eapi_client.py` SRD API
client):

- **Phase 1 — Generator skills** (done for `encounter-generator`; not yet
  built for `location-generator`, `monster-generator`, `magic-generator`).
- **Phase 2 — Reference skills**: `dm-guide` (done), `players-handbook`
  (this spec). Same shape as `dm-guide` — local reference markdown as the
  fast/offline primary path, `shared/dnd5eapi_client.py` (already built,
  generic across SRD endpoints) as fallback for anything not covered
  locally, `shared/write_draft.py` for the optional compiled cheat-sheet.
- **Phase 3 — `dm-orchestrator`, batch mode** and **Phase 4 —
  `dm-orchestrator`, live session mode**: unaffected by this spec.

`players-handbook` has the same two behaviors as `dm-guide`, scoped to
what a *player* needs at the table rather than DM adjudication:

1. **Chat Q&A** — answer a player's rules question directly in
   conversation (how actions/bonus actions/reactions work from their
   seat, how spellcasting works, skill check mechanics). No file output,
   no campaign dependency.
2. **Cheat-sheet generation** — on request, compile a fixed,
   campaign-agnostic player quick-reference page into the active
   campaign's draft pipeline, the same target `dm-guide` and
   `encounter-generator` write to (`shared/write_draft.py`).

No new shared Python code is needed: `dnd5eapi_client.py`'s `fetch()` is
already endpoint-agnostic (`spells/*`, `rules/*`, `equipment/*`, ...), so
this skill calls it as-is.

## New Dependency: `playernote` Jekyll Layout

`dm-guide`'s cheat-sheet uses the existing `_layouts/dmnote.html`, a
DM-only page layout. There is no equivalent player-facing layout, so this
spec adds `_layouts/playernote.html` — structurally identical to
`dmnote.html` (same `side_by_side` base, same title/jumbo/content
structure) but named and scoped for player-facing reference pages, so DM
vs. player reference content stays symmetrically named going forward.

## File Layout

```
ai/skills/players-handbook/
  SKILL.md
  references/
    player-actions.md        # actions/bonus actions/reactions from the
                              # player's seat, skill checks, advantage
                              # sources a player can trigger
    spellcasting-basics.md   # spell slots, concentration, casting
                              # components (V/S/M), ritual casting,
                              # common spell tags
  evals/
    evals.json

_layouts/
  playernote.html             # new
```

No `ai/skills/players-handbook/scripts/` or `tests/` directory, matching
`dm-guide` — no per-request arithmetic, and the one piece of reusable
code (`dnd5eapi_client.py`) is already built and tested under
`shared/tests/`.

## Q&A Workflow

1. Check whether the question is covered by `references/player-actions.md`
   or `references/spellcasting-basics.md`. If so, answer directly from
   there — no network call.
2. If not covered locally, call `dnd5eapi_client.py fetch()` for the
   relevant endpoint (Claude picks the endpoint based on the question —
   likely `spells/<slug>`, `rules/<slug>`, or `equipment/<slug>`
   depending on what's being asked) and answer using that response.
3. If `fetch()` raises `Dnd5eApiError`, tell the user the rules API
   couldn't be reached (surface `.message`) and still answer from
   Claude's own knowledge/best judgment rather than refusing to respond.

This path has no campaign dependency and works with no active campaign
set.

## Cheat-Sheet Workflow

Triggered by requests like "give me a player quick-reference" / "compile
the player handbook page."

1. Resolve active campaign from `.active-campaign` at the repo root. If
   missing or empty, surface the same `no_active_campaign` error path as
   `dm-guide`/`encounter-generator` ("Run scripts/use-campaign first")
   and write nothing.
2. Render **both** reference files' full content into one Markdown body.
   This content is fixed and campaign-agnostic — not tailored per
   request, and not API-fetched (the committed cheat-sheet artifact never
   depends on network availability at generation time).
3. Build frontmatter:
   ```json
   {
     "layout": "playernote",
     "title": "Player Quick Reference",
     "permalink": "/players-handbook/:slug",
     "category": "players-handbook",
     "jumbo": "",
     "search": true,
     "excerpt_separator": ""
   }
   ```
   (`id` and `slug` are filled in automatically by `write_draft.py`.)
4. Call `shared/write_draft.py` with `kind="players-handbook"`,
   `slug="quick-reference"`, the frontmatter above, and the rendered
   body. This **always overwrites**
   `campaigns/<campaign>/_drafts/players-handbook/quick-reference.md` on
   every request — no promoted-page check, matching `dm-guide`'s and
   `write_draft.py`'s existing write-always semantics.

## Error Handling

- Q&A path: no active-campaign dependency, so no campaign-related
  errors. API failures degrade to a stated fallback (see Q&A Workflow
  step 3), never a hard failure.
- Cheat-sheet path: `no_active_campaign` surfaced identically to
  `dm-guide`/`encounter-generator`. `write_draft.py` failures (e.g.
  can't create `_drafts/` dir) surface the underlying error, matching
  existing behavior.

## Testing

- No new Python module, so no new `shared/tests/` file — `fetch()` is
  already covered by `shared/tests/test_dnd5eapi_client.py`.
- `ai/skills/players-handbook/evals/evals.json`, mirroring
  `dm-guide/evals/evals.json`'s shape (prompt → expected output →
  assertions). Minimum coverage:
  - A question answered entirely from local reference tables (no API
    call expected) — e.g. how bonus actions work for a player.
  - A question requiring the API fallback, with the API reachable — e.g.
    a specific spell's details not summarized locally.
  - A question requiring the API fallback, with the API unreachable
    (expect a stated fallback message, not a refusal or hard error).
  - Cheat-sheet generation with an active campaign (expect the draft
    file, correct frontmatter incl. `layout: playernote`, both reference
    areas represented in the body).
  - Cheat-sheet generation with no active campaign (expect the
    `no_active_campaign` guidance, no draft written).

## Out of Scope (deferred to later work)

- Any change to `dnd5eapi_client.py` itself — it's already generic
  enough for this skill's endpoints.
- Campaign-tailored or on-demand-subset cheat-sheet generation — the
  cheat-sheet is a single fixed page, matching `dm-guide`.
- Character-sheet-specific content (ability scores, class features,
  leveling) — out of scope for this abbreviated reference skill; that
  belongs to `rpg-character-gen` or a future dedicated skill.
- `location-generator`, `monster-generator`, `magic-generator` (Phase 1,
  remaining), `dm-orchestrator` (Phases 3-4).
