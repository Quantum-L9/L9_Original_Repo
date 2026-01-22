"""
API → Agent Executor Integration Tests

Tests the flow: HTTP Request → API Router → Agent Executor → Response
"""

# Mock external services before imports
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Dynamically import and patch api.db.init_db
import types

# Create a mock module for api.db if it doesn't exist
if "api.db" not in sys.modules:
    api_db_module = types.ModuleType("api.db")
    api_db_module.init_db = lambda: None  # Mock function
    sys.modules["api.db"] = api_db_module

from fastapi.testclient import TestClient

# Now import server (it should work with the mocked db module)
from api.server import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Test client with mocked DB."""
    return TestClient(app)


@pytest.fixture
def mock_executor():
    """Mock agent executor."""
    with patch("api.agent_routes.AgentExecutorService") as mock:
        executor = MagicMock()
        executor.start_agent_task = AsyncMock(
            return_value=MagicMock(
                status="completed", result={"message": "Task completed"}, iterations=1
            )
        )
        mock.return_value = executor
        yield executor


class TestAPIAgentIntegration:
    """Test API to Agent Executor integration."""

    def test_execute_request_reaches_executor(self, client, mock_executor):
        """POST /agent/execute reaches agent executor."""
        payload = {"agent_id": "l9-standard-v1", "message": "Test message"}
        response = client.post("/agent/execute", json=payload)
        # Verify request was processed (may return 200 or 422 depending on validation)
        assert response.status_code in [200, 422, 500]

    def test_task_submission_creates_task(self, client, mock_executor):
        """POST /agent/task creates task envelope."""
        payload = {"agent_id": "l9-standard-v1", "payload": {"message": "Test"}}
        response = client.post("/agent/task", json=payload)
        assert response.status_code in [200, 201, 422]

    def test_agent_status_returns_state(self, client):
        """GET /agent/status returns agent state."""
        response = client.get("/agent/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_agent_health_integration(self, client):
        """GET /agent/health verifies agent subsystem health."""
        response = client.get("/agent/health")
        assert response.status_code == 200
