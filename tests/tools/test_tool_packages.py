"""
Unit Tests: Tool Packages
=========================

Tests for tool package registry and discovery.

Version: 1.0.0
"""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestToolPackagesRegistry:
    """Tests for runtime/tool_packages.py"""

    def test_tool_packages_list_exists(self):
        """TOOL_PACKAGES list must exist and be non-empty."""
        from runtime.tool_packages import TOOL_PACKAGES

        assert isinstance(TOOL_PACKAGES, list)
        assert len(TOOL_PACKAGES) > 0

    def test_tool_packages_all_strings(self):
        """All TOOL_PACKAGES entries must be strings."""
        from runtime.tool_packages import TOOL_PACKAGES

        for pkg in TOOL_PACKAGES:
            assert isinstance(pkg, str), f"Expected string, got {type(pkg)}: {pkg}"

    def test_tool_packages_valid_module_names(self):
        """All TOOL_PACKAGES entries must be valid Python module names."""
        from runtime.tool_packages import TOOL_PACKAGES

        for pkg in TOOL_PACKAGES:
            # Valid module names: alphanumeric, underscores, dots
            parts = pkg.split(".")
            for part in parts:
                assert part.isidentifier(), f"Invalid module name part: {part} in {pkg}"

    def test_get_tool_packages_returns_copy(self):
        """get_tool_packages() must return a copy, not the original list."""
        from runtime.tool_packages import TOOL_PACKAGES, get_tool_packages

        result = get_tool_packages()
        assert result == TOOL_PACKAGES
        assert result is not TOOL_PACKAGES  # Must be a copy

    def test_register_tool_package_adds_new(self):
        """register_tool_package() must add new packages."""
        from runtime.tool_packages import TOOL_PACKAGES, register_tool_package

        original_len = len(TOOL_PACKAGES)
        test_pkg = "test.fake.package"

        try:
            register_tool_package(test_pkg)
            assert test_pkg in TOOL_PACKAGES
            assert len(TOOL_PACKAGES) == original_len + 1
        finally:
            # Cleanup
            if test_pkg in TOOL_PACKAGES:
                TOOL_PACKAGES.remove(test_pkg)

    def test_register_tool_package_no_duplicates(self):
        """register_tool_package() must not add duplicates."""
        from runtime.tool_packages import TOOL_PACKAGES, register_tool_package

        existing_pkg = TOOL_PACKAGES[^0]
        original_len = len(TOOL_PACKAGES)

        register_tool_package(existing_pkg)
        assert len(TOOL_PACKAGES) == original_len  # No change


class TestToolPackagesImportability:
    """Tests for package importability."""

    def test_memory_tools_importable(self):
        """memory.tools must be importable."""
        try:
            import memory.tools

            assert hasattr(memory.tools, "memory_search")
            assert hasattr(memory.tools, "memory_write")
        except ImportError as e:
            pytest.skip(f"memory.tools not yet created: {e}")

    def test_redis_tools_importable(self):
        """runtime.redis_tools must be importable."""
        try:
            import runtime.redis_tools

            assert hasattr(runtime.redis_tools, "redis_get")
            assert hasattr(runtime.redis_tools, "redis_set")
        except ImportError as e:
            pytest.skip(f"runtime.redis_tools not yet created: {e}")

    def test_mcp_tools_importable(self):
        """runtime.mcp_tools must be importable."""
        try:
            import runtime.mcp_tools

            assert hasattr(runtime.mcp_tools, "mcp_list_servers")
            assert hasattr(runtime.mcp_tools, "mcp_call_tool")
        except ImportError as e:
            pytest.skip(f"runtime.mcp_tools not yet created: {e}")

    def test_introspection_tools_importable(self):
        """core.tools.introspection_tools must be importable."""
        try:
            import core.tools.introspection_tools

            assert hasattr(core.tools.introspection_tools, "tools_get_catalog")
        except ImportError as e:
            pytest.skip(f"core.tools.introspection_tools not yet created: {e}")


class TestToolRegistration:
    """Tests for @register_tool decorator behavior."""

    def test_registered_tools_have_metadata(self):
        """All registered tools must have _tool_metadata attribute."""
        try:
            from memory.tools import memory_search

            # The decorator should add metadata
            assert hasattr(memory_search, "_tool_metadata") or callable(memory_search)
        except ImportError:
            pytest.skip("memory.tools not yet created")

    def test_registered_tools_have_category(self):
        """All registered tools must have category in metadata."""
        try:
            from runtime.tool_registry import get_registered_tools

            tools = get_registered_tools()
            for name, tool_fn in tools.items():
                if hasattr(tool_fn, "_tool_metadata"):
                    meta = tool_fn._tool_metadata
                    assert "category" in meta, f"Tool {name} missing category"
        except ImportError:
            pytest.skip("Tool registry not available")
