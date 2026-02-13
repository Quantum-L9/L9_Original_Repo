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

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.decorators import must_stay_async

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

    service = GraphToWorldModelSync(neo4j_driver="mock")  # GMP-90: driver required

    assert service.sync_interval_seconds == 300  # 5 minutes
    assert service._running is False
    assert service._sync_count == 0
    assert service._last_sync is None


def test_sync_service_custom_interval():
    """Test custom sync interval."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", sync_interval_seconds=60)

    assert service.sync_interval_seconds == 60


def test_sync_service_enabled_override():
    """Test enabled flag override."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    # Force enabled
    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=True)
    assert service.enabled is True

    # Force disabled
    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=False)
    assert service.enabled is False


def test_sync_service_requires_neo4j_driver():
    """Test that neo4j_driver is required (GMP-90)."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    with pytest.raises(ValueError, match="requires neo4j_driver"):
        GraphToWorldModelSync(neo4j_driver=None)


# =============================================================================
# Test Start/Stop
# =============================================================================


@pytest.mark.asyncio
async def test_start_when_disabled():
    """Test that start does nothing when disabled."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=False)
    await service.start()

    assert service._running is False
    assert service._task is None


@pytest.mark.asyncio
async def test_stop_when_not_running():
    """Test that stop handles not-running gracefully."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=False)
    await service.stop()  # Should not raise

    assert service._running is False


# =============================================================================
# Test Transform
# =============================================================================


def test_transform_to_wm_entity():
    """Test transformation from graph state to WM entity.

    IMPORTANT: _load_from_graph returns a FLAT dict structure, not nested.
    This was the root cause of the silent failure bug (PR #103).
    """
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock")  # GMP-90 requires driver

    # FIXED: Use FLAT structure matching _load_from_graph output
    # BUG FIX (PR #103): Previously used nested {"agent": {...}} which caused
    # all attributes to be empty strings (silent failure)
    graph_state = {
        "agent_id": "L",
        "designation": "CTO",
        "role": "Chief Technology Officer",
        "mission": "Build L9",
        "status": "ACTIVE",
        "authority_level": "SUPERVISOR",
        "supervisor_id": "Igor",
        "responsibilities": [
            {"title": "Architecture", "description": "System design", "priority": 1},
            {"title": "Governance", "description": "Policy enforcement", "priority": 2},
        ],
        "directives": [
            {"text": "Be safe", "context": "always", "severity": "critical"},
            {"text": "Be helpful", "context": "default", "severity": "normal"},
        ],
        "tools": [
            {"name": "memory_read", "risk_level": "low", "requires_approval": False},
            {"name": "gmp_run", "risk_level": "high", "requires_approval": True},
        ],
    }

    entity = service._transform_to_wm_entity("L", graph_state)

    assert entity["entity_type"] == "agent"
    assert entity["entity_id"] == "agent:L"
    assert entity["name"] == "L"
    assert entity["attributes"]["designation"] == "CTO"
    assert entity["attributes"]["role"] == "Chief Technology Officer"
    assert entity["attributes"]["mission"] == "Build L9"
    assert entity["attributes"]["status"] == "ACTIVE"
    assert entity["attributes"]["authority_level"] == "SUPERVISOR"
    assert entity["attributes"]["responsibility_count"] == 2
    assert entity["attributes"]["directive_count"] == 2
    assert entity["attributes"]["tool_count"] == 2
    assert "Architecture" in entity["attributes"]["responsibilities"]
    assert "gmp_run" in entity["attributes"]["high_risk_tools"]


def test_transform_preserves_actual_data_not_empty():
    """REGRESSION TEST: Verify attributes are NOT empty after transform.

    This test catches the silent failure bug from PR #103 where data
    structure mismatch caused all attributes to be empty strings.
    """
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock")

    # Realistic graph state from _load_from_graph (FLAT structure)
    graph_state = {
        "agent_id": "L",
        "designation": "CTO",
        "role": "Chief Technology Officer",
        "mission": "Build secure AI runtime",
        "status": "ACTIVE",
        "authority_level": "SUPERVISOR",
        "supervisor_id": "Igor",
        "responsibilities": [
            {"title": "Architecture", "description": "", "priority": 1}
        ],
        "directives": [{"text": "Be safe", "context": "", "severity": ""}],
        "tools": [
            {"name": "memory_read", "risk_level": "low", "requires_approval": False}
        ],
    }

    entity = service._transform_to_wm_entity("L", graph_state)

    # CRITICAL: These must NOT be empty strings!
    # The original bug caused all these to be "" (empty)
    assert entity["attributes"]["designation"] != "", "designation should not be empty"
    assert entity["attributes"]["role"] != "", "role should not be empty"
    assert entity["attributes"]["mission"] != "", "mission should not be empty"
    assert entity["attributes"]["authority_level"] != "", (
        "authority_level should not be empty"
    )

    # Verify actual values match input
    assert entity["attributes"]["designation"] == "CTO"
    assert entity["attributes"]["role"] == "Chief Technology Officer"
    assert entity["attributes"]["mission"] == "Build secure AI runtime"


def test_transform_handles_empty_state():
    """Test transformation with minimal/empty state.

    FIXED: Use FLAT structure (no nested "agent" key).
    """
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock")

    # FLAT structure with empty/default values
    graph_state = {
        "agent_id": "L",
        "designation": "",
        "role": "",
        "mission": "",
        "status": "ACTIVE",  # Default status
        "authority_level": "",
        "supervisor_id": None,
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }

    entity = service._transform_to_wm_entity("L", graph_state)

    assert entity["entity_id"] == "agent:L"
    assert entity["attributes"]["responsibility_count"] == 0
    assert entity["attributes"]["directive_count"] == 0
    assert entity["attributes"]["tool_count"] == 0
    assert entity["attributes"]["status"] == "ACTIVE"


# =============================================================================
# Test sync_agent
# =============================================================================


@pytest.mark.asyncio
async def test_sync_agent_when_disabled():
    """Test sync_agent returns DISABLED when service disabled."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=False)
    result = await service.sync_agent("L")

    assert result["status"] == "DISABLED"
    assert result["agent_id"] == "L"


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_sync_agent_success():
    """Test successful sync_agent call.

    FIXED: Use FLAT structure for mock_graph_state (PR #103 bug fix).
    """
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=True)

    # FIXED: Mock with FLAT structure matching _load_from_graph output
    mock_graph_state = {
        "agent_id": "L",
        "designation": "CTO",
        "role": "Chief Technology Officer",
        "mission": "Build L9",
        "status": "ACTIVE",
        "authority_level": "SUPERVISOR",
        "supervisor_id": "Igor",
        "responsibilities": [],
        "directives": [],
        "tools": [],
    }

    with patch.object(service, "_load_from_graph", return_value=mock_graph_state):
        with patch.object(service, "_upsert_to_world_model", return_value=None):
            result = await service.sync_agent("L")

    assert result["status"] == "SUCCESS"
    assert result["agent_id"] == "L"
    assert "synced_at" in result
    assert service._sync_count == 1


