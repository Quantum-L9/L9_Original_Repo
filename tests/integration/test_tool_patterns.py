"""
Integration Tests for Tool Pattern Extraction
==============================================

Tests for the ToolPatternExtractor service (UKG Phase 4).

Verifies:
- Pattern extraction from audit data
- Scheduled job starts and stops
- Pattern storage in World Model
- Top tools and problematic tools identification

Version: 1.0.0
Created: 2026-01-05
GMP: GMP-UKG-4 (Tool Pattern Extraction)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Test ToolPatternExtractor Class
# =============================================================================


def test_extractor_import():
    """Test that extractor can be imported."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    assert ToolPatternExtractor is not None


def test_extractor_defaults():
    """Test default configuration."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor()

    assert extractor.interval_hours == 6
    assert extractor.lookback_hours == 24
    assert extractor._running is False
    assert extractor._extraction_count == 0


def test_extractor_custom_config():
    """Test custom configuration."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(
        interval_hours=12,
        lookback_hours=48,
    )

    assert extractor.interval_hours == 12
    assert extractor.lookback_hours == 48


def test_extractor_enabled_override():
    """Test enabled flag override."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    # Force enabled
    extractor = ToolPatternExtractor(enabled=True)
    assert extractor.enabled is True

    # Force disabled
    extractor = ToolPatternExtractor(enabled=False)
    assert extractor.enabled is False


# =============================================================================
# Test Pattern Extraction Logic
# =============================================================================


def test_extract_patterns_empty_data():
    """Test pattern extraction with no data."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor()
    patterns = extractor._extract_patterns([])

    assert patterns["total_invocations"] == 0
    assert patterns["success_rate"] == 0.0
    assert patterns["tool_stats"] == {}


def test_extract_patterns_with_data():
    """Test pattern extraction with sample audit data."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor()

    audit_data = [
        {
            "tool_name": "memory_read",
            "success": True,
            "duration_ms": 50,
            "cost_usd": 0.0,
        },
        {
            "tool_name": "memory_read",
            "success": True,
            "duration_ms": 60,
            "cost_usd": 0.0,
        },
        {
            "tool_name": "web_search",
            "success": True,
            "duration_ms": 1200,
            "cost_usd": 0.005,
        },  # $0.005 per search
        {
            "tool_name": "web_search",
            "success": False,
            "duration_ms": 500,
            "cost_usd": 0.002,
        },
        {
            "tool_name": "llm_chat",
            "success": True,
            "duration_ms": 800,
            "cost_usd": 0.01,
        },  # $0.01 per chat
    ]

    patterns = extractor._extract_patterns(audit_data)

    assert patterns["total_invocations"] == 5
    assert patterns["success_rate"] == 0.8  # 4/5
    assert "memory_read" in patterns["tool_stats"]
    assert "web_search" in patterns["tool_stats"]
    assert "llm_chat" in patterns["tool_stats"]

    # Check memory_read stats
    mr_stats = patterns["tool_stats"]["memory_read"]
    assert mr_stats["invocations"] == 2
    assert mr_stats["successes"] == 2
    assert mr_stats["success_rate"] == 1.0

    # Check web_search stats
    ws_stats = patterns["tool_stats"]["web_search"]
    assert ws_stats["invocations"] == 2
    assert ws_stats["failures"] == 1
    assert ws_stats["success_rate"] == 0.5


def test_get_top_tools():
    """Test top tools identification."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor()

    tool_stats = {
        "tool_a": {"invocations": 100, "success_rate": 0.95},
        "tool_b": {"invocations": 50, "success_rate": 0.90},
        "tool_c": {"invocations": 200, "success_rate": 0.99},
        "tool_d": {"invocations": 10, "success_rate": 0.80},
    }

    top_tools = extractor._get_top_tools(tool_stats, limit=3)

    assert len(top_tools) == 3
    assert top_tools[0]["name"] == "tool_c"  # Most invocations
    assert top_tools[1]["name"] == "tool_a"
    assert top_tools[2]["name"] == "tool_b"


