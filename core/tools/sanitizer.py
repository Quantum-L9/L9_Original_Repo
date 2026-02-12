"""
L9 Core Tools - Tool Input Sanitizer
===================================

Deterministic sanitization and validation gate for tool call arguments.

Purpose:
- Prevent garbage/unsafe tool arguments from reaching tool executors
- Enforce schema shape (properties/required) where available
- Apply resource limits (size, depth, list lengths, string lengths)
- Normalize basic primitive types for determinism

This module is intentionally conservative and fast:
- If a tool provides a schema, we reject unknown keys by default.
- If a tool provides no schema (or an empty schema), we only enforce resource limits.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Input Sanitizer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-09T01:42:58Z",
    "updated_at": "2026-01-08T22:15:53Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "sanitizer",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.tools.registry_adapter",
            "tests.unit.test_tool_input_sanitizer",
        ],
    },
}
# ============================================================================

import json
import re
from dataclasses import dataclass
from typing import Any

_DEFAULT_MAX_TOTAL_BYTES = 32_768  # 32KB
_DEFAULT_MAX_DEPTH = 8
_DEFAULT_MAX_LIST_LENGTH = 200
_DEFAULT_MAX_STRING_LENGTH = 16_384

# Allowlist for internal context keys injected by the runtime (not user supplied).
_INTERNAL_CONTEXT_KEYS = {"agent_id", "task_id", "principal_id"}

# Conservative path key heuristics (only apply traversal checks for these keys).
_PATH_LIKE_KEY_RE = re.compile(r"(path|file|filename|directory|dir)$", re.IGNORECASE)


class ToolInputSanitizationError(ValueError):
    """Raised when tool input cannot be sanitized/validated."""

    def __init__(self, tool_id: str, reasons: list[str]) -> None:
        """Initialize sanitization error with tool ID and failure reasons.

        Args:
            tool_id: Identifier of the tool that failed validation.
            reasons: List of validation failure reasons.
        """
        super().__init__(f"Tool input rejected for '{tool_id}': " + "; ".join(reasons))
        self.tool_id = tool_id
        self.reasons = reasons


@dataclass(frozen=True)
class ToolInputSanitizerConfig:
    """
    Configuration class for tool input sanitization parameters to prevent unsafe arguments.
    Args:
        max_total_bytes: Maximum total size in bytes allowed for input data.
        max_depth: Maximum allowed nesting depth of input structures.
        max_list_length: Maximum length permitted for input lists.
        max_string_length: Maximum length allowed for input strings.
        internal_context_keys: Set of internal context keys to exclude from validation.
    """

    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES
    max_depth: int = _DEFAULT_MAX_DEPTH
    max_list_length: int = _DEFAULT_MAX_LIST_LENGTH
    max_string_length: int = _DEFAULT_MAX_STRING_LENGTH
    internal_context_keys: frozenset[str] = frozenset(_INTERNAL_CONTEXT_KEYS)


class ToolInputSanitizer:
    """
    Centralized input sanitization for tool arguments.

    Schema expectations (JSON-schema-like dict):
    - {"type": "object", "properties": {...}, "required": [...]}
    """

    def __init__(self, config: ToolInputSanitizerConfig | None = None) -> None:
        """Initialize sanitizer with optional configuration.

        Args:
            config: Resource limits and settings. Uses defaults if None.
        """
        self._config = config or ToolInputSanitizerConfig()

    def sanitize(
        self,
        tool_id: str,
        arguments: Any,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Sanitize and validate tool arguments.

        Returns sanitized dict or raises ToolInputSanitizationError.
        """
        reasons: list[str] = []

        if not isinstance(arguments, dict):
            raise ToolInputSanitizationError(tool_id, ["arguments must be an object"])

        # Enforce resource limits early (on raw input) to avoid pathological payloads.
        self._enforce_resource_limits(tool_id, arguments, reasons=reasons)
        if reasons:
            raise ToolInputSanitizationError(tool_id, reasons)

        schema_obj = schema or {}
        properties = schema_obj.get("properties") or {}
        required: list[str] = list(schema_obj.get("required") or [])

        # If schema has properties, enforce unknown-key rejection by default.
        enforce_known_keys = bool(properties)

        sanitized: dict[str, Any] = {}

        # Validate required fields (only if schema declares them).
        if required:
            missing = [k for k in required if k not in arguments]
            if missing:
                reasons.append(f"missing required fields: {sorted(missing)}")

        # Validate/sanitize each provided key.
        for key, value in arguments.items():
            if not isinstance(key, str):
                reasons.append("all argument keys must be strings")
                continue

            if (
                enforce_known_keys
                and key not in properties
                and key not in self._config.internal_context_keys
            ):
                reasons.append(f"unknown field: {key}")
                continue

            # Path traversal / invalid byte checks for path-like keys.
            if _PATH_LIKE_KEY_RE.search(key) and isinstance(value, str):
                if "\x00" in value:
                    reasons.append(f"{key}: contains null byte")
                    continue
                if self._has_path_traversal(value):
                    reasons.append(f"{key}: path traversal detected")
                    continue

            expected = properties.get(key) if isinstance(properties, dict) else None
            sanitized[key] = self._sanitize_value(
                key=key, value=value, expected=expected, reasons=reasons
            )

        if reasons:
            raise ToolInputSanitizationError(tool_id, reasons)

        # Final resource-limit pass on sanitized output for determinism.
        self._enforce_resource_limits(tool_id, sanitized, reasons=reasons)
        if reasons:
            raise ToolInputSanitizationError(tool_id, reasons)

        return sanitized

    def _sanitize_value(
        self,
        key: str,
        value: Any,
        expected: dict[str, Any] | None,
        reasons: list[str],
    ) -> Any:
        """Sanitize a single value based on expected schema type."""
        expected_type = None
        if isinstance(expected, dict):
            expected_type = expected.get("type")

        # Null is allowed (executors can enforce further constraints); still size-limited elsewhere.
        if value is None:
            return None

        # Primitive coercions for determinism.
        if expected_type == "string":
            if isinstance(value, (int, float, bool)):
                return str(value)
            if not isinstance(value, str):
                reasons.append(f"{key}: expected string")
                return value
            return value.strip()

        if expected_type == "integer":
            if isinstance(value, bool):
                reasons.append(f"{key}: expected integer, got bool")
                return value
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip().lstrip("-").isdigit():
                try:
                    return int(value.strip())
                except Exception:
                    reasons.append(f"{key}: failed to coerce integer")
                    return value
            reasons.append(f"{key}: expected integer")
            return value

        if expected_type == "number":
            if isinstance(value, bool):
                reasons.append(f"{key}: expected number, got bool")
                return value
            if isinstance(value, (int, float)):
                # nosemgrep: l9-float-requires-try-except (isinstance already validated)
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value.strip())
                except Exception:
                    reasons.append(f"{key}: expected number")
                    return value
            reasons.append(f"{key}: expected number")
            return value

        if expected_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                v = value.strip().lower()
                if v in {"true", "1", "yes"}:
                    return True
                if v in {"false", "0", "no"}:
                    return False
            reasons.append(f"{key}: expected boolean")
            return value

        if expected_type == "array":
            if isinstance(value, list):
                return value
            reasons.append(f"{key}: expected array")
            return value

        if expected_type == "object":
            if isinstance(value, dict):
                return value
            reasons.append(f"{key}: expected object")
            return value

        # No schema info: apply minimal normalization for strings.
        if isinstance(value, str):
            return value.strip()

        return value

    def _enforce_resource_limits(
        self, tool_id: str, obj: Any, reasons: list[str]
    ) -> None:
        """Check object against depth, size, and length limits."""
        # Total payload size limit FIRST — cheapest global check, highest severity
        try:
            raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            reasons.append("arguments are not JSON-serializable")
            return

        if len(raw.encode("utf-8")) > self._config.max_total_bytes:
            reasons.append(
                f"payload exceeds max_total_bytes={self._config.max_total_bytes}"
            )
            return  # Bail on oversized — structural checks are moot

        # Depth + structural limits (no early returns — report ALL violations)
        if self._exceeds_depth(obj, max_depth=self._config.max_depth):
            reasons.append(f"input nesting exceeds max_depth={self._config.max_depth}")

        # List length limits (recursive)
        if self._exceeds_list_length(obj, max_len=self._config.max_list_length):
            reasons.append(
                f"list length exceeds max_list_length={self._config.max_list_length}"
            )

        # String length limits (recursive)
        if self._exceeds_string_length(obj, max_len=self._config.max_string_length):
            reasons.append(
                f"string length exceeds max_string_length={self._config.max_string_length}"
            )

    @staticmethod
    def _exceeds_depth(obj: Any, max_depth: int) -> bool:
        """
        Performs recursive validation to detect unsafe or oversized tool call arguments in the sanitizer module.

        Args:
            o: The object to validate, which can be a list, dict, or other types.

        Returns:
            True if an unsafe or oversized argument is found; otherwise, False.
        """
        """Check if object nesting exceeds maximum depth."""

        def _walk(o: Any, depth: int) -> bool:
            """
            Performs recursive validation of tool call arguments to prevent unsafe data.

            Args:
                o: The argument object to validate, which can be a string, list, or dictionary.

            Returns:
                True if the argument passes validation checks; False otherwise.
            """
            if depth > max_depth:
                return True
            if isinstance(o, dict):
                return any(_walk(v, depth + 1) for v in o.values())
            if isinstance(o, list):
                return any(_walk(v, depth + 1) for v in o)
            return False

        return _walk(obj, 0)

    @staticmethod
    def _exceeds_list_length(obj: Any, max_len: int) -> bool:
        """Check if any list in object exceeds maximum length."""

        def _walk(o: Any) -> bool:
            """
            Performs recursive validation to detect unsafe or excessively large tool arguments in sanitization processes.

            Args:
                o: The object to validate, which can be a list, dict, or other types.

            Returns:
                True if an unsafe or oversized argument is detected; otherwise, False.
            """
            if isinstance(o, list):
                if len(o) > max_len:
                    return True
                return any(_walk(v) for v in o)
            if isinstance(o, dict):
                """
                Performs recursive validation of tool call arguments to prevent unsafe data.

                Args:
                    o: The argument object to validate, which can be a string, list, or dictionary.

                Returns:
                    True if the argument or any nested element exceeds the maximum length; otherwise, False.
                """
                return any(_walk(v) for v in o.values())
            return False

        return _walk(obj)

    @staticmethod
    def _exceeds_string_length(obj: Any, max_len: int) -> bool:
        """Check if any string in object exceeds maximum length."""

        def _walk(o: Any) -> bool:
            """
            Performs recursive validation of tool call arguments to prevent unsafe data.

            Args:
                o: The argument object to validate, which can be a string, list, or dictionary.

            Returns:
                True if the argument or any nested element exceeds the maximum length, indicating potential unsafe content.
            """
            if isinstance(o, str):
                return len(o) > max_len
            if isinstance(o, list):
                return any(_walk(v) for v in o)
            if isinstance(o, dict):
                return any(_walk(v) for v in o.values())
            return False

        return _walk(obj)

    @staticmethod
    def _has_path_traversal(path: str) -> bool:
        """Check if path contains directory traversal (..) segments."""
        # Split on both Unix and Windows separators.
        parts = re.split(r"[\\/]+", path)
        return any(p == ".." for p in parts)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-014",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "dataclass",
        "event-driven",
        "foundation",
        "serialization",
        "tool-registry",
    ],
    "keywords": [
        "arguments",
        "enforce",
        "lengths",
        "limits",
        "module",
        "provides",
        "resource",
        "sanitization",
    ],
    "business_value": "If a tool provides a schema, we reject unknown keys by default. If a tool provides no schema (or an empty schema), we only enforce resource limits.",
    "last_modified": "2026-01-08T22:15:53Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
