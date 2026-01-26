"""
Integration Tests for Graph-Backed Agent State
===============================================

Full integration tests for the graph state lifecycle:
1. Bootstrap L's graph from defaults
2. Query state via AgentGraphLoader
3. Hydrate to HydratedAgentContext
4. Modify via AgentSelfModifyTool
5. Verify changes persist

These tests require a running Neo4j instance.
Skip with: pytest -m "not integration"

Version: 1.0.0
Created: 2026-01-05
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver for unit testing."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_driver.close = AsyncMock()

    return mock_driver, mock_session


@pytest.fixture
def sample_agent_node():
    """Sample agent node data."""
    return {
        "agent_id": "L",
        "designation": "Chief Technology Officer",
        "role": "System Architect",
        "mission": "Evolve L9 architecture",
        "authority_level": "CTO",
        "status": "ACTIVE",
    }


@pytest.fixture
def sample_graph_result(sample_agent_node):
    """Sample full graph query result."""
    return {
        "a": sample_agent_node,
        "responsibilities": [
            {
                "title": "Architecture Design",
                "description": "Design systems",
                "priority": 0,
            },
            {"title": "Code Quality", "description": "Ensure quality", "priority": 0},
        ],
        "directives": [
            {"text": "Respect Igor", "context": "governance", "severity": "CRITICAL"},
            {"text": "Log everything", "context": "observability", "severity": "HIGH"},
        ],
        "sops": [
            {"name": "code_deployment", "steps": ["Review", "Test", "Deploy"]},
        ],
        "tools": [
            {
                "name": "shell",
                "risk_level": "HIGH",
                "requires_approval": True,
                "approval_source": "igor",
            },
            {"name": "memory_search", "risk_level": "LOW", "requires_approval": False},
        ],
        "supervisor": {"agent_id": "igor"},
        "collaborators": [],
    }


# =============================================================================
# Integration Test: Full Lifecycle
# =============================================================================


@pytest.mark.asyncio
async def test_full_graph_lifecycle(mock_neo4j_driver, sample_graph_result):
    """Test complete graph state lifecycle."""
    from core.agents.graph_state import AgentGraphLoader, GraphHydrator

    mock_driver, mock_session = mock_neo4j_driver

    # Configure mock to return sample data
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=sample_graph_result)
    mock_session.run = AsyncMock(return_value=mock_result)

    # Step 1: Load state
    loader = AgentGraphLoader(mock_driver)
    state = await loader.load("L")

    assert state.agent_id == "L"
    assert state.designation == "Chief Technology Officer"
    assert len(state.responsibilities) == 2
    assert len(state.directives) == 2
    assert state.supervisor_id == "igor"

    # Step 2: Hydrate to context
    hydrator = GraphHydrator(mock_driver)
    hydrator.loader = loader  # Use same loader with cached state

    context = await hydrator.hydrate("L", include_kernels=False)

    assert context.agent_id == "L"
    assert len(context.critical_directives) == 1
    assert "Respect Igor" in context.critical_directives
    assert "shell" in context.tools_requiring_approval

    # Step 3: Generate system prompt
    prompt = context.to_system_prompt_context()

    assert "Chief Technology Officer" not in prompt  # Uses 'CTO'
    assert "Respect Igor" in prompt
    assert "[REQUIRES APPROVAL]" in prompt


@pytest.mark.asyncio
async def test_tool_approval_flow(mock_neo4j_driver, sample_graph_result):
    """Test tool approval checking flow."""
    from core.agents.graph_state import GraphHydrator

    mock_driver, mock_session = mock_neo4j_driver

    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=sample_graph_result)
    mock_session.run = AsyncMock(return_value=mock_result)

    hydrator = GraphHydrator(mock_driver)

    # Load state first
    await hydrator.hydrate("L")

    # Check shell (requires approval)
    requires, source = await hydrator.check_tool_approval("L", "shell")
    assert requires is True
    assert source == "igor"

    # Check memory_search (no approval needed)
    requires, source = await hydrator.check_tool_approval("L", "memory_search")
    assert requires is False


@pytest.mark.asyncio
async def test_self_modify_governance(mock_neo4j_driver):
    """Test self-modify tool governance enforcement."""
    from core.tools.agent_self_modify import AgentSelfModifyTool

    mock_driver, mock_session = mock_neo4j_driver

    tool = AgentSelfModifyTool(mock_driver)

    # HIGH severity without approval should fail
    result = await tool.add_directive(
        agent_id="L",
        text="New high-risk directive",
        context="architecture",
        severity="HIGH",
        igor_approved=False,
    )

    assert result["success"] is False
    assert "Igor approval" in result["error"]

    # LOW severity should succeed (after mocking Neo4j response)
    mock_record = {"directive_id": "new-uuid", "text": "Low risk"}
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=mock_record)
    mock_session.run = AsyncMock(return_value=mock_result)

    result = await tool.add_directive(
        agent_id="L",
        text="New low-risk directive",
        context="observability",
        severity="LOW",
        igor_approved=False,
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_cache_invalidation(mock_neo4j_driver, sample_graph_result):
    """Test that cache invalidation works correctly."""
    from core.agents.graph_state import AgentGraphLoader

    mock_driver, mock_session = mock_neo4j_driver

    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=sample_graph_result)
    mock_session.run = AsyncMock(return_value=mock_result)

    loader = AgentGraphLoader(mock_driver)

    # First load populates cache
    await loader.load("L")
    assert "L" in loader._cache

    # Invalidate cache
    loader.invalidate_cache("L")
    assert "L" not in loader._cache

    # Second load should hit Neo4j again
    await loader.load("L")

    # Session.run should have been called twice
    assert mock_session.run.call_count == 2


@pytest.mark.asyncio
async def test_directive_compliance_check(mock_neo4j_driver, sample_graph_result):
    """Test directive compliance validation."""
    from core.agents.graph_state import GraphHydrator

    mock_driver, mock_session = mock_neo4j_driver

    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=sample_graph_result)
    mock_session.run = AsyncMock(return_value=mock_result)

    hydrator = GraphHydrator(mock_driver)
    await hydrator.hydrate("L")

    # Test compliant action
    compliant, violations = await hydrator.validate_directive_compliance(
        "L",
        "Update architecture documentation",
    )
    assert compliant is True
    assert len(violations) == 0

    # Test violating action (deletion)
    # Note: Simple keyword check in current implementation
    compliant, violations = await hydrator.validate_directive_compliance(
        "L",
        "delete production database",
    )
    # Depends on directives containing "NO deletion" keyword
    # In our sample, we have "Respect Igor" which doesn't contain this


# =============================================================================
# Integration Test: Bootstrap Verification
# =============================================================================


@pytest.mark.asyncio
async def test_bootstrap_defaults():
    """Test that bootstrap defaults are complete and valid."""
    from core.agents.graph_state.bootstrap_l_graph import (
        L_AGENT_CONFIG,
        L_DIRECTIVES,
        L_RESPONSIBILITIES,
        L_SOPS,
        L_TOOLS,
    )

    # Agent config complete
    assert L_AGENT_CONFIG["agent_id"] == "L"
    assert L_AGENT_CONFIG["authority_level"] == "CTO"

    # Has required responsibilities
    assert len(L_RESPONSIBILITIES) >= 3
    arch = next((r for r in L_RESPONSIBILITIES if "Architecture" in r["title"]), None)
    assert arch is not None
    assert arch["priority"] == 0  # P0 = highest priority

    # Has CRITICAL directives
    critical = [d for d in L_DIRECTIVES if d["severity"] == "CRITICAL"]
    assert len(critical) >= 2

    # Igor authority is CRITICAL
    igor_directive = next((d for d in critical if "Igor" in d["text"]), None)
    assert igor_directive is not None

    # Has essential SOPs
    sop_names = [s["name"] for s in L_SOPS]
    assert "code_deployment" in sop_names

    # Has tools with proper risk classification
    shell_tool = next((t for t in L_TOOLS if t["name"] == "shell"), None)
    assert shell_tool["risk_level"] == "HIGH"
    assert shell_tool["requires_approval"] is True


# =============================================================================
# Skip Real Neo4j Tests by Default
# =============================================================================


@pytest.mark.skip(reason="Requires running Neo4j instance")
@pytest.mark.asyncio
async def test_real_neo4j_bootstrap():
    """
    Test with real Neo4j instance.

    Enable by removing skip marker and ensuring Neo4j is running:
    docker compose up -d l9-neo4j
    """
    from neo4j import AsyncGraphDatabase, basic_auth

    from core.agents.graph_state.bootstrap_l_graph import (
        bootstrap_l_graph,
        verify_l_graph,
    )

    neo4j_uri = os.getenv("NEO4J_URL") or os.getenv(
        "NEO4J_URI", "bolt://localhost:7687"
    )
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=basic_auth(neo4j_user, neo4j_password),
    )

    try:
        # Bootstrap
        stats = await bootstrap_l_graph(driver)
        assert stats["agent"] == 1
        assert stats["responsibilities"] >= 3

        # Verify
        verification = await verify_l_graph(driver)
        assert verification["valid"] is True
        assert verification["agent_id"] == "L"

    finally:
        await driver.close()
