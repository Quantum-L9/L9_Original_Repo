"""
Integration Tests for Graph to World Model Sync
================================================

Tests for the GraphToWorldModelSync service (UKG Phase 3).

Verifies:
- Sync service can be started and stopped
- Agent state is correctly transformed to WM entity
- Changes to graph state appear in World Model
- Feature flag controls enablement

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-3 (World Model Sync)
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test GraphToWorldModelSync Class
# =============================================================================

def test_sync_service_import():
    """Test that sync service can be imported."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    assert GraphToWorldModelSync is not None


def test_sync_service_defaults():
    """Test default configuration."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync()
    
    assert service.sync_interval_seconds == 300  # 5 minutes
    assert service._running is False
    assert service._sync_count == 0
    assert service._last_sync is None


def test_sync_service_custom_interval():
    """Test custom sync interval."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(sync_interval_seconds=60)
    
    assert service.sync_interval_seconds == 60


def test_sync_service_enabled_override():
    """Test enabled flag override."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    # Force enabled
    service = GraphToWorldModelSync(enabled=True)
    assert service.enabled is True
    
    # Force disabled
    service = GraphToWorldModelSync(enabled=False)
    assert service.enabled is False


# =============================================================================
# Test Start/Stop
# =============================================================================

@pytest.mark.asyncio
async def test_start_when_disabled():
    """Test that start does nothing when disabled."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=False)
    await service.start()
    
    assert service._running is False
    assert service._task is None


@pytest.mark.asyncio
async def test_stop_when_not_running():
    """Test that stop handles not-running gracefully."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=False)
    await service.stop()  # Should not raise
    
    assert service._running is False


# =============================================================================
# Test Transform
# =============================================================================

def test_transform_to_wm_entity():
    """Test transformation from graph state to WM entity."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync()
    
    graph_state = {
        "agent": {
            "designation": "CTO",
            "role": "Chief Technology Officer",
            "mission": "Build L9",
            "status": "ACTIVE",
            "authority_level": "SUPERVISOR",
        },
        "responsibilities": [
            {"title": "Architecture"},
            {"title": "Governance"},
        ],
        "directives": [
            {"text": "Be safe"},
            {"text": "Be helpful"},
        ],
        "tools": [
            {"name": "memory_read", "risk_level": "low"},
            {"name": "gmp_run", "risk_level": "high", "requires_approval": True},
        ],
    }
    
    entity = service._transform_to_wm_entity("L", graph_state)
    
    assert entity["entity_type"] == "agent"
    assert entity["entity_id"] == "agent:L"
    assert entity["name"] == "L"
    assert entity["attributes"]["designation"] == "CTO"
    assert entity["attributes"]["role"] == "Chief Technology Officer"
    assert entity["attributes"]["responsibility_count"] == 2
    assert entity["attributes"]["directive_count"] == 2
    assert entity["attributes"]["tool_count"] == 2
    assert "Architecture" in entity["attributes"]["responsibilities"]
    assert "gmp_run" in entity["attributes"]["high_risk_tools"]


def test_transform_handles_empty_state():
    """Test transformation with minimal/empty state."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync()
    
    graph_state = {
        "agent": {},
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }
    
    entity = service._transform_to_wm_entity("L", graph_state)
    
    assert entity["entity_id"] == "agent:L"
    assert entity["attributes"]["responsibility_count"] == 0
    assert entity["attributes"]["tool_count"] == 0


# =============================================================================
# Test sync_agent
# =============================================================================

@pytest.mark.asyncio
async def test_sync_agent_when_disabled():
    """Test sync_agent returns DISABLED when service disabled."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=False)
    result = await service.sync_agent("L")
    
    assert result["status"] == "DISABLED"
    assert result["agent_id"] == "L"


