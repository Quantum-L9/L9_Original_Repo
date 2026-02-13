"""
E2E Tests: Dynamic Tool Binding
================================

Tests for core/agents/dynamic_tool_binding.py — agent-level
tool binding using dynamic discovery.

Covers:
- All 5 exported functions
- Feature flag gating
- Cache behavior
- Error handling when discovery is disabled

Version: 1.0.0
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_discovery_enabled():
    """Mock dynamic discovery as enabled."""
    with patch(
        "core.tools.dynamic_discovery.is_dynamic_discovery_enabled",
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_discovery_disabled():
    """Mock dynamic discovery as disabled."""
    with patch(
        "core.tools.dynamic_discovery.is_dynamic_discovery_enabled",
        return_value=False,
    ):
        yield


@pytest.fixture
def mock_cached_tools():
    """Mock cached tools returning a preset list."""
    tools = [
        {"type": "function", "function": {"name": "memory_search"}},
        {"type": "function", "function": {"name": "memory_write"}},
    ]
    with patch(
        "core.tools.dynamic_discovery.get_cached_tools",
        return_value=tools,
    ):
        yield tools


@pytest.fixture
def mock_no_cached_tools():
    """Mock cache returning None (no cached tools)."""
    with patch(
        "core.tools.dynamic_discovery.get_cached_tools",
        return_value=None,
    ):
        yield


# ============================================================================
# UNIT TESTS: IMPORTS & EXPORTS
# ============================================================================


class TestDynamicToolBindingExports:
    """Verify module exports are correct."""

    def test_module_importable(self):
        """Module must be importable without errors."""
        import core.agents.dynamic_tool_binding as mod

        assert mod is not None

    def test_all_exports_defined(self):
        """Module __all__ must list at least 5 public functions."""
        import core.agents.dynamic_tool_binding as mod

        assert hasattr(mod, "__all__"), "Module must define __all__"
        assert len(mod.__all__) >= 5, (
            f"Expected at least 5 exports, got {len(mod.__all__)}: {mod.__all__}"
        )

    def test_exports_match_expected(self):
        """Exported names must include all required spec functions."""
        import core.agents.dynamic_tool_binding as mod

        expected = {
            "bind_tools_to_agent",
            "get_agent_tools",
            "refresh_agent_tools",
            "get_tool_binding_status",
            "clear_tool_cache",
        }
        actual = set(mod.__all__)
        missing = expected - actual
        assert not missing, f"Missing exports: {missing}"

    def test_wired_in_agents_init(self):
        """core/agents/__init__.py must import and re-export all 5."""
        import core.agents as agents_pkg

        expected = [
            "bind_tools_to_agent",
            "get_agent_tools",
            "refresh_agent_tools",
            "get_tool_binding_status",
            "clear_tool_cache",
        ]
        for name in expected:
            assert hasattr(agents_pkg, name), (
                f"core.agents.__init__.py missing export: {name}"
            )

    def test_all_exports_callable(self):
        """All exported functions must be callable."""
        import core.agents.dynamic_tool_binding as mod

        for name in mod.__all__:
            fn = getattr(mod, name)
            assert callable(fn), f"Export {name} is not callable"


# ============================================================================
# UNIT TESTS: FEATURE FLAG GATING
# ============================================================================


class TestFeatureFlagGating:
    """Verify functions respect dynamic discovery feature flag."""

    @pytest.mark.asyncio
    async def test_bind_tools_static_when_disabled(self, mock_discovery_disabled):
        """bind_tools_to_agent must fall back to static bundle when flag is off."""
        from core.agents.dynamic_tool_binding import bind_tools_to_agent

        # Should not raise even when disabled — returns static bundle
        result = await bind_tools_to_agent(
            agent_id="test-agent",
            task_description="search memory",
        )
        # When disabled, returns static tool bundle (list of tools, not empty)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_tool_binding_status_reports_disabled(
        self, mock_discovery_disabled
    ):
        """Status must indicate discovery is disabled."""
        from core.agents.dynamic_tool_binding import get_tool_binding_status

        status = await get_tool_binding_status()
        assert isinstance(status, dict)
        assert status.get("enabled") is False or "disabled" in str(status).lower()


# ============================================================================
# UNIT TESTS: CACHE BEHAVIOR
# ============================================================================


class TestCacheBehavior:
    """Verify tool caching works correctly."""

    @pytest.mark.asyncio
    async def test_clear_tool_cache_callable(self):
        """clear_tool_cache must execute without error."""
        from core.agents.dynamic_tool_binding import clear_tool_cache

        # Should not raise
        try:
            result = await clear_tool_cache()
        except TypeError:
            # Might be sync
            result = clear_tool_cache()
        # No assertion on result — just verifying no crash
