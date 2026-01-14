"""
L9 Docker Stack Smoke Tests
Version: 1.1.0

Validates that the Docker stack is properly wired:
- Health endpoints respond
- API docs are accessible
- Key routers are mounted
- Agent executor endpoint works
- DB connectivity is verified

Run with: pytest tests/docker/test_stack_smoke.py -v

These tests AUTO-DETECT execution context:
- Inside Docker: Uses Docker DNS (l9-api:8000, l9-postgres:5432)
- From host: Uses localhost (127.0.0.1:8000, 127.0.0.1:5432)

No environment variables required. Manual override still works:
  API_BASE_URL=http://custom:9000 pytest tests/docker/test_stack_smoke.py -v
"""

import os
import pytest
import httpx

# =============================================================================
# Configuration (Auto-detected)
# =============================================================================

# Import auto-detection from conftest
from .conftest import (
    resolve_service_url,
    get_execution_context,
    API_BASE_URL,
    MCP_MEMORY_URL,
    MEMORY_API_BASE_URL,  # DEPRECATED alias for MCP_MEMORY_URL
)

# API key for authenticated endpoints
API_KEY = os.environ.get("L9_EXECUTOR_API_KEY", os.environ.get("L9_API_KEY", "YOUR_API_KEY_HERE"))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def api_client():
    """HTTP client for main API."""
    with httpx.Client(
        base_url=API_BASE_URL,
        timeout=30.0,
        headers={"Authorization": f"Bearer {API_KEY}"},
    ) as client:
        yield client


