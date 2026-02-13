"""
Validation protocols and implementations for L9 async-first codebase.

This module provides a comprehensive validation framework using Protocol-based
interfaces for type safety and structlog for observability.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Validation Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:48:24Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "validation_protocols",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.protocols.__init__"],
    },
}
# ============================================================================

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Core Enums and Data Structures
# ============================================================================


class ValidationSeverity(Enum):
    """Severity levels for validation errors."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """
    Represents a single validation error or warning.

    Attributes:
        field: The field name that failed validation.
        message: Human-readable error message.
        severity: The severity level of the validation issue.
        code: Machine-readable error code for categorization.
        metadata: Additional contextual data about the error.
    """

    field: str
    message: str
    severity: ValidationSeverity
    code: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate error structure on instantiation."""
        if not self.field:
            raise ValueError("field cannot be empty")
        if not self.message:
            raise ValueError("message cannot be empty")
        if not self.code:
            raise ValueError("code cannot be empty")


@dataclass
class ValidationResult:
    """
    Aggregates validation results with helper methods.

    Attributes:
        valid: Whether validation passed completely.
        errors: List of validation errors encountered.
        warnings: List of validation warnings encountered.
    """

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def has_errors(self) -> bool:
        """Check if any errors (not warnings) are present."""
        return any(e.severity == ValidationSeverity.ERROR for e in self.errors)

    def get_error_messages(self) -> list[str]:
        """Extract error messages for easy logging or display."""
        return [
            e.message for e in self.errors if e.severity == ValidationSeverity.ERROR
        ]

    def get_warning_messages(self) -> list[str]:
        """Extract warning messages for easy logging or display."""
        return [
            w.message for w in self.warnings if w.severity == ValidationSeverity.WARNING
        ]


# ============================================================================
# Protocol Definitions
# ============================================================================


