from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_api.routes.generate import router as generate_router
from llm_api.routes.health import router as health_router
from llm_api.routes.meta import router as meta_router
from llm_api.routes.promote import router as promote_router
from llm_api.services.body_size_limit import BodySizeLimitMiddleware
from llm_api.services.config import Settings
from llm_api.services.errors import install_exception_handlers
from llm_api.services.logging import configure_logging
from llm_api.services.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = Settings()  # pyright: ignore[reportCallIssue]
    configure_logging(settings)

    app = FastAPI(title="dnd-ai llm api", version="0.1.0")

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)

    # Local dev convenience: if auth is relaxed, disable CORS restrictions.
    # This avoids browser preflight failures when serving the UI from
    # alternate local ports (e.g., Playwright/static server).
    if settings.relax_auth_on_localhost:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins_list,
            allow_credentials=False,
            # Include OPTIONS so browser preflight requests succeed.
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    install_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(generate_router, prefix="/v1")
    app.include_router(meta_router, prefix="/v1")
    app.include_router(promote_router, prefix="/v1")

    return app


app = create_app()
