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
    """Tests for verify_websocket_auth helper function."""

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_verify_websocket_auth_with_query_token(self):
        """Verify auth helper accepts valid token from query params."""
        from api.server import verify_websocket_auth
        
        # Mock WebSocket with query params
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": TEST_API_KEY}
        
        # Should return True for valid token
        result = verify_websocket_auth(mock_ws, None)
        assert result is True

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_verify_websocket_auth_with_param_token(self):
        """Verify auth helper accepts valid token from parameter."""
        from api.server import verify_websocket_auth
        
        # Mock WebSocket without query params
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        
        # Should return True for valid token passed as param
        result = verify_websocket_auth(mock_ws, TEST_API_KEY)
        assert result is True

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_verify_websocket_auth_rejects_invalid_token(self):
        """Verify auth helper rejects invalid token."""
        from api.server import verify_websocket_auth
        
        # Mock WebSocket with wrong token
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "wrong-key"}
        
        # Should return False for invalid token
        result = verify_websocket_auth(mock_ws, None)
        assert result is False

    @patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": TEST_API_KEY})
    def test_verify_websocket_auth_rejects_missing_token(self):
        """Verify auth helper rejects missing token."""
        from api.server import verify_websocket_auth
        
        # Mock WebSocket without token
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        
        # Should return False for missing token
        result = verify_websocket_auth(mock_ws, None)
        assert result is False

    def test_verify_websocket_auth_no_config(self):
        """Verify auth helper returns False when key not configured."""
        # Clear the env var
        env = os.environ.copy()
        if "L9_EXECUTOR_API_KEY" in env:
            del env["L9_EXECUTOR_API_KEY"]
        
        with patch.dict(os.environ, env, clear=True):
            # Reload module to pick up empty env
            import importlib
            import api.server
            importlib.reload(api.server)
            
            from api.server import verify_websocket_auth
            
            mock_ws = MagicMock()
            mock_ws.query_params = {}
            
            # Should return False when key not configured
            result = verify_websocket_auth(mock_ws, "any-token")
            assert result is False
            
            # Restore for other tests
            importlib.reload(api.server)
