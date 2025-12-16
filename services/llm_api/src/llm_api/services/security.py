from __future__ import annotations

from fastapi import Request
from fastapi import Header

from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


def _is_localhost_origin(origin: str) -> bool:
    o = (origin or "").strip().lower()
    return (
        o == "http://localhost"
        or o == "http://127.0.0.1"
        or o.startswith("http://localhost:")
        or o.startswith("http://127.0.0.1:")
    )


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings = Settings()  # pyright: ignore[reportCallIssue]

    if settings.relax_auth_on_localhost:
        host = request.client.host if request.client else ""
        origin = request.headers.get("origin") or ""

        if host in {"127.0.0.1", "::1"}:
            return
        if origin == settings.ui_origin or _is_localhost_origin(origin):
            return

    if not x_api_key or x_api_key != settings.llm_api_key:
        raise ApiError(code="unauthorized", message="Invalid API key", status_code=401)
