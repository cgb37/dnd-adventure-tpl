from __future__ import annotations

import traceback
from dataclasses import dataclass

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict | None = None


def _request_id() -> str | None:
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("request_id")


def install_exception_handlers(app: FastAPI, settings=None) -> None:
    """Install exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
        settings: Optional Settings instance. When provided, dev mode
                  (settings.is_production == False) includes exception
                  details in 500 responses to aid local debugging.
    """
    is_production = getattr(settings, "is_production", True)

    def _json_sanitize(value):
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {k: _json_sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_sanitize(v) for v in value]
        if isinstance(value, tuple):
            return [_json_sanitize(v) for v in value]
        if isinstance(value, set):
            return [_json_sanitize(v) for v in value]
        return value

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
        errors = _json_sanitize(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        log = structlog.get_logger(__name__)
        log.exception("Unhandled exception")

        # In development, expose the exception message (not stack trace) to
        # help developers diagnose issues without scanning server logs.
        # In production, details are always empty to avoid leaking internals.
        details: dict = {}
        if not is_production:
            details["debug"] = str(exc)

        return JSONResponse(
            status_code=500,
            content={
                "request_id": _request_id(),
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": details,
                },
            },
        )
