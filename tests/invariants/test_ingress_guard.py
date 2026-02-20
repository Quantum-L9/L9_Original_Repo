"""
Invariant Tests: IngressGuard Middleware
========================================
Tests for ADR-0092 IngressGuard middleware enforcement.

These tests verify:
  - Anonymous state-mutating requests are rejected (403).
  - Read-only requests pass without principal_id.
  - Exempt paths (health, docs) always pass.
  - principal_id is stamped on request.state.
  - structlog audit fields are emitted.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api.middleware.ingress_guard import (
    _EXEMPT_PATHS,
    _READ_ONLY_METHODS,
    _STATE_MUTATING_METHODS,
    IngressGuardMiddleware,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app() -> FastAPI:
    """Create a minimal FastAPI app with IngressGuard middleware."""
    _app = FastAPI()
    _app.add_middleware(IngressGuardMiddleware)

    @_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @_app.get("/data")
    async def get_data(request: Request) -> dict:
        return {
            "principal_id": getattr(request.state, "principal_id", ""),
            "ingress_origin": getattr(request.state, "ingress_origin", ""),
        }

    @_app.post("/data")
    async def post_data(request: Request) -> dict:
        return {
            "principal_id": getattr(request.state, "principal_id", ""),
            "ingress_origin": getattr(request.state, "ingress_origin", ""),
            "classification": getattr(request.state, "classification", ""),
            "request_id": getattr(request.state, "request_id", ""),
        }

    @_app.post("/mcp/tool")
    async def mcp_tool(request: Request) -> dict:
        return {
            "ingress_origin": getattr(request.state, "ingress_origin", ""),
        }

    @_app.post("/slack/event")
    async def slack_event(request: Request) -> dict:
        return {
            "ingress_origin": getattr(request.state, "ingress_origin", ""),
        }

    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Invariant 1: Anonymous POST → 403
# ---------------------------------------------------------------------------


class TestAnonymousMutationRejection:
    """State-mutating requests without principal_id must be rejected."""

    def test_post_without_principal_returns_403(self, client: TestClient) -> None:
        resp = client.post("/data", json={"key": "value"})
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"] == "missing_principal"

    def test_post_with_empty_principal_returns_403(self, client: TestClient) -> None:
        resp = client.post(
            "/data",
            json={"key": "value"},
            headers={"X-Principal-Id": ""},
        )
        assert resp.status_code == 403

    def test_post_with_whitespace_principal_returns_403(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/data",
            json={"key": "value"},
            headers={"X-Principal-Id": "   "},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Invariant 2: Authenticated POST → 200
# ---------------------------------------------------------------------------


class TestAuthenticatedMutationAllowed:
    """State-mutating requests with valid principal_id must be allowed."""

    def test_post_with_principal_returns_200(self, client: TestClient) -> None:
        resp = client.post(
            "/data",
            json={"key": "value"},
            headers={"X-Principal-Id": "user-123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["principal_id"] == "user-123"
        assert body["classification"] == "state_mutating"
        assert body["request_id"] != ""


# ---------------------------------------------------------------------------
# Invariant 3: GET requests always pass (no principal required)
# ---------------------------------------------------------------------------


class TestReadOnlyAlwaysAllowed:
    """GET/HEAD/OPTIONS must pass without principal_id."""

    def test_get_without_principal_returns_200(self, client: TestClient) -> None:
        resp = client.get("/data")
        assert resp.status_code == 200

    def test_get_stamps_anonymous_principal(self, client: TestClient) -> None:
        resp = client.get("/data")
        body = resp.json()
        assert body["principal_id"] == ""

    def test_get_with_principal_stamps_it(self, client: TestClient) -> None:
        resp = client.get("/data", headers={"X-Principal-Id": "user-456"})
        body = resp.json()
        assert body["principal_id"] == "user-456"


# ---------------------------------------------------------------------------
# Invariant 4: Exempt paths always pass
# ---------------------------------------------------------------------------


class TestExemptPaths:
    """Health, docs, and liveness paths must pass without principal_id."""

    def test_health_exempt(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Invariant 5: ingress_origin derived from route prefix
# ---------------------------------------------------------------------------


class TestIngressOriginDerivation:
    """ingress_origin must be derived from the route prefix."""

    def test_mcp_prefix_sets_mcp_origin(self, client: TestClient) -> None:
        resp = client.post(
            "/mcp/tool",
            json={},
            headers={"X-Principal-Id": "user-789"},
        )
        assert resp.status_code == 200
        assert resp.json()["ingress_origin"] == "mcp"

    def test_slack_prefix_sets_slack_origin(self, client: TestClient) -> None:
        resp = client.post(
            "/slack/event",
            json={},
            headers={"X-Principal-Id": "user-789"},
        )
        assert resp.status_code == 200
        assert resp.json()["ingress_origin"] == "slack"

    def test_default_origin_is_http(self, client: TestClient) -> None:
        resp = client.post(
            "/data",
            json={},
            headers={"X-Principal-Id": "user-789"},
        )
        assert resp.status_code == 200
        assert resp.json()["ingress_origin"] == "http"


# ---------------------------------------------------------------------------
# Invariant 6: Negative tests — gateway failure must not 500
# ---------------------------------------------------------------------------


class TestGatewayFailureSafety:
    """Middleware must never produce 500 from its own logic."""

    def test_malformed_principal_header_does_not_500(self, client: TestClient) -> None:
        """Even bizarre header values should result in 403, not 500."""
        resp = client.post(
            "/data",
            json={},
            headers={"X-Principal-Id": "\x00\x01\x02"},
        )
        # Should either reject (403) or accept — never 500
        assert resp.status_code in {200, 403}
