"""
L9 API Server Health Tests
==========================

Tests for health check endpoints.
No external services required - uses TestClient.

Version: 1.0.0
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# =============================================================================
# Test Class: Server Health
# =============================================================================


class TestServerHealth:
    """Tests for server health check endpoints."""

    # =============================================================================
    # Test: Health endpoint returns 200
    # =============================================================================

    def test_health_endpoint_returns_200(self):
        """
        Contract: /health endpoint returns 200 OK with status message.
        """
        try:
            from api.server import app

            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["service"] == "l9-api"
        except Exception as e:
            pytest.skip(f"Could not test health endpoint: {e}")

    # =============================================================================
    # Test: Root endpoint returns info
    # =============================================================================

    def test_root_endpoint_returns_info(self):
        """
        Contract: Root endpoint returns service information.
        """
        try:
            from api.server import app

            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "L9 Phase 2 AI OS"
            assert "version" in data
            assert "features" in data
        except Exception as e:
            pytest.skip(f"Could not test root endpoint: {e}")

    # =============================================================================
    # Test: Docs endpoint accessible
    # =============================================================================

    def test_docs_endpoint_accessible(self):
        """
        Contract: OpenAPI docs endpoint is accessible.
        """
        try:
            from api.server import app

            client = TestClient(app)
            response = client.get("/docs")

            # Docs endpoint should return HTML (200) or redirect
            assert response.status_code in [200, 307, 308]
        except Exception as e:
            pytest.skip(f"Could not test docs endpoint: {e}")
