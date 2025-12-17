from __future__ import annotations

from typing import Any

import structlog
from fastapi.responses import JSONResponse


def _request_id() -> str | None:
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("request_id")


def ok(data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=200, content={"request_id": _request_id(), "data": data})


def created(data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=201, content={"request_id": _request_id(), "data": data})
