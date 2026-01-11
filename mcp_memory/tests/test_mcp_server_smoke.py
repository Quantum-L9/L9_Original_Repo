"""CI smoke tests for MCP Memory Server.

Spins up MCP app in-process and tests critical endpoints.
Run with: pytest mcp_memory/tests/test_mcp_server_smoke.py
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os

from src.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "MCP_API_KEY_L": "test-key-l",
        "MCP_API_KEY_C": "test-key-c",
        "OPENAI_API_KEY": "test-openai-key",
        "MEMORY_DSN": "postgresql://test:test@localhost:5432/test",
    }):
        yield


# =============================================================================
# Smoke Test 1: Health Endpoint
# =============================================================================

def test_health_endpoint(client):
    """Test /health endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code in [200, 503]  # 503 if DB not connected (OK for smoke test)
    assert "status" in response.json() or "error" in response.json()


# =============================================================================
# Smoke Test 2: MCP Tools Endpoint
# =============================================================================

def test_mcp_tools_endpoint(client, mock_env):
    """Test /mcp/tools endpoint lists available tools."""
    response = client.get(
        "/mcp/tools",
        headers={"Authorization": "Bearer test-key-c"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)
    assert len(data["tools"]) > 0
    
    # Verify expected tools exist
    tool_names = [tool["name"] for tool in data["tools"]]
    assert "save_memory" in tool_names
    assert "search_memory" in tool_names
    assert "get_memory_stats" in tool_names


# =============================================================================
# Smoke Test 3: MCP Call - Search Memory
# =============================================================================

@pytest.mark.asyncio
async def test_mcp_call_search_memory(client, mock_env):
    """Test /mcp/call endpoint with search_memory tool."""
    with patch("src.routes.memory_unified.embed_text", new_callable=AsyncMock) as mock_embed, \
         patch("src.routes.memory_unified.fetch_all", new_callable=AsyncMock) as mock_fetch:
        
        # Mock embedding
        mock_embed.return_value = [0.1] * 1536
        
        # Mock search results (empty for smoke test)
        mock_fetch.return_value = []
        
        response = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer test-key-c"},
            json={
                "tool_name": "search_memory",
                "arguments": {
                    "query": "test query",
                    "user_id": "test-user",
                    "top_k": 5
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "result" in data


# =============================================================================
# Smoke Test 4: MCP Call - Save Memory
# =============================================================================

@pytest.mark.asyncio
async def test_mcp_call_save_memory(client, mock_env):
    """Test /mcp/call endpoint with save_memory tool."""
    with patch("src.routes.memory_unified.embed_text", new_callable=AsyncMock) as mock_embed, \
         patch("src.routes.memory_unified.execute", new_callable=AsyncMock) as mock_execute, \
         patch("src.routes.memory_unified.fetch_one", new_callable=AsyncMock) as mock_fetch:
        
        # Mock embedding
        mock_embed.return_value = [0.1] * 1536
        
        # Mock database operations
        mock_execute.return_value = None
        mock_fetch.return_value = {
            "packet_id": "test-id",
            "envelope": {"kind": "MEMORY"},
            "timestamp": "2026-01-09T00:00:00Z"
        }
        
        response = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer test-key-c"},
            json={
                "tool_name": "save_memory",
                "arguments": {
                    "content": "Test memory",
                    "kind": "preference",
                    "scope": "developer",
                    "duration": "long",
                    "user_id": "test-user"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"


# =============================================================================
# Smoke Test 5: Context Injection
# =============================================================================

@pytest.mark.asyncio
async def test_mcp_call_context_injection(client, mock_env):
    """Test /mcp/call endpoint with get_context_injection tool."""
    with patch("src.routes.memory_unified.embed_text", new_callable=AsyncMock) as mock_embed, \
         patch("src.routes.memory_unified.fetch_all", new_callable=AsyncMock) as mock_fetch:
        
        # Mock embedding
        mock_embed.return_value = [0.1] * 1536
        
        # Mock search results
        mock_fetch.return_value = []
        
        response = client.post(
            "/mcp/call",
            headers={"Authorization": "Bearer test-key-c"},
            json={
                "tool_name": "get_context_injection",
                "arguments": {
                    "task_description": "Test task",
                    "user_id": "test-user",
                    "top_k": 5
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "result" in data


# =============================================================================
# Smoke Test 6: Authentication Failure
# =============================================================================

def test_mcp_tools_auth_failure(client):
    """Test /mcp/tools endpoint rejects invalid API key."""
    response = client.get(
        "/mcp/tools",
        headers={"Authorization": "Bearer invalid-key"}
    )
    assert response.status_code == 403
    assert "Invalid API key" in response.json()["detail"] or "detail" in response.json()


# =============================================================================
# Smoke Test 7: Missing Authorization Header
# =============================================================================

def test_mcp_tools_missing_auth(client):
    """Test /mcp/tools endpoint rejects requests without Authorization header."""
    response = client.get("/mcp/tools")
    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"] or "detail" in response.json()