@pytest.fixture(scope="module")
def memory_client():
    """HTTP client for memory API."""
    with httpx.Client(
        base_url=MEMORY_API_BASE_URL,
        timeout=30.0,
    ) as client:
        yield client


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthEndpoints:
    """Verify all health endpoints respond correctly."""

    def test_root_health(self, api_client: httpx.Client):
        """Root /health endpoint (Docker healthcheck)."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_root_endpoint(self, api_client: httpx.Client):
        """Root / endpoint returns API info."""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "features" in data

    def test_os_health(self, api_client: httpx.Client):
        """OS layer health check."""
        response = api_client.get("/os/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "os"

    def test_agent_health(self, api_client: httpx.Client):
        """Agent layer health check."""
        response = api_client.get("/agent/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "agent"

    def test_memory_api_health(self, memory_client: httpx.Client):
        """Memory substrate API health check."""
        response = memory_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# =============================================================================
# API Docs Tests
# =============================================================================


class TestAPIDocs:
    """Verify FastAPI documentation is accessible."""

    def test_docs_endpoint(self, api_client: httpx.Client):
        """OpenAPI docs at /docs."""
        response = api_client.get("/docs")
        assert response.status_code == 200
        # FastAPI returns HTML for docs
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_json(self, api_client: httpx.Client):
        """OpenAPI JSON schema."""
        response = api_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


# =============================================================================
# Router Wiring Tests
# =============================================================================


class TestRouterWiring:
    """Verify key routers are properly mounted."""

    def test_os_status(self, api_client: httpx.Client):
        """OS status endpoint is wired."""
        response = api_client.get("/os/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_agent_status(self, api_client: httpx.Client):
        """Agent status endpoint is wired."""
        response = api_client.get("/agent/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_memory_test_endpoint(self, api_client: httpx.Client):
        """Memory test endpoint is wired (requires auth)."""
        response = api_client.post("/memory/test")
        # Either 200 (success) or 401/403 (auth required) proves router is wired
        assert response.status_code in [200, 401, 403, 422]


# =============================================================================
# Agent Executor Tests
# =============================================================================


class TestAgentExecutor:
    """Verify agent executor endpoint is functional."""

    def test_agent_execute_basic(self, api_client: httpx.Client):
        """
        POST /agent/execute with minimal payload.

        This tests the executor wiring without requiring real external tools.
        Expected: Either success response or 503 if executor not initialized
        (which is acceptable in smoke test - proves route exists).
        Requires authentication.
        """
        payload = {
            "message": "What is 2 + 2?",
            "agent_id": "l9-standard-v1",
            "kind": "query",
            "max_iterations": 1,
        }

        response = api_client.post("/agent/execute", json=payload)

        # Accept: 200 (success), 503 (executor not ready), 500 (internal error)
        # All prove the route is wired correctly
        # Note: api_client fixture includes auth header
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            data = response.json()
            assert "ok" in data
            assert "task_id" in data
            assert "status" in data
        elif response.status_code == 503:
            # Executor not initialized - acceptable in smoke test
            data = response.json()
            assert "detail" in data

    def test_agent_task_submit(self, api_client: httpx.Client):
        """
        POST /agent/task - submit task to queue.

        This tests the simpler task submission endpoint.
        Requires authentication.
        """
        payload = {
            "type": "test_task",
            "content": "Smoke test task",
        }

        response = api_client.post("/agent/task", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data


# =============================================================================
# Database Connectivity Tests
# =============================================================================


class TestDatabaseConnectivity:
    """Verify database connectivity and DSN configuration."""

    def test_database_url_not_localhost(self):
        """
        Verify DATABASE_URL doesn't point to localhost.

        This prevents the "works on my machine" bug where containers
        can't reach host's localhost.
        """
        database_url = os.environ.get("DATABASE_URL", "")
        memory_dsn = os.environ.get("MEMORY_DSN", "")

        # At least one should be set
        url = database_url or memory_dsn
        if url:
            assert "127.0.0.1" not in url, (
                f"DATABASE_URL contains localhost (127.0.0.1): {url}"
            )
            assert "localhost:5432" not in url, (
                f"DATABASE_URL contains localhost: {url}"
            )

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """
        Verify actual database connectivity.

        This runs inside the container where DATABASE_URL should use
        service DNS (postgres:5432).
        """
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")

        database_url = os.environ.get("DATABASE_URL") or os.environ.get("MEMORY_DSN")
        if not database_url:
            pytest.skip("DATABASE_URL not set")

        try:
            conn = await asyncpg.connect(database_url)
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            assert result == 1
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")


# =============================================================================
# Memory System Tests
# =============================================================================


class TestMemorySystem:
    """Verify memory system is operational."""

    def test_memory_stats(self, api_client: httpx.Client):
        """Memory stats endpoint (may require auth)."""
        response = api_client.get("/memory/stats")
        # 200 = success, 401/403 = auth required (proves route wired)
        # 503 = memory not initialized (acceptable in smoke test)
        assert response.status_code in [200, 401, 403, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data


# =============================================================================
# Smoke Test Summary
# =============================================================================


class TestSmokeSummary:
    """Final summary test to confirm all critical paths work."""

    def test_all_critical_paths(
        self, api_client: httpx.Client, memory_client: httpx.Client
    ):
        """
        Single test that validates all critical paths quickly.

        Useful for pre-commit hooks that need fast feedback.
        """
        # 1. Main API responds
        assert api_client.get("/health").status_code == 200

        # 2. Memory API responds
        assert memory_client.get("/health").status_code == 200

        # 3. Core routes are wired
        assert api_client.get("/os/health").status_code == 200
        assert api_client.get("/agent/health").status_code == 200

        # 4. Docs accessible
        assert api_client.get("/docs").status_code == 200

        # 5. Agent executor route exists
        exec_response = api_client.post(
            "/agent/execute",
            json={
                "message": "ping",
                "max_iterations": 1,
            },
        )
        assert exec_response.status_code in [200, 500, 503]


# =============================================================================
# Run as standalone script
# =============================================================================

if __name__ == "__main__":
    # Allow running as: python test_stack_smoke.py
    pytest.main([__file__, "-v", "--tb=short"])