@runtime_checkable
class ValidationProtocol(Protocol):
    """
    Interface for validation implementations.

    Defines the contract that all validators must implement to work
    with the L9 validation framework.
    """

    @must_stay_async("callers use await")
    async def validate(
        self,
        data: Any,
        schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        Perform complete validation on data.

        Args:
            data: The data to validate.
            schema: Optional JSON Schema-like configuration for validation rules.

        Returns:
            ValidationResult containing validation outcomes.
        """
        ...

    @must_stay_async("callers use await")
    async def validate_field(
        self,
        field_name: str,
        value: Any,
        field_schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        Validate a single field.

        Args:
            field_name: Name of the field being validated.
            value: The field value to validate.
            field_schema: JSON Schema-like rules for this specific field.

        Returns:
            ValidationResult for the field.
        """
        ...

    @must_stay_async("callers use await")
    async def validate_required(
        self,
        data: dict[str, Any],
        required_fields: list[str],
    ) -> ValidationResult:
        """
        Validate that required fields are present and non-null.

        Args:
            data: Dictionary to check for required fields.
            required_fields: List of field names that must be present.

        Returns:
            ValidationResult indicating presence/absence of required fields.
        """
        ...

    @must_stay_async("callers use await")
    async def validate_type(
        self,
        value: Any,
        expected_type: str | type,
    ) -> ValidationResult:
        """
        Validate that a value matches an expected type.

        Args:
            value: The value to type-check.
            expected_type: Expected type as string (e.g., 'string', 'integer') or Python type.

        Returns:
            ValidationResult for type validation.
        """
        ...


# ============================================================================
# Standard Validator Implementation
# ============================================================================


class StandardValidator:
    """
    Production-grade validator for L9 async codebase.

    Implements JSON Schema-like validation with full async support,
    comprehensive error tracking, and structured logging.
    """

    # Type mappings from schema types to Python types
    TYPE_MAPPING: ClassVar[dict[str, type | tuple[type, ...]]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
        "null": type(None),
    }

    def __init__(self, logger_instance: structlog.PrintLogger | None = None) -> None:
        """
        Initialize the validator.

        Args:
            logger_instance: Optional custom structlog logger instance.
        """
        self.logger = logger_instance or logger

    @must_stay_async("callers use await")
    async def validate(
        self,
        data: Any,
        schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        Perform complete validation on data against schema.

        Args:
            data: The data to validate.
            schema: JSON Schema-like configuration dictionary.

        Returns:
            ValidationResult aggregating all validation outcomes.
        """
        if schema is None:
            schema = {}

        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        self.logger.info(  # type: ignore[call-arg]
            "validation_started",
            schema_keys=list(schema.keys()) if schema else None,
        )

        # Validate required fields
        if "required" in schema:
            required_result = await self.validate_required(
                data if isinstance(data, dict) else {},
                schema["required"],
            )
            errors.extend(required_result.errors)
            warnings.extend(required_result.warnings)

        # Validate individual fields
        if "properties" in schema and isinstance(data, dict):
            for field_name, field_schema in schema["properties"].items():
                if field_name in data:
                    field_result = await self.validate_field(
                        field_name,
                        data[field_name],
                        field_schema,
                    )
                    errors.extend(field_result.errors)
                    warnings.extend(field_result.warnings)

        valid = len([e for e in errors if e.severity == ValidationSeverity.ERROR]) == 0
        result = ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
        )

        self.logger.info(  # type: ignore[call-arg]
            "validation_completed",
            valid=valid,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
        )

        return result

    @must_stay_async("callers use await")
    async def validate_field(
        self,
        field_name: str,
        value: Any,
        field_schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        Validate a single field against its schema definition.

        Args:
            field_name: Name of the field being validated.
            value: The field value to validate.
            field_schema: JSON Schema-like rules for this field.

        Returns:
            ValidationResult for the field validation.
        """
        if field_schema is None:
            field_schema = {}

        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        # Type validation
        if "type" in field_schema:
            type_result = await self.validate_type(value, field_schema["type"])
            errors.extend(type_result.errors)
            warnings.extend(type_result.warnings)

        # Enum validation
        if "enum" in field_schema and value not in field_schema["enum"]:
            errors.append(
                ValidationError(
                    field=field_name,
                    message=f"Value '{value}' not in allowed values: {field_schema['enum']}",
                    severity=ValidationSeverity.ERROR,
                    code="ENUM_VALIDATION_FAILED",
                    metadata={"allowed_values": field_schema["enum"], "value": value},
                )
            )

        # String constraints
        if isinstance(value, str):
            if "minLength" in field_schema and len(value) < field_schema["minLength"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"String length {len(value)} is below minimum {field_schema['minLength']}",
                        severity=ValidationSeverity.ERROR,
                        code="MIN_LENGTH_VIOLATION",
                        metadata={
                            "min_length": field_schema["minLength"],
                            "actual_length": len(value),
                        },
                    )
                )

            if "maxLength" in field_schema and len(value) > field_schema["maxLength"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"String length {len(value)} exceeds maximum {field_schema['maxLength']}",
                        severity=ValidationSeverity.ERROR,
                        code="MAX_LENGTH_VIOLATION",
                        metadata={
                            "max_length": field_schema["maxLength"],
                            "actual_length": len(value),
                        },
                    )
                )

            if "pattern" in field_schema:
                import re

                if not re.match(field_schema["pattern"], value):
                    errors.append(
                        ValidationError(
                            field=field_name,
                            message=f"String does not match pattern: {field_schema['pattern']}",
                            severity=ValidationSeverity.ERROR,
                            code="PATTERN_VALIDATION_FAILED",
                            metadata={
                                "pattern": field_schema["pattern"],
                                "value": value,
                            },
                        )
                    )

        # Numeric constraints
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in field_schema and value < field_schema["minimum"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Value {value} is below minimum {field_schema['minimum']}",
                        severity=ValidationSeverity.ERROR,
                        code="MIN_VALUE_VIOLATION",
                        metadata={"minimum": field_schema["minimum"], "value": value},
                    )
                )

            if "maximum" in field_schema and value > field_schema["maximum"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Value {value} exceeds maximum {field_schema['maximum']}",
                        severity=ValidationSeverity.ERROR,
                        code="MAX_VALUE_VIOLATION",
                        metadata={"maximum": field_schema["maximum"], "value": value},
                    )
                )

        # Array constraints
        if isinstance(value, list):
            if "minItems" in field_schema and len(value) < field_schema["minItems"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Array length {len(value)} is below minimum {field_schema['minItems']}",
                        severity=ValidationSeverity.ERROR,
                        code="MIN_ITEMS_VIOLATION",
                        metadata={
                            "min_items": field_schema["minItems"],
                            "actual_items": len(value),
                        },
                    )
                )

            if "maxItems" in field_schema and len(value) > field_schema["maxItems"]:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Array length {len(value)} exceeds maximum {field_schema['maxItems']}",
                        severity=ValidationSeverity.ERROR,
                        code="MAX_ITEMS_VIOLATION",
                        metadata={
                            "max_items": field_schema["maxItems"],
                            "actual_items": len(value),
                        },
                    )
                )

        valid = len([e for e in errors if e.severity == ValidationSeverity.ERROR]) == 0

        self.logger.info(  # type: ignore[call-arg]
            "field_validation_completed",
            field_name=field_name,
            valid=valid,
            error_count=len(errors),
        )

        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    @must_stay_async("callers use await")
    async def validate_required(
        self,
        data: dict[str, Any],
        required_fields: list[str],
    ) -> ValidationResult:
        """
        Validate presence and non-null status of required fields.

        Args:
            data: Dictionary to check for required fields.
            required_fields: List of field names that must be present.

        Returns:
            ValidationResult for required field validation.
        """
        errors: list[ValidationError] = []

        for field_name in required_fields:
            if field_name not in data or data[field_name] is None:
                errors.append(
                    ValidationError(
                        field=field_name,
                        message=f"Required field '{field_name}' is missing or null",
                        severity=ValidationSeverity.ERROR,
                        code="REQUIRED_FIELD_MISSING",
                        metadata={"required_field": field_name},
                    )
                )

                self.logger.warning(  # type: ignore[call-arg]
                    "required_field_missing",
                    field_name=field_name,
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    @must_stay_async("callers use await")
    async def validate_type(
        self,
        value: Any,
        expected_type: str | type,
    ) -> ValidationResult:
        """
        Validate that a value matches an expected type.

        Args:
            value: The value to type-check.
            expected_type: Type as string name or Python type object.

        Returns:
            ValidationResult for type validation.
        """
        if isinstance(expected_type, str):
            expected_type = self.TYPE_MAPPING.get(expected_type, str)

        errors: list[ValidationError] = []

        if not isinstance(value, expected_type):
            type_name = (
                expected_type.__name__
                if hasattr(expected_type, "__name__")
                else str(expected_type)
            )
            errors.append(
                ValidationError(
                    field="unknown",
                    message=f"Expected type {type_name}, got {type(value).__name__}",
                    severity=ValidationSeverity.ERROR,
                    code="TYPE_MISMATCH",
                    metadata={
                        "expected_type": type_name,
                        "actual_type": type(value).__name__,
                        "value": str(value),
                    },
                )
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ============================================================================
# Decorator for Function Input Validation
# ============================================================================

T = TypeVar("T", bound=Callable[..., Any])


def validate_input(
    schema: dict[str, Any] | None = None,
    validator: StandardValidator | None = None,
) -> Callable[[T], T]:
    """
    Decorator for automatic input validation of async functions.

    Validates function arguments against a schema before execution.
    Works with both async and sync functions.

    Args:
        schema: JSON Schema-like validation rules.
        validator: Custom validator instance (creates default if None).

    Returns:
        Decorated function with validation.

    Raises:
        ValueError: If validation fails with ERROR severity.

    Example:
        ```python
        user_schema = {
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "email": {"type": "string", "pattern": r".*@.*"},
            },
        }


        @validate_input(schema=user_schema)
        @must_stay_async("callers use await")
        async def create_user(name: str, email: str) -> dict:
            return {"name": name, "email": email}
        ```
    """
    schema = schema or {}
    val = validator or StandardValidator()

    def decorator(func: T) -> T:
        """
        Performs validation of asynchronous and synchronous functions within the L9 async-first codebase, ensuring type safety and proper error handling.
        Args:
            func: The function to be decorated, which may be synchronous or asynchronous.
        Returns:
            A wrapped version of the input function with validation logic.
        Raises:
            ValueError: If validation fails during function execution.
        """
        if iscoroutinefunction(func):

            @wraps(func)
            @must_stay_async("callers use await")
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """
                Performs asynchronous validation by wrapping a function to ensure data integrity within the L9 async-first validation framework.

                Args:
                    *args: Positional arguments for the wrapped function.
                    **kwargs: Keyword arguments for the wrapped function.

                Returns:
                    The result of the wrapped function, potentially after validation.

                Raises:
                    ValueError: If validation fails or invalid data is encountered.
                """
                # Build data dict from function arguments
                data = {**kwargs}
                if args:
                    import inspect

                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    for i, arg in enumerate(args):
                        if i < len(params):
                            data[params[i]] = arg

                # Validate
                result = await val.validate(data, schema)

                if not result.valid:
                    error_messages = result.get_error_messages()
                    error_str = "; ".join(error_messages)
                    logger.error(
                        "validation_failed",
                        function=func.__name__,
                        errors=error_messages,
                    )
                    raise ValueError(f"Input validation failed: {error_str}")

                return await func(*args, **kwargs)

            return async_wrapper  # type: ignore

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Performs synchronous validation of functions within the L9 async-first codebase, ensuring type safety and proper error handling.

            Args:
                *args: Positional arguments for the wrapped function.
                **kwargs: Keyword arguments for the wrapped function.

            Returns:
                The result of the wrapped function execution.

            Raises:
                ValueError: If validation fails or invalid data is encountered.
            """
            # For sync functions, we need to run validation synchronously
            import asyncio
            import inspect

            # Build data dict from function arguments
            data = {**kwargs}
            if args:
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                for i, arg in enumerate(args):
                    if i < len(params):
                        data[params[i]] = arg

            # Run async validation in event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                should_close = True
            else:
                should_close = False

            try:
                result = loop.run_until_complete(val.validate(data, schema))
            finally:
                if should_close:
                    loop.close()

            if not result.valid:
                error_messages = result.get_error_messages()
                error_str = "; ".join(error_messages)
                logger.error(
                    "validation_failed",
                    function=func.__name__,
                    errors=error_messages,
                )
                raise ValueError(f"Input validation failed: {error_str}")

            return func(*args, **kwargs)

        return sync_wrapper  # type: ignore

    return decorator


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-121",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "dataclass",
        "event-driven",
        "foundation",
        "logging",
        "messaging",
        "validation",
    ],
    "keywords": [
        "async",
        "create",
        "decorator",
        "errors",
        "field",
        "messages",
        "module",
        "protocol",
    ],
    "business_value": "This module provides a comprehensive validation framework using Protocol-based interfaces for type safety and structlog for observability.",
    "last_modified": "2026-01-25T08:58:45Z",
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
