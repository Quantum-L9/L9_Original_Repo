# core/protocols/error_handling_protocols.py
"""
Error handling protocols and implementations for L9 async-first codebase.

This module provides a production-ready error handling system using typing.Protocol,
structlog for structured logging, and Python 3.12 async/await syntax.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Error Handling Protocols",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:48:24Z",
    "updated_at": "2026-02-02T10:35:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "error_handling_protocols",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "PostgreSQL"],
        "memory_layers": [],
        "imported_by": ["core.protocols.__init__"],
    },
}
# ============================================================================

import asyncio
import dataclasses
import enum
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger(__name__)


class ErrorSeverity(enum.Enum):
    """Error severity levels for classification and handling decisions."""

    UNKNOWN = "unknown"
    """Unknown severity - not yet classified."""

    TRANSIENT = "transient"
    """Temporary error that may succeed on retry."""

    PERMANENT = "permanent"
    """Persistent error unlikely to resolve without intervention."""

    FATAL = "fatal"
    """Critical error requiring immediate shutdown or escalation."""


class ErrorCategory(enum.Enum):
    """Error categories for classification and routing."""

    VALIDATION = "validation"
    """Input validation or business logic errors."""

    TIMEOUT = "timeout"
    """Operation exceeded time limits."""

    NETWORK = "network"
    """Network connectivity or communication errors."""

    DATABASE = "database"
    """Database connection or query errors."""

    PERMISSION = "permission"
    """Authorization or authentication failures."""

    RESOURCE = "resource"
    """Resource exhaustion or unavailability."""

    UNKNOWN = "unknown"
    """Unclassified or unexpected errors."""


@dataclasses.dataclass
class ErrorContext:
    """
    Contextual information about an error for structured logging and analysis.

    Attributes:
        error_id: Unique identifier for this error instance.
        error_type: The exception class name.
        message: Human-readable error message.
        severity: ErrorSeverity classification.
        category: ErrorCategory classification.
        timestamp: When the error occurred (UTC).
        traceback_str: Full exception traceback.
        source_module: Module where error originated.
        source_function: Function where error originated.
        correlation_id: ID for tracing related operations.
        metadata: Additional contextual data.
        attempt_number: Current retry attempt (0-based).
        max_retries: Maximum retry attempts allowed.
        is_retryable: Whether error qualifies for retry.
    """

    error_id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.UNKNOWN
    category: ErrorCategory = ErrorCategory.UNKNOWN
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now(UTC))
    traceback_str: str = ""
    source_module: str = ""
    source_function: str = ""
    correlation_id: str | None = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    attempt_number: int = 0
    max_retries: int = 0
    is_retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for structured logging."""
        return dataclasses.asdict(self)


