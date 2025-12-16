from __future__ import annotations

from dataclasses import dataclass

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict | None = None


def _request_id() -> str | None:
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("request_id")


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or {},
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        # Don't leak internal details to clients.
        log = structlog.get_logger(__name__)
        log.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": {},
                },
            },
        )
