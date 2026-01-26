"""
L9 API Auth Tests
=================

Tests for API key authentication module.
No external services required.

Version: 1.0.0
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

# =============================================================================
# Test Class: Auth Validation
# =============================================================================


class TestAuthValidation:
    """Tests for API key authentication validation."""

    # =============================================================================
    # Test: Valid API key passes
    # =============================================================================

    def test_valid_api_key_passes(self):
        """
        Contract: Valid API key in Authorization header passes verification.
        """
        test_key = "test-executor-key-12345"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            # Import after patching env
            from api.auth import verify_api_key

            # Should not raise
            result = verify_api_key(authorization=f"Bearer {test_key}")

            # verify_api_key returns None on success (no exception)
            assert result is None, "Valid API key should return None (no exception)"

    # =============================================================================
    # Test: Invalid API key fails
    # =============================================================================

    def test_invalid_api_key_fails(self):
        """
        Contract: Invalid API key returns 401 Unauthorized.
        """
        test_key = "correct-key"
        wrong_key = "wrong-key"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            from api.auth import verify_api_key

            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(authorization=f"Bearer {wrong_key}")

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized, got {exc_info.value.status_code}"
            )
            assert "Unauthorized" in exc_info.value.detail, (
                f"Expected 'Unauthorized' in detail, got: {exc_info.value.detail}"
            )

    # =============================================================================
    # Test: Missing auth header fails
    # =============================================================================

    def test_missing_auth_header_fails(self):
        """
        Contract: Missing Authorization header returns 401 Unauthorized.
        """
        test_key = "test-key"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            from api.auth import verify_api_key

            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(authorization=None)

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized, got {exc_info.value.status_code}"
            )
            assert "Unauthorized" in exc_info.value.detail, (
                f"Expected 'Unauthorized' in detail, got: {exc_info.value.detail}"
            )

    # =============================================================================
    # Test: Missing executor key config fails
    # =============================================================================

    def test_missing_executor_key_config_fails(self):
        """
        Contract: If L9_EXECUTOR_API_KEY is not configured, returns 500.
        """
        # Clear the env var
        env = os.environ.copy()
        if "L9_EXECUTOR_API_KEY" in env:
            del env["L9_EXECUTOR_API_KEY"]

        with patch.dict(os.environ, env, clear=True):
            # Need to reimport to pick up empty env
            import importlib

            import api.auth

            importlib.reload(api.auth)

            with pytest.raises(HTTPException) as exc_info:
                api.auth.verify_api_key(authorization="Bearer some-key")

            assert exc_info.value.status_code == 500, (
                f"Expected 500 Internal Server Error, got {exc_info.value.status_code}"
            )
            assert "not configured" in exc_info.value.detail, (
                f"Expected 'not configured' in detail, got: {exc_info.value.detail}"
            )

    # =============================================================================
    # Test: Malformed bearer token fails
    # =============================================================================

    def test_malformed_bearer_token_fails(self):
        """
        Contract: Malformed Bearer token returns 401.
        """
        test_key = "correct-key"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            # Reload module to pick up new env value
            import importlib

            import api.auth

            importlib.reload(api.auth)

            # No "Bearer " prefix
            with pytest.raises(HTTPException) as exc_info:
                api.auth.verify_api_key(authorization=test_key)

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized for malformed token, got {exc_info.value.status_code}"
            )

    # =============================================================================
    # Edge Case Tests
    # =============================================================================

    def test_auth_empty_token(self):
        """
        Contract: Empty token is rejected.
        """
        test_key = "correct-key"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            from api.auth import verify_api_key

            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(authorization="Bearer ")

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized, got {exc_info.value.status_code}"
            )

    def test_auth_whitespace_token(self):
        """
        Contract: Whitespace-only token is rejected.
        """
        test_key = "correct-key"

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            from api.auth import verify_api_key

            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(authorization="Bearer    ")

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized, got {exc_info.value.status_code}"
            )

    def test_auth_very_long_token(self):
        """
        Contract: Excessively long token is rejected.
        """
        test_key = "correct-key"
        very_long_token = "x" * 10000  # 10KB token

        with patch.dict(os.environ, {"L9_EXECUTOR_API_KEY": test_key}):
            from api.auth import verify_api_key

            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(authorization=f"Bearer {very_long_token}")

            assert exc_info.value.status_code == 401, (
                f"Expected 401 Unauthorized, got {exc_info.value.status_code}"
            )
