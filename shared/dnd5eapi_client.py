#!/usr/bin/env python3
"""
Generic, cached client for the public D&D 2014 SRD API
(https://www.dnd5eapi.co/api/2014/, docs: https://5e-bits.github.io/docs/introduction).

Lives at the repo root's shared/ dir (a sibling of write_draft.py) so any
skill can reach it via the same sys.path bootstrap (each skill script
walks up from its own path to find .git, then adds repo_root / "shared"
to sys.path). This module's own repo-root resolution (find_repo_root)
instead walks up from Path.cwd() at call time - see _default_cache_dir().
It is deliberately endpoint-agnostic - dm-guide calls it for rules/*, but
future skills (monster-generator, magic-generator, players-handbook) can
call it for monsters/*, spells/*, equipment/*, etc. without any change
here.

Local-first, API-supplemental: dm-guide's own local reference markdown is
the fast, offline path for common questions. This client exists for
follow-up questions those local tables don't cover.

Responses are cached indefinitely under <repo_root>/.cache/dnd5eapi/ (2014
SRD content is static, so there is no expiry/TTL logic) - a cache hit
never touches the network. Every test of this module mocks
urllib.request.urlopen; none of them perform a real network call.

CLI usage:
  python3 dnd5eapi_client.py rules/grappling

Output (stdout): the JSON body (exit 0), or
  {"error": {"code": "...", "message": "..."}} (exit 1).
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://www.dnd5eapi.co/api/2014"
TIMEOUT_SECONDS = 5


class Dnd5eApiError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def find_repo_root(start: Path) -> Path:
    """Walk upward from `start` until a directory containing `.git` is found."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise Dnd5eApiError("repo_root_not_found", f"No .git directory found above {start}")


def _default_cache_dir() -> Path:
    return find_repo_root(Path.cwd()) / ".cache" / "dnd5eapi"


def _cache_path(cache_dir: Path, endpoint: str) -> Path:
    safe_name = endpoint.strip("/").replace("/", "-")
    return cache_dir / f"{safe_name}.json"


def fetch(endpoint: str, *, cache_dir: Path | None = None) -> dict:
    """Fetch `endpoint` (path after /api/2014/, no leading slash) as JSON.

    Checks the on-disk cache first; a hit is returned without any network
    call. On a miss, fetches from BASE_URL, caches the result, and returns
    it. Raises Dnd5eApiError on any failure - never any other exception
    type reaches the caller.
    """
    resolved_cache_dir = cache_dir if cache_dir is not None else _default_cache_dir()
    path = _cache_path(resolved_cache_dir, endpoint)

    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            raise Dnd5eApiError(
                "invalid_response", f"Cached response for {endpoint!r} is corrupt: {exc}"
            )

    url = f"{BASE_URL}/{endpoint.strip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise Dnd5eApiError("not_found", f"No resource at {endpoint!r} (HTTP 404)")
        raise Dnd5eApiError(
            "invalid_response", f"HTTP {exc.code} fetching {endpoint!r}: {exc.reason}"
        )
    except urllib.error.URLError as exc:
        raise Dnd5eApiError("network_error", f"Could not reach dnd5eapi.co: {exc.reason}")
    except (OSError, ValueError) as exc:
        raise Dnd5eApiError("network_error", f"Could not reach dnd5eapi.co: {exc}")

    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Dnd5eApiError("invalid_response", f"Malformed JSON from {endpoint!r}: {exc}")

    try:
        resolved_cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass  # caching is an optimization; a write failure shouldn't fail an otherwise-successful fetch
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("endpoint", help="Path after /api/2014/, e.g. rules/grappling")
    args = parser.parse_args()

    try:
        data = fetch(args.endpoint)
    except Dnd5eApiError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
        return 1

    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
