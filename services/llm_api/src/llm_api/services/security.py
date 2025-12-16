from __future__ import annotations

from fastapi import Header

from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    settings = Settings()
    if not x_api_key or x_api_key != settings.llm_api_key:
        raise ApiError(code="unauthorized", message="Invalid API key", status_code=401)
