"""
E2E Tests: Full Tool Wiring Pipeline
=====================================

Comprehensive end-to-end tests that validate the ENTIRE tool
wiring chain from decorator → registry → discovery → execution.

This is the single test file that proves the GMP-TS-META
deployment works correctly.

Test Layers:
1. Static Analysis — file-level checks without imports
2. Registration — decorator wiring verification
3. Discovery — tool_packages → discover_from_packages chain
4. Execution — mock-execute tools end-to-end
5. Invariants — system-wide constraints

Version: 1.0.0
"""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.decorators import must_stay_async

# Project root for file-system scans
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# LAYER 1: STATIC ANALYSIS
# ============================================================================


class TestStaticWiring:
    """File-level checks — no runtime imports needed."""

    def test_tool_search_meta_file_exists(self):
        """runtime/tool_search_meta.py must exist."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        assert path.exists(), f"Missing file: {path}"

    def test_dynamic_tool_binding_file_exists(self):
        """core/agents/dynamic_tool_binding.py must exist."""
        path = PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py"
        assert path.exists(), f"Missing file: {path}"

    def test_tool_search_meta_syntax_valid(self):
        """tool_search_meta.py must parse without syntax errors."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in tool_search_meta.py: {e}")

    def test_dynamic_tool_binding_syntax_valid(self):
        """dynamic_tool_binding.py must parse without syntax errors."""
        path = PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py"
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in dynamic_tool_binding.py: {e}")

    def test_tool_search_meta_imports_register_tool(self):
        """tool_search_meta.py must import register_tool."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        source = path.read_text(encoding="utf-8")
        assert "register_tool" in source, (
            "tool_search_meta.py does not import register_tool"
        )

    def test_tool_search_meta_imports_must_stay_async(self):
        """tool_search_meta.py must import must_stay_async."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        source = path.read_text(encoding="utf-8")
        assert "must_stay_async" in source, (
            "tool_search_meta.py does not import must_stay_async"
        )

    def test_tool_search_meta_imports_discover(self):
        """tool_search_meta.py must import discover_tools_for_task."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        source = path.read_text(encoding="utf-8")
        assert "discover_tools_for_task" in source, (
            "tool_search_meta.py does not import discover_tools_for_task"
        )

    def test_no_print_logger_in_new_files(self):
        """New files must not use PrintLogger or standard logging (ADR-0019)."""
        new_files = [
            PROJECT_ROOT / "runtime" / "tool_search_meta.py",
            PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py",
        ]
        violations = []
        for path in new_files:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            if "PrintLogger" in source:
                violations.append(f"{path}: uses PrintLogger")
            if "import logging" in source and "structlog" not in source:
                violations.append(f"{path}: uses stdlib logging without structlog")
        assert not violations, "ADR-0019 violations (structlog only):\n" + "\n".join(
            violations
        )


# ============================================================================
# LAYER 2: REGISTRATION CHAIN
# ============================================================================


class TestRegistrationChain:
    """Verify decorator → registry → TOOL_PACKAGES chain."""

    def test_all_tool_packages_importable(self):
        """Every entry in TOOL_PACKAGES must be importable."""
        from runtime.tool_packages import TOOL_PACKAGES

        failed = []
        for pkg in TOOL_PACKAGES:
            try:
                importlib.import_module(pkg)
            except ImportError as e:
                failed.append(f"{pkg}: {e}")
        assert not failed, "TOOL_PACKAGES import failures:\n" + "\n".join(failed)

    def test_no_duplicate_tool_names(self):
        """No two packages may register a tool with the same name."""
        from runtime.tool_packages import TOOL_PACKAGES

        seen: dict[str, str] = {}
        duplicates = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
            except ImportError:
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and hasattr(obj, "_tool_metadata"):
                    tool_name = obj._tool_metadata.get("name", attr_name)
                    if tool_name in seen:
                        duplicates.append(
                            f"'{tool_name}' in both {seen[tool_name]} and {pkg}"
                        )
                    else:
                        seen[tool_name] = pkg

        assert not duplicates, "Duplicate tool names across packages:\n" + "\n".join(
            duplicates
        )

    def test_all_registered_tools_have_category(self):
        """Every @register_tool function must have a category."""
        from runtime.tool_packages import TOOL_PACKAGES

        missing_category = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
            except ImportError:
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and hasattr(obj, "_tool_metadata"):
                    meta = obj._tool_metadata
                    if "category" not in meta or not meta["category"]:
                        missing_category.append(f"{pkg}::{attr_name} has no category")

        assert not missing_category, "Tools missing category:\n" + "\n".join(
            missing_category
        )

    def test_all_registered_tools_have_description(self):
        """Every @register_tool function must have a non-empty description."""
        from runtime.tool_packages import TOOL_PACKAGES

        missing_desc = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
            except ImportError:
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and hasattr(obj, "_tool_metadata"):
                    meta = obj._tool_metadata
                    desc = meta.get("description", "")
                    if not desc or len(desc) < 10:
                        missing_desc.append(
                            f"{pkg}::{attr_name} — description too short: '{desc}'"
                        )

        assert not missing_desc, "Tools with inadequate descriptions:\n" + "\n".join(
            missing_desc
        )

    def test_all_registered_tools_are_async(self):
        """Every registered tool function must be async."""
        from runtime.tool_packages import TOOL_PACKAGES

        sync_tools = []

        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
            except ImportError:
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and hasattr(obj, "_tool_metadata"):
                    if not inspect.iscoroutinefunction(obj):
                        sync_tools.append(f"{pkg}::{attr_name}")

        assert not sync_tools, "Sync tools found (must be async):\n" + "\n".join(
            sync_tools
        )


# ============================================================================
# LAYER 3: DISCOVERY PIPELINE
# ============================================================================


class TestDiscoveryPipeline:
    """Verify discover_from_packages() → tool availability."""

    def test_discover_from_packages_returns_int(self):
        """discover_from_packages() must return integer count."""
        from runtime.tool_packages import discover_from_packages

        result = discover_from_packages()
        assert isinstance(result, int), f"Expected int, got {type(result)}"

    def test_tool_count_minimum_threshold(self):
        """Total discovered tools must meet minimum threshold."""
        from runtime.tool_packages import TOOL_PACKAGES

        total = 0
        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if callable(obj) and hasattr(obj, "_tool_metadata"):
                        total += 1
            except ImportError:
                continue

        # After GMP-TS-META: at minimum we have research(4) + reflection(5)
        # + mcp(7) + tool_search(1) = 17
        assert total >= 10, f"Expected at least 10 discoverable tools, found {total}"

    def test_tool_search_discoverable_via_packages(self):
        """tool_search must be discoverable through TOOL_PACKAGES."""
        from runtime.tool_packages import TOOL_PACKAGES

        found = False
        for pkg in TOOL_PACKAGES:
            try:
                module = importlib.import_module(pkg)
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if (
                        callable(obj)
                        and hasattr(obj, "_tool_metadata")
                        and obj._tool_metadata.get("name") == "tool_search"
                    ):
                        found = True
                        break
            except ImportError:
                continue
            if found:
                break

        assert found, (
            "tool_search not discoverable via TOOL_PACKAGES — "
            "check runtime.tool_search_meta is in TOOL_PACKAGES"
        )


# ============================================================================
# LAYER 4: EXECUTION PIPELINE (MOCKED)
# ============================================================================


class TestExecutionPipeline:
    """Verify tools can be invoked through the execution chain."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_tool_search_e2e_with_mock(self):
        """Full E2E: call tool_search → get tool definitions back."""
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "memory_search",
                    "description": "Search memory",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        # Patch where the function is USED (imported into), not where defined
        with patch(
            "runtime.tool_search_meta.discover_tools_for_task",
            new_callable=AsyncMock,
            return_value=mock_tools,
        ):
            from runtime.tool_search_meta import tool_search

            result = await tool_search(query="I need to search memory")

            assert isinstance(result, dict)
            assert "tools" in result
            assert len(result["tools"]) >= 1
            assert result["tools"][0]["function"]["name"] == "memory_search"

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_tool_search_returns_openai_format(self):
        """Returned tools must be in OpenAI function-calling format."""
        mock_tools = [
            {
                "type": "function",
                "function": {
                    "name": "git_commit",
                    "description": "Commit code changes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                        },
                        "required": ["message"],
                    },
                },
            }
        ]

        with patch(
            "runtime.tool_search_meta.discover_tools_for_task",
            new_callable=AsyncMock,
            return_value=mock_tools,
        ):
            from runtime.tool_search_meta import tool_search

            result = await tool_search(query="commit code")
            tools = result.get("tools", [])

            for tool in tools:
                assert "type" in tool, "Tool missing 'type' field"
                assert tool["type"] == "function", (
                    f"Tool type must be 'function', got '{tool['type']}'"
                )
                assert "function" in tool, "Tool missing 'function' field"
                fn = tool["function"]
                assert "name" in fn, "Function missing 'name'"
                assert "description" in fn, "Function missing 'description'"
                assert "parameters" in fn, "Function missing 'parameters'"


