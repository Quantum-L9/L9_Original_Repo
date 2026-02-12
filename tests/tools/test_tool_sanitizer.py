"""
Unit Tests – Tool Input Sanitizer
===================================

Tests for core/tools/sanitizer.py.

Covers:
- ToolInputSanitizer.sanitize(): schema validation, type coercion
- Resource limits: max_total_bytes, max_depth, max_list_length, max_string_length
- Path traversal blocking
- Unknown key rejection with schema
- Internal context keys bypass
- ToolInputSanitizationError attributes

Version: 1.0.0
"""

from __future__ import annotations

import pytest

from core.tools.sanitizer import (
    ToolInputSanitizationError,
    ToolInputSanitizer,
    ToolInputSanitizerConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sanitizer() -> ToolInputSanitizer:
    """Default sanitizer with production defaults."""
    return ToolInputSanitizer()


@pytest.fixture
def strict_sanitizer() -> ToolInputSanitizer:
    """Sanitizer with tight limits for boundary testing."""
    config = ToolInputSanitizerConfig(
        max_total_bytes=256,
        max_depth=3,
        max_list_length=5,
        max_string_length=64,
    )
    return ToolInputSanitizer(config)


@pytest.fixture
def sample_schema() -> dict:
    """A realistic tool input schema."""
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "score": {"type": "number"},
            "verbose": {"type": "boolean"},
            "tags": {"type": "array"},
            "options": {"type": "object"},
            "filepath": {"type": "string"},
        },
        "required": ["query"],
    }


# ---------------------------------------------------------------------------
# Basic Validation
# ---------------------------------------------------------------------------


class TestBasicValidation:
    """Tests for fundamental sanitization behavior."""

    def test_non_dict_arguments_rejected(self, sanitizer: ToolInputSanitizer) -> None:
        with pytest.raises(ToolInputSanitizationError, match="must be an object"):
            sanitizer.sanitize("tool_a", "not a dict")

    def test_list_arguments_rejected(self, sanitizer: ToolInputSanitizer) -> None:
        with pytest.raises(ToolInputSanitizationError, match="must be an object"):
            sanitizer.sanitize("tool_b", [1, 2, 3])

    def test_none_arguments_rejected(self, sanitizer: ToolInputSanitizer) -> None:
        with pytest.raises(ToolInputSanitizationError, match="must be an object"):
            sanitizer.sanitize("tool_c", None)

    def test_empty_dict_passes_without_schema(
        self, sanitizer: ToolInputSanitizer
    ) -> None:
        result = sanitizer.sanitize("tool_d", {})
        assert result == {}

    def test_valid_input_passes(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "search",
            {"query": "find documents", "limit": 10},
            schema=sample_schema,
        )
        assert result["query"] == "find documents"
        assert result["limit"] == 10


