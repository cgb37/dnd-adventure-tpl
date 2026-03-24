from __future__ import annotations

import os
import pytest

# Ensure required env vars are set before importing Settings
os.environ.setdefault("LLM_API_KEY", "test-key")


def test_app_env_defaults_to_development():
    from llm_api.services.config import Settings
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.app_env == "development"


def test_app_env_reads_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    # Force a fresh Settings instance (pydantic-settings reads env at init)
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    assert s.app_env == "production"
    monkeypatch.delenv("APP_ENV", raising=False)


def test_is_production_false_by_default():
    from llm_api.services.config import Settings
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert s.is_production is False


def test_is_production_true_when_set(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    assert s.is_production is True
    monkeypatch.delenv("APP_ENV", raising=False)