# ============================================================================
# LAYER 5: SYSTEM INVARIANTS
# ============================================================================


class TestSystemInvariants:
    """Cross-cutting constraints that must always hold."""

    def test_no_circular_imports(self):
        """Importing tool_search_meta must not cause circular imports."""
        # Clear module cache for clean import
        modules_to_clear = [k for k in sys.modules if "tool_search_meta" in k]
        for k in modules_to_clear:
            del sys.modules[k]

        try:
            import runtime.tool_search_meta  # noqa: F401 — import test

            assert True  # If we get here, no circular import
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            raise

    def test_no_orphan_imports_in_tool_search(self):
        """All imports in tool_search_meta.py must resolve."""
        path = PROJECT_ROOT / "runtime" / "tool_search_meta.py"
        if not path.exists():
            pytest.skip("File not found")

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Try importing each top-level module
        failed = []
        for mod_name in imports:
            top_level = mod_name.split(".")[0]
            try:
                importlib.import_module(top_level)
            except ImportError as e:
                failed.append(f"{mod_name}: {e}")

        assert not failed, "Orphan imports in tool_search_meta.py:\n" + "\n".join(
            failed
        )

    def test_no_todos_in_new_files(self):
        """New files must not contain TODO/FIXME/HACK markers."""
        new_files = [
            PROJECT_ROOT / "runtime" / "tool_search_meta.py",
            PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py",
        ]
        violations = []
        forbidden = ["TODO", "FIXME", "HACK", "XXX"]

        for path in new_files:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                if marker in source:
                    violations.append(f"{path.name}: contains {marker}")

        assert not violations, "Forbidden markers in new files:\n" + "\n".join(
            violations
        )

    def test_structlog_only_in_new_files(self):
        """New files must use structlog, not stdlib logging (ADR-0019)."""
        new_files = [
            PROJECT_ROOT / "runtime" / "tool_search_meta.py",
            PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py",
        ]
        violations = []

        for path in new_files:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            lines = source.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("import logging") or (
                    stripped.startswith("from logging")
                ):
                    violations.append(f"{path.name}:{i}: {stripped}")

        assert not violations, (
            "ADR-0019 violations (must use structlog):\n" + "\n".join(violations)
        )

    def test_dora_meta_in_new_files(self):
        """New files should have __dora_meta__ blocks."""
        new_files = [
            PROJECT_ROOT / "runtime" / "tool_search_meta.py",
            PROJECT_ROOT / "core" / "agents" / "dynamic_tool_binding.py",
        ]
        missing = []

        for path in new_files:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            if "__dora_meta__" not in source:
                missing.append(path.name)

        assert not missing, f"Files missing __dora_meta__ block: {missing}"