@runtime_checkable
class ErrorHandlingProtocol(Protocol):
    """
    Protocol for error handling implementations.

    Defines the interface that error handlers must implement for L9 async system.
    Enables duck typing and multiple error handler implementations.
    """

    @must_stay_async("callers use await")
    async def handle_error(
        self,
        exception: Exception,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ErrorContext:
        """
        Handle an exception and return structured error context.

        Coordinates classification, logging, and retry decision making.

        Args:
            exception: The exception instance to handle.
            correlation_id: Optional ID for tracing related operations.
            metadata: Optional additional contextual data.

        Returns:
            ErrorContext containing classification and handling decisions.

        Raises:
            Exception: May re-raise fatal errors requiring escalation.
        """
        ...

    def classify_error(
        self, exception: Exception
    ) -> tuple[ErrorSeverity, ErrorCategory]:
        """
        Classify an exception by severity and category.

        Args:
            exception: The exception to classify.

        Returns:
            Tuple of (ErrorSeverity, ErrorCategory) classification.
        """
        ...

    def should_retry(
        self,
        context: ErrorContext,
        attempt_number: int,
        max_retries: int,
    ) -> bool:
        """
        Determine if an error qualifies for retry based on context and attempt history.

        Args:
            context: ErrorContext from error classification.
            attempt_number: Current attempt number (0-based).
            max_retries: Maximum allowed retry attempts.

        Returns:
            True if error should be retried, False otherwise.
        """
        ...

    @must_stay_async("callers use await")
    async def log_error(self, context: ErrorContext) -> None:
        """
        Log error with structured information for monitoring and analysis.

        Args:
            context: ErrorContext containing error information.

        Raises:
            Exception: Logging errors do not propagate; they are suppressed.
        """
        ...


class StandardErrorHandler:
    """
    Standard error handler implementation for L9 async codebase.

    Provides error classification, structured logging via structlog,
    retry decision making, and full async compatibility.
    """

    def __init__(
        self,
        default_max_retries: int = 3,
        timeout_threshold: float = 30.0,
        log_traceback: bool = True,
    ):
        """
        Initialize StandardErrorHandler.

        Args:
            default_max_retries: Default maximum retry attempts (0-based).
            timeout_threshold: Duration in seconds to classify as timeout.
            log_traceback: Whether to include full tracebacks in logs.
        """
        self.default_max_retries = default_max_retries
        self.timeout_threshold = timeout_threshold
        self.log_traceback = log_traceback

    @must_stay_async("callers use await")
    async def handle_error(
        self,
        exception: Exception,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ErrorContext:
        """
        Handle an exception and return structured error context.

        Coordinates classification, logging, and retry decision making
        with full async compatibility.

        Args:
            exception: The exception instance to handle.
            correlation_id: Optional ID for tracing related operations.
            metadata: Optional additional contextual data.

        Returns:
            ErrorContext containing classification and handling decisions.

        Raises:
            Exception: Re-raises fatal errors requiring system escalation.
        """
        severity, category = self.classify_error(exception)

        # Extract source information from traceback
        tb = traceback.extract_tb(exception.__traceback__)
        source_module = tb[-1].filename if tb else ""
        source_function = tb[-1].name if tb else ""

        context = ErrorContext(
            error_type=type(exception).__name__,
            message=str(exception),
            severity=severity,
            category=category,
            traceback_str=traceback.format_exc() if self.log_traceback else "",
            source_module=source_module,
            source_function=source_function,
            correlation_id=correlation_id,
            metadata=metadata or {},
            is_retryable=severity == ErrorSeverity.TRANSIENT,
        )

        await self.log_error(context)

        if severity == ErrorSeverity.FATAL:
            raise exception

        return context

    def classify_error(
        self, exception: Exception
    ) -> tuple[ErrorSeverity, ErrorCategory]:
        """
        Classify an exception by severity and category.

        Uses exception type, message content, and common async error patterns
        to determine appropriate severity and category.

        Args:
            exception: The exception to classify.

        Returns:
            Tuple of (ErrorSeverity, ErrorCategory) classification.
        """
        exc_type = type(exception).__name__
        exc_message = str(exception).lower()

        # Category classification
        category = self._classify_category(exc_type, exc_message)

        # Severity classification based on category and error type
        severity = self._classify_severity(exc_type, category)

        return severity, category

    def _classify_category(self, exc_type: str, exc_message: str) -> ErrorCategory:
        """Classify error category from exception type and message."""
        if exc_type in ("ValueError", "TypeError", "AttributeError", "KeyError"):
            return ErrorCategory.VALIDATION

        if exc_type in ("TimeoutError", "asyncio.TimeoutError"):
            return ErrorCategory.TIMEOUT

        if exc_type in (
            "ConnectionError",
            "OSError",
            "socket.error",
            "aiohttp.ClientError",
        ):
            return ErrorCategory.NETWORK

        if "timeout" in exc_message or "timed out" in exc_message:
            return ErrorCategory.TIMEOUT

        if any(
            pattern in exc_message
            for pattern in ["connection refused", "connection reset", "no route"]
        ):
            return ErrorCategory.NETWORK

        if exc_type in ("PermissionError", "AuthenticationError"):
            return ErrorCategory.PERMISSION

        if any(
            pattern in exc_message
            for pattern in ["permission denied", "unauthorized", "forbidden"]
        ):
            return ErrorCategory.PERMISSION

        if exc_type in ("MemoryError", "ResourceWarning"):
            return ErrorCategory.RESOURCE

        if any(
            pattern in exc_message
            for pattern in ["resource exhausted", "too many open"]
        ):
            return ErrorCategory.RESOURCE

        if exc_type in (
            "psycopg2.Error",
            "pymongo.errors.MongoException",
            "sqlalchemy.exc.SQLAlchemyError",
        ):
            return ErrorCategory.DATABASE

        if "database" in exc_message or "db" in exc_message:
            return ErrorCategory.DATABASE

        return ErrorCategory.UNKNOWN

    def _classify_severity(
        self, exc_type: str, category: ErrorCategory
    ) -> ErrorSeverity:
        """Classify error severity from exception type and category."""
        # FATAL errors
        if exc_type in (
            "SystemExit",
            "KeyboardInterrupt",
            "GeneratorExit",
        ):
            return ErrorSeverity.FATAL

        if category == ErrorCategory.PERMISSION:
            return ErrorSeverity.PERMANENT

        if category == ErrorCategory.VALIDATION:
            return ErrorSeverity.PERMANENT

        # TRANSIENT errors
        if category in (
            ErrorCategory.TIMEOUT,
            ErrorCategory.NETWORK,
            ErrorCategory.RESOURCE,
        ):
            return ErrorSeverity.TRANSIENT

        # DATABASE errors are typically TRANSIENT (connection issues)
        # but can be PERMANENT (schema errors)
        if category == ErrorCategory.DATABASE:
            return ErrorSeverity.TRANSIENT

        return ErrorSeverity.PERMANENT

    def should_retry(
        self,
        context: ErrorContext,
        attempt_number: int,
        max_retries: int,
    ) -> bool:
        """
        Determine if an error qualifies for retry.

        Transient errors within retry budget qualify for retry.
        Permanent and fatal errors never retry.

        Args:
            context: ErrorContext from error classification.
            attempt_number: Current attempt number (0-based).
            max_retries: Maximum allowed retry attempts.

        Returns:
            True if error should be retried, False otherwise.
        """
        if context.severity == ErrorSeverity.FATAL:
            return False

        if context.severity == ErrorSeverity.PERMANENT:
            return False

        if context.severity == ErrorSeverity.TRANSIENT:
            return attempt_number < max_retries

        return False

    @must_stay_async("callers use await")
    async def log_error(self, context: ErrorContext) -> None:
        """
        Log error with structured information via structlog.

        Produces consistent, machine-readable logs suitable for monitoring,
        alerting, and post-incident analysis.

        Args:
            context: ErrorContext containing error information.

        Raises:
            Exception: Logging errors are suppressed to prevent error loops.
        """
        try:
            log_data = context.to_dict()

            if context.severity == ErrorSeverity.FATAL:
                logger.critical("fatal_error", **log_data)
            elif context.severity == ErrorSeverity.PERMANENT:
                logger.error("permanent_error", **log_data)
            else:
                logger.warning("transient_error", **log_data)

        except Exception:
            # Logger itself failed — write to stderr to avoid recursion
            sys.stderr.write("error_handling.log_error_failed\n")


@asynccontextmanager
@must_stay_async("callers use await")
async def with_error_handling(
    handler: ErrorHandlingProtocol,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    correlation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Async context manager for error handling with automatic retry logic.

    Wraps async operations with classification, logging, and exponential
    backoff retry mechanism.

    Args:
        handler: ErrorHandlingProtocol implementation instance.
        max_retries: Maximum retry attempts (0-based).
        backoff_factor: Exponential backoff multiplier (seconds).
        correlation_id: Optional ID for tracing related operations.
        metadata: Optional additional contextual data.

    Yields:
        None

    Raises:
        Exception: Unrecoverable errors and exhausted retries propagate.

    Example:
        async with with_error_handling(handler, max_retries=3):
            await some_async_operation()
    """
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        try:
            yield
            return

        except Exception as exc:
            context = await handler.handle_error(
                exc, correlation_id=correlation_id, metadata=metadata
            )
            context.attempt_number = attempt
            context.max_retries = max_retries

            if not handler.should_retry(context, attempt, max_retries):
                raise

            last_error = exc
            attempt += 1

            if attempt <= max_retries:
                delay = backoff_factor * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    if last_error:
        raise last_error


__dora_footer__ = {
    "component_id": "CORE-PROTO-001",
    "governance_level": "standard",
    "compliance_required": True,
    "tags": ["error-handling", "protocol", "resilience"],
    "keywords": ["error", "retry", "classification", "async"],
    "business_value": "Unified error handling protocol with classification and retry logic.",
    "last_modified": "2026-01-25T12:00:00Z",
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
