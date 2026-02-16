"""
L9 Tool Input Sanitizer — Validation Ordering Tests
=====================================================

Regression tests for Bug 3: _enforce_resource_limits() checked depth
and string length before total bytes, masking the highest-severity
violation.

Reference: L9 Bug Postmortem — 5 Root Causes (2026-02-12)

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Sanitizer Validation Order Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "tool_registry",
    "module_name": "test_sanitizer_validation_order",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


class TestValidationOrdering:
    """Total-bytes violation must be the FIRST reason reported, never masked."""

    def test_oversized_payload_reports_total_bytes_first(self):
        """A payload exceeding both total bytes AND string length must
        report total-bytes as the first (highest-severity) reason."""
        from core.tools.sanitizer import (
            ToolInputSanitizationError,
            ToolInputSanitizer,
            ToolInputSanitizerConfig,
        )

        config = ToolInputSanitizerConfig(
            max_total_bytes=32_768,
            max_string_length=16_384,
        )
        sanitizer = ToolInputSanitizer(config)

        huge_payload = {"data": "A" * 50_000}

        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("test_tool", huge_payload)

        reasons = exc_info.value.reasons
        assert len(reasons) >= 1, "Must report at least one violation"
        assert "max_total_bytes" in reasons[0], (
            f"First reason must be total-bytes violation, got: '{reasons[0]}'. "
            "Total-bytes check must precede string-length check."
        )

    def test_string_length_not_masked_when_within_total_bytes(self):
        """When total bytes is within limits but string exceeds max_string_length,
        the string-length violation must still be reported."""
        from core.tools.sanitizer import (
            ToolInputSanitizationError,
            ToolInputSanitizer,
            ToolInputSanitizerConfig,
        )

        config = ToolInputSanitizerConfig(
            max_total_bytes=100_000,
            max_string_length=100,
        )
        sanitizer = ToolInputSanitizer(config)

        payload = {"data": "B" * 200}

        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("test_tool", payload)

        reasons = exc_info.value.reasons
        assert any("max_string_length" in r for r in reasons), (
            "String-length violation must be reported when total bytes is OK"
        )

    def test_depth_violation_reported_when_within_total_bytes(self):
        """Nesting depth violation must be reported independently of byte size."""
        from core.tools.sanitizer import (
            ToolInputSanitizationError,
            ToolInputSanitizer,
            ToolInputSanitizerConfig,
        )

        config = ToolInputSanitizerConfig(
            max_total_bytes=100_000,
            max_depth=3,
        )
        sanitizer = ToolInputSanitizer(config)

        nested: dict = {"level": "leaf"}
        for _ in range(6):
            nested = {"child": nested}

        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("test_tool", nested)

        reasons = exc_info.value.reasons
        assert any("max_depth" in r for r in reasons), (
            "Depth violation must be reported"
        )

    def test_multiple_structural_violations_all_reported(self):
        """When total bytes is OK but depth, list length, and string length
        are all exceeded, ALL structural violations must appear in reasons."""
        from core.tools.sanitizer import (
            ToolInputSanitizationError,
            ToolInputSanitizer,
            ToolInputSanitizerConfig,
        )

        config = ToolInputSanitizerConfig(
            max_total_bytes=500_000,
            max_depth=2,
            max_list_length=3,
            max_string_length=10,
        )
        sanitizer = ToolInputSanitizer(config)

        payload = {
            "deep": {"a": {"b": {"c": "leaf"}}},
            "long_list": [1, 2, 3, 4, 5],
            "long_string": "X" * 20,
        }

        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("test_tool", payload)

        reasons_text = " ".join(exc_info.value.reasons)
        assert "max_depth" in reasons_text, "Depth violation missing"
        assert "max_list_length" in reasons_text, "List-length violation missing"
        assert "max_string_length" in reasons_text, "String-length violation missing"

    def test_oversized_payload_bails_early_skips_structural(self):
        """When total bytes is exceeded, structural checks must be skipped."""
        from core.tools.sanitizer import (
            ToolInputSanitizationError,
            ToolInputSanitizer,
            ToolInputSanitizerConfig,
        )

        config = ToolInputSanitizerConfig(
            max_total_bytes=100,
            max_depth=2,
            max_string_length=10,
        )
        sanitizer = ToolInputSanitizer(config)

        payload = {"data": "A" * 200}

        with pytest.raises(ToolInputSanitizationError) as exc_info:
            sanitizer.sanitize("test_tool", payload)

        reasons = exc_info.value.reasons
        assert len(reasons) == 1, (
            f"Oversized payload should produce exactly 1 reason "
            f"(bail early), got {len(reasons)}: {reasons}"
        )
        assert "max_total_bytes" in reasons[0]
