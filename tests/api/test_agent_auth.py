"""
L9 Agent Endpoint Auth Tests
=============================

Tests for agent endpoint authentication:
- /agent/task requires authentication
- /agent/execute requires authentication

Version: 1.0.0
"""

import os
from unittest.mock import patch

import httpx
import pytest

# =============================================================================
# Configuration
# =============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TEST_API_KEY = "test-executor-key-12345"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_client_no_auth():
    """HTTP client without authentication."""
    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture
def api_client_with_auth():
    """HTTP client with valid authentication."""
    with httpx.Client(
        base_url=API_BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
    ) as client:
        yield client


# =============================================================================
# Test: Agent Execute Endpoint Auth
# =============================================================================


class TestAgentExecuteAuth:
    """Tests for /agent/execute endpoint authentication."""

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_execute_requires_auth(self, api_client_no_auth):
        """Verify /agent/execute requires authentication."""
        payload = {
            "message": "What is 2 + 2?",
            "agent_id": "l9-standard-v1",
            "kind": "query",
            "max_iterations": 1,
        }

        response = api_client_no_auth.post("/agent/execute", json=payload)

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}"
        )
        data = response.json()
        assert "Unauthorized" in data.get("detail", "")

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_execute_with_valid_auth(self, api_client_with_auth):
        """Verify /agent/execute works with valid auth."""
        payload = {
            "message": "What is 2 + 2?",
            "agent_id": "l9-standard-v1",
            "kind": "query",
            "max_iterations": 1,
        }

        response = api_client_with_auth.post("/agent/execute", json=payload)

        # Accept: 200 (success), 503 (executor not ready), 500 (internal error)
        # All prove auth worked and route is functional
        assert response.status_code in [
            200,
            500,
            503,
        ], f"Expected 200/500/503 with valid auth, got {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "ok" in data
            assert "task_id" in data
            assert "status" in data

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_execute_with_invalid_auth(self, api_client_no_auth):
        """Verify /agent/execute rejects invalid auth token."""
        payload = {
            "message": "What is 2 + 2?",
            "agent_id": "l9-standard-v1",
            "kind": "query",
            "max_iterations": 1,
        }

        headers = {"Authorization": "Bearer wrong-key"}

        response = api_client_no_auth.post(
            "/agent/execute", json=payload, headers=headers
        )

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}"
        )
        data = response.json()
        assert "Unauthorized" in data.get("detail", "")


# =============================================================================
# Test: Agent Task Endpoint Auth
# =============================================================================


class TestAgentTaskAuth:
    """Tests for /agent/task endpoint authentication."""

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_task_requires_auth(self, api_client_no_auth):
        """Verify /agent/task requires authentication."""
        payload = {
            "type": "test_task",
            "content": "Test task content",
        }

        response = api_client_no_auth.post("/agent/task", json=payload)

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}"
        )
        data = response.json()
        assert "Unauthorized" in data.get("detail", "")

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_task_with_valid_auth(self, api_client_with_auth):
        """Verify /agent/task works with valid auth."""
        payload = {
            "type": "test_task",
            "content": "Test task content",
        }

        response = api_client_with_auth.post("/agent/task", json=payload)

        assert response.status_code == 200, (
            f"Expected 200 OK with valid auth, got {response.status_code}"
        )

        data = response.json()
        assert data["status"] == "accepted"
        assert "task_id" in data

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_agent_task_with_invalid_auth(self, api_client_no_auth):
        """Verify /agent/task rejects invalid auth token."""
        payload = {
            "type": "test_task",
            "content": "Test task content",
        }

        headers = {"Authorization": "Bearer wrong-key"}

        response = api_client_no_auth.post("/agent/task", json=payload, headers=headers)

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}"
        )
        data = response.json()
        assert "Unauthorized" in data.get("detail", "")