@pytest.mark.asyncio
async def test_sync_agent_success():
    """Test successful sync_agent call."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=True)
    
    # Mock the internal methods
    mock_graph_state = {
        "agent": {"designation": "CTO"},
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }
    
    with patch.object(service, '_load_from_graph', return_value=mock_graph_state):
        with patch.object(service, '_upsert_to_world_model', return_value=None):
            result = await service.sync_agent("L")
    
    assert result["status"] == "SUCCESS"
    assert result["agent_id"] == "L"
    assert "synced_at" in result
    assert service._sync_count == 1


@pytest.mark.asyncio
async def test_sync_agent_not_found():
    """Test sync_agent when agent not in graph."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=True)
    
    with patch.object(service, '_load_from_graph', return_value=None):
        result = await service.sync_agent("L")
    
    assert result["status"] == "NOT_FOUND"


# =============================================================================
# Test Status
# =============================================================================

def test_get_status():
    """Test status reporting."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=True, sync_interval_seconds=120)
    
    status = service.get_status()
    
    assert status["enabled"] is True
    assert status["running"] is False
    assert status["sync_count"] == 0
    assert status["last_sync"] is None
    assert status["sync_interval_seconds"] == 120


# =============================================================================
# Test Global Instance
# =============================================================================

def test_get_graph_wm_sync():
    """Test getting global instance."""
    from core.integration.graph_to_wm_sync import get_graph_wm_sync, GraphToWorldModelSync
    
    # Clear any existing instance
    import core.integration.graph_to_wm_sync as module
    module._sync_service = None
    
    service = get_graph_wm_sync()
    
    assert isinstance(service, GraphToWorldModelSync)
    
    # Second call returns same instance
    service2 = get_graph_wm_sync()
    assert service is service2
    
    # Cleanup
    module._sync_service = None


# =============================================================================
# Test Feature Flag
# =============================================================================

def test_feature_flag_from_env():
    """Test that feature flag is read from environment."""
    from core.integration import graph_to_wm_sync as module
    
    # Save original
    original = module.L9_GRAPH_WM_SYNC
    
    # Mock env
    with patch.dict(os.environ, {"L9_GRAPH_WM_SYNC": "true"}):
        # Reimport to pick up new env
        import importlib
        importlib.reload(module)
        
        service = module.GraphToWorldModelSync()
        assert service.enabled is True
    
    # Restore
    module.L9_GRAPH_WM_SYNC = original


# =============================================================================
# Test Integration with World Model Service
# =============================================================================

@pytest.mark.asyncio
async def test_upsert_to_world_model_integration():
    """Test that _upsert_to_world_model calls WorldModelService correctly."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=True)
    
    entity = {
        "entity_type": "agent",
        "entity_id": "agent:L",
        "name": "L",
        "attributes": {"designation": "CTO"},
    }
    
    # Mock WorldModelService by patching the import inside the method
    mock_wm_service = AsyncMock()
    mock_wm_service.upsert_entity = AsyncMock()
    
    mock_wm_module = MagicMock()
    mock_wm_module.WorldModelService = MagicMock(return_value=mock_wm_service)
    
    with patch.dict("sys.modules", {"world_model.service": mock_wm_module}):
        await service._upsert_to_world_model(entity)
    
    mock_wm_service.upsert_entity.assert_called_once_with(
        entity_type="agent",
        entity_id="agent:L",
        name="L",
        attributes={"designation": "CTO"},
    )


@pytest.mark.asyncio
async def test_upsert_handles_missing_wm_service():
    """Test graceful handling when WorldModelService not available."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync
    
    service = GraphToWorldModelSync(enabled=True)
    
    entity = {
        "entity_type": "agent",
        "entity_id": "agent:L",
        "name": "L",
        "attributes": {},
    }
    
    # Remove world_model.service from modules to trigger ImportError
    import sys
    original_module = sys.modules.get("world_model.service")
    
    # Temporarily remove/set to None to force ImportError
    sys.modules["world_model.service"] = None
    
    try:
        # Should not raise - handles ImportError gracefully
        await service._upsert_to_world_model(entity)
    finally:
        # Restore
        if original_module:
            sys.modules["world_model.service"] = original_module
        elif "world_model.service" in sys.modules:
            del sys.modules["world_model.service"]

