"""
L9 Core - Exception Hierarchy
==============================

Centralized exception classes for L9 Secure AI OS.
Provides specific exception types for better error handling and debugging.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Exception Hierarchy",
    "module_version": "1.0.0",
    "created_by": "Manus AI",
    "created_at": "2026-01-22T00:00:00Z",
    "updated_at": "2026-01-22T00:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "exceptions",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "runtime.l_tools",
            "core.agents.executor",
        ],
    },
}
# ============================================================================

from typing import Any


# =============================================================================
# Base Exception
# =============================================================================


class L9Error(Exception):
    """Base exception for all L9 errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        """
        Initialize L9 error.

        Args:
            message: Human-readable error message
            details: Additional error context
            retryable: Whether the operation can be retried
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.retryable = retryable


# =============================================================================
# API Errors
# =============================================================================


class L9APIError(L9Error):
    """Base exception for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error context
            retryable: Whether the request can be retried
        """
        super().__init__(message, details, retryable)
        self.status_code = status_code


class L9ValidationError(L9APIError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=400, details=details, retryable=False)


class L9NotFoundError(L9APIError):
    """Exception raised when a resource is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=404, details=details, retryable=False)


class L9AuthenticationError(L9APIError):
    """Exception raised when authentication fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=401, details=details, retryable=False)


class L9AuthorizationError(L9APIError):
    """Exception raised when authorization fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=403, details=details, retryable=False)


class L9RateLimitError(L9APIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=429, details=details, retryable=True)


# =============================================================================
# Memory Errors
# =============================================================================


class L9MemoryError(L9Error):
    """Base exception for memory-related errors."""

    pass


class L9MemoryWriteError(L9MemoryError):
    """Exception raised when memory write fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9MemoryReadError(L9MemoryError):
    """Exception raised when memory read fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9MemoryConnectionError(L9MemoryError):
    """Exception raised when memory connection fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


# =============================================================================
# Agent Errors
# =============================================================================


class L9AgentError(L9Error):
    """Base exception for agent-related errors."""

    pass


class L9AgentExecutionError(L9AgentError):
    """Exception raised when agent execution fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


class L9AgentTimeoutError(L9AgentError):
    """Exception raised when agent execution times out."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9AgentConfigurationError(L9AgentError):
    """Exception raised when agent configuration is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


# =============================================================================
# Tool Errors
# =============================================================================


class L9ToolError(L9Error):
    """Base exception for tool-related errors."""

    pass


class L9ToolExecutionError(L9ToolError):
    """Exception raised when tool execution fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


class L9ToolNotFoundError(L9ToolError):
    """Exception raised when a tool is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


class L9ToolTimeoutError(L9ToolError):
    """Exception raised when tool execution times out."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9ToolValidationError(L9ToolError):
    """Exception raised when tool input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


# =============================================================================
# Infrastructure Errors
# =============================================================================


class L9InfrastructureError(L9Error):
    """Base exception for infrastructure-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9DatabaseError(L9InfrastructureError):
    """Exception raised when database operations fail."""

    pass


class L9ConnectionError(L9InfrastructureError):
    """Exception raised when network/service connection fails."""

    pass


class L9TimeoutError(L9InfrastructureError):
    """Exception raised when an operation times out."""

    pass


class L9ConfigurationError(L9Error):
    """Exception raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=False)


# =============================================================================
# External Service Errors
# =============================================================================


class L9ExternalServiceError(L9Error):
    """Base exception for external service errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details, retryable=True)


class L9LLMError(L9ExternalServiceError):
    """Exception raised when LLM API calls fail."""

    pass


class L9EmbeddingError(L9ExternalServiceError):
    """Exception raised when embedding generation fails."""

    pass


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-FOUND-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["error-handling", "exception", "foundation", "core"],
    "keywords": [
        "exception",
        "error",
        "api",
        "agent",
        "tool",
        "memory",
        "infrastructure",
    ],
    "business_value": "Provides centralized exception hierarchy for consistent error handling across L9",
    "last_modified": "2026-01-22T00:00:00Z",
    "modified_by": "Manus_AI",
    "change_summary": "Initial creation of L9 exception hierarchy",
}
# ============================================================================
