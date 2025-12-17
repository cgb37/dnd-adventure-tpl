from __future__ import annotations

import httpx
from fastapi import APIRouter

from llm_api.services.config import Settings
from llm_api.services.responses import ok

router = APIRouter()


@router.get("/healthz")
async def healthz():
    settings = Settings()

    ollama_reachable = None
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Ollama native endpoint is stable for reachability checks.
                resp = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                ollama_reachable = resp.status_code == 200
        except Exception:
            ollama_reachable = False

    return ok(
        {
            "status": "ok",
            "provider": settings.llm_provider,
            "ollama_reachable": ollama_reachable,
        }
    )
