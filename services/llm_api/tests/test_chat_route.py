from __future__ import annotations

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("RELAX_AUTH_ON_LOCALHOST", "true")

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from llm_api.app import create_app
    app = create_app()
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_chat_returns_200(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "What is a goblin?"}]},
    )
    assert resp.status_code == 200


def test_chat_response_has_message_key(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Describe the dungeon."}]},
    )
    body = resp.json()
    assert "data" in body
    assert "message" in body["data"]


def test_chat_message_has_role_and_content(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Tell me about orcs."}]},
    )
    msg = resp.json()["data"]["message"]
    assert msg["role"] == "assistant"
    assert isinstance(msg["content"], str)
    assert len(msg["content"]) > 0


def test_chat_response_has_request_id(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    body = resp.json()
    assert "request_id" in body


def test_chat_empty_messages_returns_422(client):
    resp = client.post("/v1/chat", json={"messages": []})
    assert resp.status_code == 422


def test_chat_missing_messages_returns_422(client):
    resp = client.post("/v1/chat", json={})
    assert resp.status_code == 422


def test_chat_provider_override_via_header(client):
    resp = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"X-LLM-Provider": "mock"},
    )
    assert resp.status_code == 200
