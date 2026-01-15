"""
Test fixtures for memory governance tests.

These fixtures support the governance invariant regression tests.
Run: pytest tests/memory/test_governance_invariants.py -v
"""

import os
import pytest
from typing import AsyncGenerator, Dict, Any

# Set test API keys before importing app modules
os.environ["MCP_API_KEY_L"] = "test-lcto-key-all-scopes"
os.environ["MCP_API_KEY_C"] = "test-cursor-key-dev-global"
os.environ["GOVERNANCE_HARDENING_ENABLED"] = "True"
os.environ["GOVERNANCE_ENFORCEMENT_MODE"] = "enforce"


@pytest.fixture
def cursor_auth() -> Dict[str, str]:
    """Cursor API key with developer+global scopes only."""
    return {"Authorization": "Bearer test-cursor-key-dev-global"}


@pytest.fixture
def l_auth() -> Dict[str, str]:
    """L-CTO API key with all scopes including l-private."""
    return {"Authorization": "Bearer test-lcto-key-all-scopes"}


@pytest.fixture
def no_auth() -> Dict[str, str]:
    """No authentication headers (should be rejected)."""
    return {}


@pytest.fixture
def invalid_auth() -> Dict[str, str]:
    """Invalid authentication token (should be rejected)."""
    return {"Authorization": "Bearer invalid-token-should-fail"}
