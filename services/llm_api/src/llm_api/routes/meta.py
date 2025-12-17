from __future__ import annotations

from fastapi import APIRouter

from llm_api.services.config import Settings
from llm_api.services.kinds import normalize_kind
from llm_api.services.registry import list_generator_kinds, schema_for_kind
from llm_api.services.responses import ok

router = APIRouter()


@router.get("/meta/generators")
def meta_generators():
    return ok({"generators": list_generator_kinds()})


@router.get("/meta/providers")
def meta_providers():
    """Return providers that are usable given current env configuration."""

    s = Settings()  # pyright: ignore[reportCallIssue]

    providers: list[str] = []

    # Built-in dev/test provider that does not require any external model.
    providers.append("mock")

    # Local (Ollama) is always available if base URL is configured.
    if (s.ollama_base_url or "").strip():
        providers.append("ollama")

    # Hosted providers are only shown if the required key exists.
    if s.openai_api_key:
        providers.append("openai")
    if s.anthropic_api_key:
        providers.append("anthropic")
    if s.gemini_api_key:
        providers.append("gemini")

    # Expose current default provider so the UI can preselect it.
    return ok({"providers": providers, "default_provider": s.llm_provider})


@router.get("/meta/schema/{kind}")
def meta_schema(kind: str):
    k = normalize_kind(kind)
    try:
        schema = schema_for_kind(k)
    except KeyError:
        # Reuse the API's error envelope style via ok + simple message;
        # callers treat non-2xx as failure, so keep 400 here.
        from llm_api.services.errors import ApiError

        raise ApiError(code="unsupported_kind", message=f"Unsupported kind: {k}", status_code=400)

    return ok({"kind": k, "schema": schema})
