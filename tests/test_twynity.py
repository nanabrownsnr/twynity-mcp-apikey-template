"""Verify Twynity's API-key external-connection routes (Interconnector §10.2).

Covers: manifest declares api_key, POST/GET /api/v1/keys are persona-scoped,
the key never leaks into a list response (§11.3), and /external-connection/me
reports connection status.
"""

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from app.auth import TwynityIdentity
from app.twynity import register_routes


@pytest.fixture
def unauthenticated_app():
    """No auth attached — manifest/health should work without a token."""
    mcp = FastMCP("test_server")
    register_routes(mcp)
    return mcp.http_app()


def test_manifest_returns_expected_shape(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/.well-known/mcp.json")

    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "version" in body


def test_health_endpoint_returns_ok(unauthenticated_app):
    client = TestClient(unauthenticated_app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakeStore:
    def __init__(self):
        self.saved = None

    async def save(self, user_id, persona_id, name, key):
        self.saved = (user_id, persona_id, name, key)

    async def public_metadata(self, user_id, persona_id):
        if self.saved and self.saved[:2] == (user_id, persona_id):
            return {"id": "key-id", "name": self.saved[2]}
        return None


def test_manifest_declares_api_key(unauthenticated_app):
    response = TestClient(unauthenticated_app).get("/api/v1/.well-known/mcp.json")
    assert response.json()["external_connections"] == {
        "api_key": {"name": "service_api_key"},
        "oauth": None,
        "project": None,
    }


def test_keys_upsert_get_and_me_are_persona_scoped(monkeypatch):
    import app.twynity as routes

    identity = TwynityIdentity(user_id="user-1", persona_id="persona-1")
    store = FakeStore()
    monkeypatch.setattr(routes, "get_identity", lambda _request: _identity(identity))
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    mcp = FastMCP("test_keys")
    register_routes(mcp)
    client = TestClient(mcp.http_app())
    headers = {"Authorization": "Bearer verified-by-test", "Persona-Id": "persona-1"}
    payload = {"name": "GitHub PAT", "key": "ghp_secretvalue123"}

    created = client.post("/api/v1/keys", json=payload, headers=headers)
    assert created.status_code == 200
    assert created.json() == {"configured": True}
    assert store.saved == ("user-1", "persona-1", "GitHub PAT", "ghp_secretvalue123")

    fetched = client.get("/api/v1/keys", headers=headers)
    # §11.3 — the key must never appear in a list/read response.
    assert fetched.json() == {
        "items": [{"id": "key-id", "name": "GitHub PAT"}],
        "item_count": 1,
        "next_cursor": None,
    }
    assert "ghp_secretvalue123" not in fetched.text

    assert client.get("/api/v1/external-connection/me", headers=headers).json() == {"connected": True}


async def _identity(value):
    return value


def test_keys_rejects_missing_fields(monkeypatch):
    import app.twynity as routes

    monkeypatch.setattr(
        routes,
        "get_identity",
        lambda _request: _identity(TwynityIdentity(user_id="user-1", persona_id="persona-1")),
    )
    monkeypatch.setattr(routes, "get_active_store", lambda: FakeStore())
    mcp = FastMCP("test_keys_validation")
    register_routes(mcp)
    response = TestClient(mcp.http_app()).post(
        "/api/v1/keys",
        json={"name": "GitHub PAT"},
        headers={"Authorization": "Bearer test", "Persona-Id": "persona-1"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["missing_or_invalid_fields"] == ["key"]
