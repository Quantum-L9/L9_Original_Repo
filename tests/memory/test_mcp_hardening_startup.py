"""Tests for MCP memory server hardening startup functions."""

import os
import sys
import pytest

# Add mcp_memory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_memory"))

# Set required env vars before importing main (config validates on import)
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("MEMORY_DSN", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("MCP_API_KEY_L", "test-lcto-key-all-scopes")
os.environ.setdefault("MCP_API_KEY_C", "test-cursor-key-dev-global")


from mcp_memory.src.main import (
    is_non_dev_environment,
    should_fail_hardening_disabled,
    should_fail_hardening_disabled_async,
)


def test_is_non_dev_environment():
    """Test environment classification for hardening decisions."""
    # Non-dev environments (should fail if hardening disabled)
    assert is_non_dev_environment("production") is True
    assert is_non_dev_environment("staging") is True
    assert is_non_dev_environment("prod") is True
    assert is_non_dev_environment("") is True  # Empty defaults to non-dev

    # Dev-like environments (safe to run without hardening)
    assert is_non_dev_environment("development") is False
    assert is_non_dev_environment("Development") is False  # Case insensitive
    assert is_non_dev_environment("dev") is False
    assert is_non_dev_environment("local") is False
    assert is_non_dev_environment("test") is False
    assert is_non_dev_environment("testing") is False
    assert is_non_dev_environment("  TEST  ") is False  # Whitespace trimmed


def test_should_fail_hardening_disabled():
    """Test sync hardening decision function."""
    # Production + hardening disabled = FAIL
    assert should_fail_hardening_disabled("production", False) is True

    # Development + hardening disabled = OK (don't fail)
    assert should_fail_hardening_disabled("development", False) is False
    assert should_fail_hardening_disabled("test", False) is False

    # Any env + hardening enabled = OK (don't fail)
    assert should_fail_hardening_disabled("production", True) is False
    assert should_fail_hardening_disabled("development", True) is False


@pytest.mark.asyncio
async def test_should_fail_hardening_disabled_async():
    """Test async hardening decision function (wrapper for sync version)."""
    # Production + hardening disabled = FAIL
    result = await should_fail_hardening_disabled_async("production", False)
    assert result is True

    # Development + hardening disabled = OK
    result = await should_fail_hardening_disabled_async("development", False)
    assert result is False

    # Production + hardening enabled = OK
    result = await should_fail_hardening_disabled_async("production", True)
    assert result is False
