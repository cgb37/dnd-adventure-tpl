from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from llm_api.services.config import Settings


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = Settings()

        # Only enforce for endpoints that are likely to receive bodies.
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    length = int(content_length)
                except ValueError:
                    length = None

                if length is not None and length > settings.max_request_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "request_id": request.headers.get("X-Request-ID"),
                            "error": {
                                "code": "payload_too_large",
                                "message": "Request body too large",
                                "details": {"max_bytes": settings.max_request_bytes},
                            },
                        },
                    )

        return await call_next(request)
