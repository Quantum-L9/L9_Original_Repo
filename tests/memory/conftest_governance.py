"""
Test fixtures for memory governance tests.

These fixtures support the governance invariant regression tests.
Run: pytest tests/memory/test_governance_invariants.py -v
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Conftest Governance",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T11:17:09Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "conftest_governance",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os

import pytest

# Set test API keys before importing app modules
os.environ["MCP_API_KEY_L"] = "test-lcto-key-all-scopes"
os.environ["MCP_API_KEY_C"] = "test-cursor-key-dev-global"
os.environ["GOVERNANCE_HARDENING_ENABLED"] = "True"
os.environ["GOVERNANCE_ENFORCEMENT_MODE"] = "enforce"


@pytest.fixture
def cursor_auth() -> dict[str, str]:
    """Cursor API key with developer+global scopes only."""
    return {"Authorization": "Bearer test-cursor-key-dev-global"}


@pytest.fixture
def l_auth() -> dict[str, str]:
    """L-CTO API key with all scopes including l-private."""
    return {"Authorization": "Bearer test-lcto-key-all-scopes"}


@pytest.fixture
def no_auth() -> dict[str, str]:
    """No authentication headers (should be rejected)."""
    return {}


@pytest.fixture
def invalid_auth() -> dict[str, str]:
    """Invalid authentication token (should be rejected)."""
    return {"Authorization": "Bearer invalid-token-should-fail"}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "memory-substrate", "operations", "test", "testing"],
    "keywords": [
        "auth",
        "conftest",
        "cursor",
        "fixtures",
        "governance",
        "invalid",
        "memory",
        "tests",
    ],
    "business_value": "Utility module for conftest governance",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
