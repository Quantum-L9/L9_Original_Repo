"""
Tests for Graph State Consolidation
===================================

Tests for the consolidate_graph_state method in MemoryConsolidationService.
Part of UKG Phase 5: Memory Consolidation Loop.

Verifies:
- Graph state snapshots in consolidation output
- Consolidation includes agent directives count
- Graceful handling when graph not available

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-5 (Memory Consolidation Loop)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test Import
# =============================================================================

def test_memory_consolidation_service_import():
    """Test that MemoryConsolidationService can be imported."""
    from core.memory.virtual_context import MemoryConsolidationService
    assert MemoryConsolidationService is not None


def test_consolidation_service_has_graph_method():
    """Test that consolidate_graph_state method exists."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    assert hasattr(MemoryConsolidationService, 'consolidate_graph_state')


# =============================================================================
# Test consolidate_graph_state
# =============================================================================

@pytest.mark.asyncio
async def test_consolidate_graph_state_success():
    """Test successful graph state consolidation."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    # Mock substrate service
    mock_substrate = MagicMock()
    mock_substrate.write_memories = AsyncMock()
    
    service = MemoryConsolidationService(
        substrate_service=mock_substrate,
    )
    
    # Mock graph state
    mock_graph_state = {
        "agent": {
            "designation": "CTO",
            "status": "ACTIVE",
        },
        "responsibilities": [
            {"title": "Architecture"},
            {"title": "Governance"},
        ],
        "directives": [
            {"text": "Be safe"},
        ],
        "tools": [
            {"name": "memory_read"},
            {"name": "web_search"},
        ],
    }
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=mock_graph_state)
    
    # Patch where the import happens (inside core.agents.graph_state)
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state("L")
    
    assert result["status"] == "SUCCESS"
    assert "snapshot" in result
    
    snapshot = result["snapshot"]
    assert snapshot["agent_id"] == "L"
    assert snapshot["directives_count"] == 1
    assert snapshot["tools_count"] == 2
    assert "Architecture" in snapshot["responsibilities"]
    assert "Governance" in snapshot["responsibilities"]
    
    # Verify write_memories was called
    mock_substrate.write_memories.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_graph_state_not_found():
    """Test consolidation when agent not in graph."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=None)
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state("L")
    
    assert result["status"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_consolidate_graph_state_loader_unavailable():
    """Test graceful handling when AgentGraphLoader not available."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    # Make import fail by removing the module
    import sys
    original = sys.modules.get("core.agents.graph_state")
    sys.modules["core.agents.graph_state"] = None
    
    try:
        result = await service.consolidate_graph_state("L")
        # Should handle gracefully
        assert result["status"] in ["UNAVAILABLE", "ERROR"]
    finally:
        if original:
            sys.modules["core.agents.graph_state"] = original
        elif "core.agents.graph_state" in sys.modules:
            del sys.modules["core.agents.graph_state"]


@pytest.mark.asyncio
async def test_consolidate_graph_state_updates_metrics():
    """Test that metrics are updated after consolidation."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    mock_substrate.write_memories = AsyncMock()
    
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    initial_consolidations = service.metrics.get("consolidations", 0)
    
    mock_graph_state = {
        "agent": {},
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=mock_graph_state)
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        await service.consolidate_graph_state("L")
    
    assert service.metrics["consolidations"] == initial_consolidations + 1
    assert service.metrics.get("graph_state_snapshots", 0) >= 1


@pytest.mark.asyncio
async def test_consolidate_graph_state_default_agent():
    """Test that default agent is L."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    mock_substrate.write_memories = AsyncMock()
    
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    mock_graph_state = {
        "agent": {},
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=mock_graph_state)
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state()  # No agent_id
    
    # Should use default "L"
    mock_loader.load_agent_state.assert_called_once_with("L")
    assert result["snapshot"]["agent_id"] == "L"


# =============================================================================
# Test Snapshot Format
# =============================================================================

@pytest.mark.asyncio
async def test_snapshot_contains_required_fields():
    """Test that snapshot has all required fields."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    mock_substrate.write_memories = AsyncMock()
    
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    mock_graph_state = {
        "agent": {"designation": "CTO", "status": "ACTIVE"},
        "responsibilities": [{"title": "R1"}],
        "directives": [{"text": "D1"}, {"text": "D2"}],
        "tools": [{"name": "T1"}],
    }
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=mock_graph_state)
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state("L")
    
    snapshot = result["snapshot"]
    
    # Required fields
    assert "agent_id" in snapshot
    assert "timestamp" in snapshot
    assert "responsibilities" in snapshot
    assert "directives_count" in snapshot
    assert "tools_count" in snapshot
    assert "designation" in snapshot
    assert "status" in snapshot
    
    # Correct values
    assert snapshot["directives_count"] == 2
    assert snapshot["tools_count"] == 1
    assert snapshot["designation"] == "CTO"
    assert snapshot["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_snapshot_limits_responsibilities():
    """Test that snapshot limits responsibilities to first 5."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    mock_substrate.write_memories = AsyncMock()
    
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    # 10 responsibilities
    mock_graph_state = {
        "agent": {},
        "responsibilities": [{"title": f"R{i}"} for i in range(10)],
        "directives": [],
        "tools": [],
    }
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(return_value=mock_graph_state)
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state("L")
    
    # All 10 should be in responsibilities
    assert len(result["snapshot"]["responsibilities"]) == 10
    
    # But fact should only mention first 5
    fact_call = mock_substrate.write_memories.call_args
    facts = fact_call[0][1]  # Second positional arg
    fact_text = facts[0]
    
    # Should not include all 10 in the fact
    assert "R0" in fact_text
    assert "R4" in fact_text


# =============================================================================
# Test Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_consolidate_graph_state_exception_handling():
    """Test graceful exception handling."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    mock_loader = MagicMock()
    mock_loader.load_agent_state = AsyncMock(side_effect=RuntimeError("Neo4j error"))
    
    with patch("core.agents.graph_state.AgentGraphLoader", return_value=mock_loader):
        result = await service.consolidate_graph_state("L")
    
    assert result["status"] == "ERROR"
    assert "error" in result


# =============================================================================
# Test get_metrics
# =============================================================================

def test_get_metrics_includes_graph_snapshots():
    """Test that get_metrics returns graph_state_snapshots."""
    from core.memory.virtual_context import MemoryConsolidationService
    
    mock_substrate = MagicMock()
    service = MemoryConsolidationService(substrate_service=mock_substrate)
    
    # Set up metrics
    service.metrics["graph_state_snapshots"] = 5
    
    metrics = service.get_metrics()
    
    assert "graph_state_snapshots" in metrics
    assert metrics["graph_state_snapshots"] == 5

