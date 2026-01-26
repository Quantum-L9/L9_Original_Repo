"""
Integration Tests: Tool Discovery
=================================

Tests for end-to-end tool discovery and registration.

Version: 1.0.0
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest


class TestToolDiscoveryIntegration:
    """Integration tests for tool discovery system."""

    def test_all_tool_packages_importable(self):
        """All packages in TOOL_PACKAGES must be importable."""
        from runtime.tool_packages import TOOL_PACKAGES

        failed = []
        for pkg in TOOL_PACKAGES:
            try:
                importlib.import_module(pkg)
            except ImportError as e:
                failed.append({"package": pkg, "error": str(e)})

        if failed:
            pytest.fail(f"Failed to import packages: {failed}")

    def test_no_duplicate_tool_names_across_packages(self):
        """No duplicate tool names across all packages."""
        from runtime.tool_packages import TOOL_PACKAGES

        tool_names: dict[str, str] = {}  # name -> first package
        duplicates = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)

                for name in dir(module):
                    obj = getattr(module, name)
                    if callable(obj) and hasattr(obj, "_tool_metadata"):
                        tool_name = obj._tool_metadata.get("name", name)

                        if tool_name in tool_names:
                            duplicates.append(
                                {
                                    "name": tool_name,
                                    "packages": [tool_names[tool_name], pkg],
                                }
                            )
                        else:
                            tool_names[tool_name] = pkg
            except ImportError:
                continue  # Skip unavailable packages

        if duplicates:
            pytest.fail(f"Duplicate tool names found: {duplicates}")

    def test_all_tools_have_required_metadata(self):
        """All registered tools must have category and description."""
        from runtime.tool_packages import TOOL_PACKAGES

        incomplete = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)

                for name in dir(module):
                    obj = getattr(module, name)
                    if callable(obj) and hasattr(obj, "_tool_metadata"):
                        meta = obj._tool_metadata
                        missing = []

                        if "category" not in meta:
                            missing.append("category")
                        if "description" not in meta:
                            missing.append("description")

                        if missing:
                            incomplete.append(
                                {
                                    "package": pkg,
                                    "tool": name,
                                    "missing": missing,
                                }
                            )
            except ImportError:
                continue

        if incomplete:
            pytest.fail(f"Tools with incomplete metadata: {incomplete}")

    def test_tool_count_matches_expected(self):
        """Total tool count should match expected."""
        from runtime.tool_packages import TOOL_PACKAGES

        expected_min = 60  # Minimum expected tools after migration
        total = 0

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)

                for name in dir(module):
                    obj = getattr(module, name)
                    if callable(obj) and hasattr(obj, "_tool_metadata"):
                        total += 1
            except ImportError:
                continue

        assert total >= expected_min, (
            f"Expected at least {expected_min} tools, found {total}"
        )


class TestToolRegistryIntegration:
    """Integration tests for tool registry."""

    @pytest.mark.asyncio
    async def test_tools_discoverable_via_executor(self):
        """Tools should be discoverable via tool executor."""
        try:
            from runtime.tool_executor import get_tool_executor

            executor = get_tool_executor()
            tools = executor.list_tools()

            assert len(tools) > 0, "No tools discovered"

            # Check for key tools
            tool_names = [t.name for t in tools]
            assert "memory_search" in tool_names
            assert "redis_get" in tool_names
        except ImportError:
            pytest.skip("Tool executor not available")

    @pytest.mark.asyncio
    async def test_tool_execution_returns_dict(self):
        """All tool executions should return dict."""
        try:
            from runtime.tool_executor import get_tool_executor

            executor = get_tool_executor()

            # Test a read-only tool
            result = await executor.execute("memory_health_check", {})

            assert isinstance(result, dict)
            assert "status" in result
        except ImportError:
            pytest.skip("Tool executor not available")


class TestForbiddenImports:
    """Tests for forbidden import patterns."""

    def test_no_imports_from_l_tools(self):
        """No module should import from runtime.l_tools."""
        import ast
        from pathlib import Path

        root = Path(__file__).parent.parent.parent
        violations = []

        for py_file in root.rglob("*.py"):
            if "l_tools.py" in str(py_file):
                continue
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                if (
                    "from runtime.l_tools" in content
                    or "import runtime.l_tools" in content
                ):
                    violations.append(str(py_file.relative_to(root)))
            except Exception:
                continue

        if violations:
            pytest.fail(f"Files importing from runtime.l_tools: {violations}")