@pytest.mark.asyncio
async def test_sync_agent_not_found():
    """Test sync_agent when agent not in graph."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=True)

    with patch.object(service, "_load_from_graph", return_value=None):
        result = await service.sync_agent("L")

    assert result["status"] == "NOT_FOUND"


# =============================================================================
# Test Status
# =============================================================================


def test_get_status():
    """Test status reporting."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(
        neo4j_driver="mock", enabled=True, sync_interval_seconds=120
    )

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
    # Clear any existing instance
    import core.integration.graph_to_wm_sync as module
    from core.integration.graph_to_wm_sync import (
        GraphToWorldModelSync,
        get_graph_wm_sync,
    )

    module._sync_service = None

    service = get_graph_wm_sync(neo4j_driver="mock")  # GMP-90: driver required

    assert isinstance(service, GraphToWorldModelSync)

    # Second call returns same instance (uses cached)
    service2 = get_graph_wm_sync(
        neo4j_driver="another_mock"
    )  # driver ignored on second call
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

        service = module.GraphToWorldModelSync(neo4j_driver="mock")  # GMP-90: required
        assert service.enabled is True

    # Restore
    module.L9_GRAPH_WM_SYNC = original


# =============================================================================
# Test Integration with World Model Service
# =============================================================================


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_upsert_to_world_model_integration():
    """Test that _upsert_to_world_model calls WorldModelService correctly."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=True)

    entity = {
        "entity_type": "agent",
        "entity_id": "agent:L",
        "name": "L",
        "attributes": {"designation": "CTO"},
    }

    # Mock WorldModelService and RLS config
    mock_wm_service = AsyncMock()
    mock_wm_service.upsert_entity = AsyncMock()

    mock_wm_module = MagicMock()
    mock_wm_module.WorldModelService = MagicMock(return_value=mock_wm_service)

    # Mock RLS config module
    mock_rls_config = MagicMock()
    mock_rls_config.tenant_uuid = "test-tenant"
    mock_rls_config.org_uuid = "test-org"
    mock_rls_config.user_uuid = "test-user"

    mock_rls_module = MagicMock()
    mock_rls_module.get_rls_config = MagicMock(return_value=mock_rls_config)

    with patch.dict(
        "sys.modules",
        {
            "world_model.service": mock_wm_module,
            "config.rls_config": mock_rls_module,
        },
    ):
        await service._upsert_to_world_model(entity)

    # Verify upsert was called with correct parameters including RLS context
    mock_wm_service.upsert_entity.assert_called_once()
    call_kwargs = mock_wm_service.upsert_entity.call_args.kwargs
    assert call_kwargs["entity_type"] == "agent"
    assert call_kwargs["entity_id"] == "agent:L"
    assert call_kwargs["tenant_id"] == "test-tenant"


@pytest.mark.asyncio
@must_stay_async("callers use await")
async def test_upsert_handles_missing_wm_service():
    """Test graceful handling when WorldModelService not available."""
    from core.integration.graph_to_wm_sync import GraphToWorldModelSync

    service = GraphToWorldModelSync(neo4j_driver="mock", enabled=True)

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