# ============================================================================
# LAYER 6: TOOL PACKAGES BACKWARD COMPATIBILITY
# ============================================================================


class TestToolPackagesBackwardCompat:
    """Verify tool_packages.py replacement is backward compatible."""

    def test_public_api_unchanged(self):
        """All 4 public API functions must exist."""
        from runtime import tool_packages

        expected_api = [
            "TOOL_PACKAGES",
            "get_tool_packages",
            "register_tool_package",
            "discover_from_packages",
        ]
        for name in expected_api:
            assert hasattr(tool_packages, name), f"Public API member missing: {name}"

    def test_get_tool_packages_returns_list_copy(self):
        """get_tool_packages() must return a list that is a copy."""
        from runtime.tool_packages import TOOL_PACKAGES, get_tool_packages

        result = get_tool_packages()
        assert isinstance(result, list)
        assert result == TOOL_PACKAGES
        assert result is not TOOL_PACKAGES  # Must be a copy

    def test_register_tool_package_idempotent(self):
        """Registering same package twice must not create duplicates."""
        from runtime.tool_packages import TOOL_PACKAGES, register_tool_package

        test_pkg = "test.e2e.fake_package"
        original_len = len(TOOL_PACKAGES)

        try:
            register_tool_package(test_pkg)
            assert test_pkg in TOOL_PACKAGES

            # Second registration must be no-op
            register_tool_package(test_pkg)
            count = TOOL_PACKAGES.count(test_pkg)
            assert count == 1, f"Package registered {count} times"
        finally:
            if test_pkg in TOOL_PACKAGES:
                TOOL_PACKAGES.remove(test_pkg)

    def test_tool_packages_wired_in_runtime_init(self):
        """runtime/__init__.py must export tool_packages API."""
        import runtime

        expected = [
            "TOOL_PACKAGES",
            "get_tool_packages",
            "register_tool_package",
            "discover_from_packages",
        ]
        for name in expected:
            assert hasattr(runtime, name), f"runtime.__init__.py missing: {name}"

    def test_consumers_can_import(self):
        """Known consumers must be able to import TOOL_PACKAGES."""
        consumers = [
            "runtime.tool_packages",
        ]
        for consumer in consumers:
            try:
                mod = importlib.import_module(consumer)
                assert hasattr(mod, "TOOL_PACKAGES")
            except ImportError as e:
                pytest.fail(f"Consumer {consumer} cannot import: {e}")
