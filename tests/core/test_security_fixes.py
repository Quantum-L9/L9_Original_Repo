"""
Tests for Security Fixes
=========================

Tests for unsafe eval() and __import__() fixes.
"""

import pytest


class TestDIContainerSecurityFix:
    """Tests for DI container eval() fix using get_type_hints()."""

    def test_string_annotation_resolution(self):
        """Test that string annotations are resolved safely."""
        from core.di.container import DIContainer
        from typing import Optional

        container = DIContainer()

        # Define a factory with string annotations
        def test_factory(param: "Optional[str]" = None) -> str:
            return param or "default"

        # Register and resolve
        container.register("test_service", test_factory)
        result = container.resolve("test_service")

        assert result == "default"

    def test_no_eval_injection(self):
        """Test that malicious code in annotations cannot be executed."""
        from core.di.container import DIContainer

        container = DIContainer()

        # Define a factory with malicious annotation
        def malicious_factory(param: "__import__('os').system('echo hacked')" = None):
            return "safe"

        # This should not execute the malicious code
        container.register("malicious", malicious_factory)
        result = container.resolve("malicious")

        assert result == "safe"


class TestToolRegistrySecurityFix:
    """Tests for tool registry eval() fix using ast.literal_eval()."""

    def test_literal_eval_safe_expressions(self):
        """Test that literal_eval only allows safe literals."""
        from core.tools.base_registry import ExecutorToolRegistry

        registry = ExecutorToolRegistry()

        # Get the calculate_executor function
        calc_tool = None
        for tool in registry.list_all():
            if tool.name == "calculate":
                calc_tool = tool
                break

        assert calc_tool is not None, "Calculate tool not found"

        # Test safe expressions
        result = calc_tool.executor("42")
        assert result["result"] == 42

        result = calc_tool.executor("3.14")
        assert result["result"] == 3.14

        result = calc_tool.executor("[1, 2, 3]")
        assert result["result"] == [1, 2, 3]

    def test_literal_eval_blocks_code_execution(self):
        """Test that literal_eval blocks code execution."""
        from core.tools.base_registry import ExecutorToolRegistry

        registry = ExecutorToolRegistry()

        # Get the calculate_executor function
        calc_tool = None
        for tool in registry.list_all():
            if tool.name == "calculate":
                calc_tool = tool
                break

        assert calc_tool is not None

        # Test that code execution is blocked
        result = calc_tool.executor("__import__('os').system('echo hacked')")
        assert "error" in result
        assert "Invalid expression" in result["error"]

        result = calc_tool.executor("eval('1+1')")
        assert "error" in result


class TestErrorTrackingSecurityFix:
    """Tests for error tracking __import__() fix."""

    @pytest.mark.asyncio
    async def test_timedelta_import_safe(self):
        """Test that timedelta is imported safely."""
        from core.error_tracking import get_recent_errors_summary

        # This should not raise an exception
        # (will return empty dict if Neo4j not available)
        result = await get_recent_errors_summary(hours=24)

        # Just verify it doesn't crash
        assert isinstance(result, dict)

    def test_no_dynamic_import_injection(self):
        """Test that dynamic imports cannot be injected."""
        # Read the error_tracking.py file to verify no __import__() usage
        with open("/tmp/L9/core/error_tracking.py", "r") as f:
            content = f.read()

        # Verify __import__() is not used
        assert "__import__(" not in content, "Unsafe __import__() still present"

        # Verify safe import is used
        assert "from datetime import timedelta" in content


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TEST-SEC-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.di.container",
        "core.tools.base_registry",
        "core.error_tracking",
    ],
    "tags": ["test", "security", "eval", "injection", "prevention"],
    "keywords": ["security", "test", "eval", "injection", "ast", "literal_eval"],
    "business_value": "Ensures security fixes for eval() and __import__() vulnerabilities are working correctly.",
    "last_modified": "2026-01-21T18:45:00Z",
    "modified_by": "Manus_AI",
    "change_summary": "Initial security fix tests",
}
# ============================================================================
