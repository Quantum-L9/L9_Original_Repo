"""
L9 WebSocket Auth Tests
========================

Tests for WebSocket endpoint authentication:
- /ws/agent requires authentication
- /lws requires authentication

Note: These tests verify the authentication logic. Full WebSocket integration
tests require a running server and are better suited for integration test suite.

Version: 1.0.0
"""

import os
from unittest.mock import patch, MagicMock

# =============================================================================
# Configuration
# =============================================================================

TEST_API_KEY = "test-executor-key-12345"


# =============================================================================
# Test: WebSocket Auth Helper Function
# =============================================================================


class TestWebSocketAuthHelper:
    """Tests for verify_ws_token helper function (unified auth)."""

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    async def test_verify_ws_token_with_query_token(self):
        """Verify auth helper accepts valid token from query params."""
        from runtime.websocket_orchestrator import verify_ws_token

        # Mock WebSocket with query params
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": TEST_API_KEY}
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        # Should return True for valid token
        result = await verify_ws_token(mock_ws, None)
        assert result is True

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    async def test_verify_ws_token_with_param_token(self):
        """Verify auth helper accepts valid token from parameter."""
        from runtime.websocket_orchestrator import verify_ws_token

        # Mock WebSocket without query params
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        # Should return True for valid token passed as param
        result = await verify_ws_token(mock_ws, TEST_API_KEY)
        assert result is True

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    async def test_verify_ws_token_rejects_invalid_token(self):
        """Verify auth helper rejects invalid token."""
        from runtime.websocket_orchestrator import verify_ws_token

        # Mock WebSocket with wrong token
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "wrong-key"}
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        # Should return False for invalid token
        result = await verify_ws_token(mock_ws, None)
        assert result is False

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    async def test_verify_ws_token_rejects_missing_token(self):
        """Verify auth helper rejects missing token."""
        from runtime.websocket_orchestrator import verify_ws_token

        # Mock WebSocket without token
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.client = MagicMock()
        mock_ws.client.host = "127.0.0.1"

        # Should return False for missing token
        result = await verify_ws_token(mock_ws, None)
        assert result is False

    async def test_verify_ws_token_no_config(self):
        """Verify auth helper returns False when key not configured."""
        # Clear the env var
        env = os.environ.copy()
        if "L9_EXECUTOR_API_KEY" in env:
            del env["L9_EXECUTOR_API_KEY"]

        with patch.dict(os.environ, env, clear=True):
            # Reload module to pick up empty env
            import importlib
            import runtime.websocket_orchestrator

            importlib.reload(runtime.websocket_orchestrator)

            from runtime.websocket_orchestrator import verify_ws_token

            mock_ws = MagicMock()
            mock_ws.query_params = {}
            mock_ws.client = MagicMock()
            mock_ws.client.host = "127.0.0.1"

            # Should return False when key not configured
            result = await verify_ws_token(mock_ws, "any-token")
            assert result is False

            # Restore for other tests
            importlib.reload(runtime.websocket_orchestrator)
