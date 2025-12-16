from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_api.routes.generate import router as generate_router
from llm_api.routes.health import router as health_router
from llm_api.services.body_size_limit import BodySizeLimitMiddleware
from llm_api.services.config import Settings
from llm_api.services.errors import install_exception_handlers
from llm_api.services.logging import configure_logging
from llm_api.services.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = Settings()
    configure_logging(settings)

    app = FastAPI(title="dnd-ai llm api", version="0.1.0")

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    install_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(generate_router, prefix="/v1")

    return app


app = create_app()
