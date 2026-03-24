from __future__ import annotations

import os
import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")


def _make_client(app_env: str):
    """Build a TestClient with the given APP_ENV."""
    os.environ["APP_ENV"] = app_env
    # Re-import to pick up env var changes
    import importlib
    import llm_api.services.config as config_mod
    import llm_api.app as app_mod
    importlib.reload(config_mod)
    importlib.reload(app_mod)
    from fastapi.testclient import TestClient
    app = app_mod.create_app()
    os.environ.pop("APP_ENV", None)
    return TestClient(app, raise_server_exceptions=False)


def test_api_error_returns_structured_json():
    client = _make_client("development")
    # /v1/generate/unknown-kind should raise an ApiError (no active campaign)
    resp = client.post("/v1/generate/npc", json={"prompt": "test"})
    # Will fail with auth or no active campaign — still a 4xx ApiError
    assert resp.status_code in (400, 401, 404, 422)
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]


def test_500_in_dev_includes_debug_details(monkeypatch):
    """In dev mode, unhandled exceptions expose exception message in details.debug."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from llm_api.services.errors import install_exception_handlers
    from llm_api.services.config import Settings

    os.environ["APP_ENV"] = "development"
    import importlib
    import llm_api.services.config as cfg
    importlib.reload(cfg)
    settings = cfg.Settings()  # pyright: ignore[reportCallIssue]

    app = FastAPI()
    install_exception_handlers(app, settings)

    @app.get("/boom")
    def boom():
        raise ValueError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert "debug" in body["error"]["details"]
    assert "secret internal detail" in body["error"]["details"]["debug"]
    os.environ.pop("APP_ENV", None)


def test_500_in_production_hides_debug_details(monkeypatch):
    """In production, unhandled exceptions return a generic message with no internal info."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from llm_api.services.errors import install_exception_handlers

    os.environ["APP_ENV"] = "production"
    import importlib
    import llm_api.services.config as cfg
    importlib.reload(cfg)
    settings = cfg.Settings()  # pyright: ignore[reportCallIssue]

    app = FastAPI()
    install_exception_handlers(app, settings)

    @app.get("/boom")
    def boom():
        raise ValueError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["details"] == {}
    assert "secret internal detail" not in resp.text
    os.environ.pop("APP_ENV", None)