def test_get_problematic_tools():
    """Test problematic tools identification."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor()

    tool_stats = {
        "good_tool": {"invocations": 100, "success_rate": 0.95},
        "bad_tool": {"invocations": 50, "success_rate": 0.50},  # 50% failure
        "okay_tool": {"invocations": 30, "success_rate": 0.85},  # 15% failure
        "few_calls": {"invocations": 3, "success_rate": 0.33},  # Not enough data
    }

    problematic = extractor._get_problematic_tools(tool_stats, error_threshold=0.2)

    assert len(problematic) == 1
    assert problematic[0]["name"] == "bad_tool"
    assert problematic[0]["failure_rate"] == 0.5


# =============================================================================
# Test Start/Stop
# =============================================================================


@pytest.mark.asyncio
async def test_start_when_disabled():
    """Test that start does nothing when disabled."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=False)
    await extractor.start()

    assert extractor._running is False
    assert extractor._task is None


@pytest.mark.asyncio
async def test_stop_when_not_running():
    """Test that stop handles not-running gracefully."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=False)
    await extractor.stop()  # Should not raise

    assert extractor._running is False


# =============================================================================
# Test run_extraction
# =============================================================================


@pytest.mark.asyncio
async def test_run_extraction_when_disabled():
    """Test run_extraction returns DISABLED when service disabled."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=False)
    result = await extractor.run_extraction()

    assert result["status"] == "DISABLED"


@pytest.mark.asyncio
async def test_run_extraction_no_data():
    """Test run_extraction with no audit data."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=True)

    with patch.object(extractor, "_query_audit_data", return_value=[]):
        result = await extractor.run_extraction()

    assert result["status"] == "NO_DATA"


@pytest.mark.asyncio
async def test_run_extraction_success():
    """Test successful run_extraction."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=True)

    mock_data = [
        {"tool_name": "test_tool", "success": True, "duration_ms": 100, "cost_usd": 1},
    ]

    with patch.object(extractor, "_query_audit_data", return_value=mock_data):
        with patch.object(extractor, "_store_patterns", return_value=None):
            result = await extractor.run_extraction()

    assert result["status"] == "SUCCESS"
    assert "extracted_at" in result
    assert extractor._extraction_count == 1


# =============================================================================
# Test Status
# =============================================================================


def test_get_status():
    """Test status reporting."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(
        enabled=True,
        interval_hours=12,
        lookback_hours=48,
    )

    status = extractor.get_status()

    assert status["enabled"] is True
    assert status["running"] is False
    assert status["extraction_count"] == 0
    assert status["last_extraction"] is None
    assert status["interval_hours"] == 12
    assert status["lookback_hours"] == 48


# =============================================================================
# Test Global Instance
# =============================================================================


def test_get_tool_pattern_extractor():
    """Test getting global instance."""
    # Clear any existing instance
    import core.integration.tool_pattern_extractor as module
    from core.integration.tool_pattern_extractor import (
        ToolPatternExtractor,
        get_tool_pattern_extractor,
    )

    module._extractor = None

    extractor = get_tool_pattern_extractor()

    assert isinstance(extractor, ToolPatternExtractor)

    # Second call returns same instance
    extractor2 = get_tool_pattern_extractor()
    assert extractor is extractor2

    # Cleanup
    module._extractor = None


# =============================================================================
# Test Integration with World Model
# =============================================================================


@pytest.mark.asyncio
async def test_store_patterns_integration():
    """Test that _store_patterns calls WorldModelService correctly."""
    from core.integration.tool_pattern_extractor import ToolPatternExtractor

    extractor = ToolPatternExtractor(enabled=True)

    patterns = {
        "tool_stats": {"test_tool": {"invocations": 5, "success_rate": 1.0}},
        "total_invocations": 5,
        "success_rate": 1.0,
        "avg_duration_ms": 100,
        "total_cost_usd": 5,
        "lookback_hours": 24,
        "extracted_at": "2026-01-05T12:00:00",
    }

    mock_wm_service = AsyncMock()
    mock_wm_service.upsert_entity = AsyncMock()

    mock_wm_module = MagicMock()
    mock_wm_module.WorldModelService = MagicMock(return_value=mock_wm_service)

    with patch.dict("sys.modules", {"world_model.service": mock_wm_module}):
        await extractor._store_patterns(patterns)

    mock_wm_service.upsert_entity.assert_called_once()
    call_kwargs = mock_wm_service.upsert_entity.call_args.kwargs

    assert call_kwargs["entity_type"] == "agent_insight"
    assert call_kwargs["entity_id"] == "agent:L:tool_patterns"
    assert call_kwargs["name"] == "L Tool Patterns"
    assert "total_invocations" in call_kwargs["attributes"]