# ---------------------------------------------------------------------------
# Required Fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    """Tests for schema-required field enforcement."""

    def test_missing_required_field_raises(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="missing required fields"):
            sanitizer.sanitize("search", {"limit": 5}, schema=sample_schema)

    def test_all_required_fields_present_passes(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize("search", {"query": "hello"}, schema=sample_schema)
        assert result["query"] == "hello"


# ---------------------------------------------------------------------------
# Unknown Key Rejection
# ---------------------------------------------------------------------------


class TestUnknownKeyRejection:
    """Tests for rejecting keys not in schema properties."""

    def test_unknown_key_rejected_with_schema(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="unknown field"):
            sanitizer.sanitize(
                "search",
                {"query": "test", "evil_key": "hack"},
                schema=sample_schema,
            )

    def test_unknown_key_allowed_without_schema(
        self, sanitizer: ToolInputSanitizer
    ) -> None:
        result = sanitizer.sanitize("search", {"any_key": "any_value"})
        assert result["any_key"] == "any_value"

    def test_internal_context_keys_bypass_rejection(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "search",
            {"query": "test", "agent_id": "a1", "task_id": "t1"},
            schema=sample_schema,
        )
        assert result["agent_id"] == "a1"
        assert result["task_id"] == "t1"


# ---------------------------------------------------------------------------
# Type Coercion
# ---------------------------------------------------------------------------


class TestTypeCoercion:
    """Tests for deterministic primitive type coercion."""

    def test_int_to_string_coercion(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize("tool", {"query": 42}, schema=sample_schema)
        assert result["query"] == "42"

    def test_string_to_integer_coercion(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "tool", {"query": "test", "limit": "10"}, schema=sample_schema
        )
        assert result["limit"] == 10

    def test_string_to_number_coercion(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "tool", {"query": "test", "score": "3.14"}, schema=sample_schema
        )
        assert result["score"] == pytest.approx(3.14)

    def test_string_to_boolean_coercion_true(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        for truthy in ("true", "1", "yes", "True", "YES"):
            result = sanitizer.sanitize(
                "tool", {"query": "test", "verbose": truthy}, schema=sample_schema
            )
            assert result["verbose"] is True

    def test_string_to_boolean_coercion_false(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        for falsy in ("false", "0", "no", "False", "NO"):
            result = sanitizer.sanitize(
                "tool", {"query": "test", "verbose": falsy}, schema=sample_schema
            )
            assert result["verbose"] is False

    def test_bool_rejected_for_integer_field(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(
            ToolInputSanitizationError, match="expected integer, got bool"
        ):
            sanitizer.sanitize(
                "tool", {"query": "test", "limit": True}, schema=sample_schema
            )

    def test_bool_rejected_for_number_field(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(
            ToolInputSanitizationError, match="expected number, got bool"
        ):
            sanitizer.sanitize(
                "tool", {"query": "test", "score": False}, schema=sample_schema
            )

    def test_string_strip_on_string_type(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "tool", {"query": "  spaces  "}, schema=sample_schema
        )
        assert result["query"] == "spaces"

    def test_null_value_allowed(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "tool", {"query": "test", "limit": None}, schema=sample_schema
        )
        assert result["limit"] is None


# ---------------------------------------------------------------------------
# Path Traversal Detection
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """Tests for blocking directory traversal in path-like keys."""

    def test_unix_traversal_blocked(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="path traversal"):
            sanitizer.sanitize(
                "tool",
                {"query": "test", "filepath": "../../../etc/passwd"},
                schema=sample_schema,
            )

    def test_windows_traversal_blocked(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="path traversal"):
            sanitizer.sanitize(
                "tool",
                {"query": "test", "filepath": "..\\..\\system32"},
                schema=sample_schema,
            )

    def test_null_byte_blocked(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="null byte"):
            sanitizer.sanitize(
                "tool",
                {"query": "test", "filepath": "file.txt\x00.sh"},
                schema=sample_schema,
            )

    def test_safe_path_allowed(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        result = sanitizer.sanitize(
            "tool",
            {"query": "test", "filepath": "data/reports/2026/q1.csv"},
            schema=sample_schema,
        )
        assert result["filepath"] == "data/reports/2026/q1.csv"

    def test_non_path_keys_skip_traversal_check(
        self, sanitizer: ToolInputSanitizer, sample_schema: dict
    ) -> None:
        """Keys that don't match path patterns should not be path-checked."""
        result = sanitizer.sanitize(
            "tool",
            {"query": "../../../not_a_path_key"},
            schema=sample_schema,
        )
        assert "../../../not_a_path_key" in result["query"]


# ---------------------------------------------------------------------------
# Resource Limits
# ---------------------------------------------------------------------------


class TestResourceLimits:
    """Tests for size, depth, and length enforcement."""

    def test_max_depth_exceeded(self, strict_sanitizer: ToolInputSanitizer) -> None:
        deep = {"a": {"b": {"c": {"d": {"e": "too deep"}}}}}
        with pytest.raises(ToolInputSanitizationError, match="max_depth"):
            strict_sanitizer.sanitize("tool", deep)

    def test_max_list_length_exceeded(
        self, strict_sanitizer: ToolInputSanitizer
    ) -> None:
        # 10 items exceeds max_list_length=5 but stays under max_total_bytes=256
        with pytest.raises(ToolInputSanitizationError, match="max_list_length"):
            strict_sanitizer.sanitize("tool", {"items": list(range(10))})

    def test_max_string_length_exceeded(
        self, strict_sanitizer: ToolInputSanitizer
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="max_string_length"):
            strict_sanitizer.sanitize("tool", {"text": "x" * 200})

    def test_max_total_bytes_exceeded(
        self, strict_sanitizer: ToolInputSanitizer
    ) -> None:
        with pytest.raises(ToolInputSanitizationError, match="max_total_bytes"):
            strict_sanitizer.sanitize("tool", {"data": "y" * 250})

    def test_within_limits_passes(self, strict_sanitizer: ToolInputSanitizer) -> None:
        result = strict_sanitizer.sanitize("tool", {"key": "small"})
        assert result["key"] == "small"


# ---------------------------------------------------------------------------
# Error Attributes
# ---------------------------------------------------------------------------


class TestErrorAttributes:
    """Tests for ToolInputSanitizationError detail fields."""

    def test_error_has_tool_id(self, sanitizer: ToolInputSanitizer) -> None:
        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("my_tool", "bad input")
        assert exc_info.value.tool_id == "my_tool"

    def test_error_has_reasons_list(self, sanitizer: ToolInputSanitizer) -> None:
        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("my_tool", 12345)
        assert isinstance(exc_info.value.reasons, list)
        assert len(exc_info.value.reasons) > 0
