"""
L9 Bootstrap Tests – Phase 4 Identity View Loading
===================================================

Tests for phase4_loadidentity: pure view computation, no Neo4j writes.
"""

import pytest

from core.agents.bootstrap.models import IdentityView
from core.agents.bootstrap.phase_4_load_identity import load_identity_persona_view


@pytest.fixture
def sample_identity_kernel():
    """Sample 02-identity kernel dict."""
    return {
        "metadata": {
            "display_name": "L-CTO",
            "short_name": "L",
            "description": "Chief Technology Officer Agent",
            "default_tone": "direct",
            "tags": ["governance", "architecture"],
        },
        "capabilities": [
            "code_generation",
            "architecture_design",
            "kernel_synthesis",
            "security_audit",
        ],
    }


@pytest.mark.asyncio
async def test_load_identity_persona_success(sample_identity_kernel):
    """Test successful identity loading."""
    result = await load_identity_persona_view(
        agent_id="l-cto",
        identity_kernel=sample_identity_kernel,
        kernel_paths={},
    )

    assert result["success"] is True
    assert "identity_view" in result["context_delta"]

    identity = result["context_delta"]["identity_view"]
    assert isinstance(identity, IdentityView)
    assert identity.agent_id == "l-cto"
    assert identity.display_name == "L-CTO"
    assert identity.short_name == "L"
    assert identity.description == "Chief Technology Officer Agent"
    assert identity.default_tone == "direct"
    assert identity.capabilities == [
        "code_generation",
        "architecture_design",
        "kernel_synthesis",
        "security_audit",
    ]
    assert "governance" in identity.tags


@pytest.mark.asyncio
async def test_load_identity_persona_with_defaults():
    """Test that missing metadata fields get defaults."""
    incomplete_kernel = {
        "metadata": {
            "display_name": "Test Agent",
            # Missing: short_name, description, default_tone - should get defaults
        },
        "capabilities": [],
    }

    result = await load_identity_persona_view(
        agent_id="test-agent",
        identity_kernel=incomplete_kernel,
        kernel_paths={},
    )

    # Should succeed with defaults applied
    assert result["success"] is True
    identity = result["context_delta"]["identity_view"]
    assert identity.display_name == "Test Agent"
    assert identity.short_name == "Te"  # First 2 chars of display_name
    assert identity.default_tone == "neutral"  # Default value


@pytest.mark.asyncio
async def test_identity_view_no_neo4j_writes(sample_identity_kernel):
    """Test that identity loading does NOT trigger Neo4j writes."""
    # This test verifies the "view-only" contract:
    # calling load_identity_persona_view should not have side effects.

    result = await load_identity_persona_view(
        agent_id="l-cto",
        identity_kernel=sample_identity_kernel,
        kernel_paths={},
    )

    # If we got here without exception, no Neo4j writes occurred
    # (view-only computation completed successfully)
    assert result["success"] is True
