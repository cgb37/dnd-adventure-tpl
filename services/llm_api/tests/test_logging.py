from __future__ import annotations

import os
import logging

import structlog

os.environ.setdefault("LLM_API_KEY", "test-key")


def _make_settings(app_env: str = "development"):
    from llm_api.services import config as config_mod
    import importlib
    importlib.reload(config_mod)
    os.environ["APP_ENV"] = app_env
    s = config_mod.Settings()  # pyright: ignore[reportCallIssue]
    os.environ.pop("APP_ENV", None)
    return s


def test_configure_logging_dev_does_not_raise():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("development")
    configure_logging(settings)  # must not raise


def test_configure_logging_prod_does_not_raise():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("production")
    configure_logging(settings)  # must not raise


def test_dev_logging_uses_console_renderer():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("development")
    configure_logging(settings)
    # ConsoleRenderer is used in dev — structlog config should have it
    config = structlog.get_config()
    processor_types = [type(p).__name__ for p in config["processors"]]
    assert "ConsoleRenderer" in processor_types


def test_prod_logging_uses_json_renderer():
    from llm_api.services.logging import configure_logging
    settings = _make_settings("production")
    configure_logging(settings)
    config = structlog.get_config()
    processor_types = [type(p).__name__ for p in config["processors"]]
    assert "JSONRenderer" in processor_types
