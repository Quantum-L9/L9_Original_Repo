"""
Security-related exceptions for L9.

Provides typed exceptions for security violations, enabling:
- Better error classification in monitoring/alerting
- Structured error responses in APIs
- Clear audit trails for security events

GMP-115: Enterprise-grade security exception hierarchy.
ADR-0087: SQL parameterization enforcement via typed exceptions.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Security Exceptions",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-02-16T18:00:00Z",
    "updated_at": "2026-02-16T18:00:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "security",
    "type": "module",
    "status": "active",
}
# ============================================================================


class SQLSecurityError(ValueError):
    """
    Base exception for SQL security violations.

    All SQL security exceptions inherit from this class, enabling:
    - Catch-all handling for any SQL security issue
    - Consistent error response formatting
    - Security event logging and alerting

    Attributes:
        value: The invalid value that triggered the exception
        allowed: List of allowed values (if applicable)
        policy_file: Path to the policy file defining allowed values
    """

    def __init__(
        self,
        message: str,
        *,
        value: str | None = None,
        allowed: list[str] | None = None,
        policy_file: str = "config/policies/sql_security.yaml",
    ) -> None:
        self.value = value
        self.allowed = allowed or []
        self.policy_file = policy_file
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        """Convert exception to dict for structured logging/responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "value": self.value,
            "allowed_count": len(self.allowed),
            "policy_file": self.policy_file,
        }


class InvalidTableError(SQLSecurityError):
    """
    Raised when an invalid table name is provided.

    This exception prevents SQL injection via dynamic table names.
    Table names cannot be parameterized in SQL, so allowlisting is
    the only defense.
    """

    def __init__(
        self,
        table: str,
        *,
        allowed: list[str] | None = None,
        context: str = "memory",
    ) -> None:
        self.table = table
        self.context = context
        message = f"Invalid table name: {table!r}"
        if allowed:
            message += f". Allowed tables for {context}: {allowed}"
        super().__init__(
            message,
            value=table,
            allowed=allowed,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert exception to dict for structured logging/responses."""
        base = super().to_dict()
        base["table"] = self.table
        base["context"] = self.context
        return base


class InvalidOperationError(SQLSecurityError):
    """
    Raised when an invalid operation is provided for temporal queries.

    Operations determine query structure (e.g., ORDER BY direction,
    WHERE clause structure). Allowlisting prevents injection via
    operation parameter manipulation.
    """

    def __init__(
        self,
        operation: str,
        *,
        allowed: list[str] | None = None,
        context: str = "temporal",
    ) -> None:
        self.operation = operation
        self.context = context
        message = f"Invalid {context} operation: {operation!r}"
        if allowed:
            message += f". Allowed operations: {allowed}"
        super().__init__(
            message,
            value=operation,
            allowed=allowed,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert exception to dict for structured logging/responses."""
        base = super().to_dict()
        base["operation"] = self.operation
        base["context"] = self.context
        return base


class InvalidSortColumnError(SQLSecurityError):
    """
    Raised when an invalid sort column is provided.

    Sort columns in ORDER BY clauses cannot be parameterized.
    Allowlisting prevents injection via sort parameter manipulation.
    """

    def __init__(
        self,
        column: str,
        *,
        table: str = "unknown",
        allowed: list[str] | None = None,
    ) -> None:
        self.column = column
        self.table = table
        message = f"Invalid sort column for {table}: {column!r}"
        if allowed:
            message += f". Allowed columns: {allowed}"
        super().__init__(
            message,
            value=column,
            allowed=allowed,
        )

    def to_dict(self) -> dict[str, object]:
        """Convert exception to dict for structured logging/responses."""
        base = super().to_dict()
        base["column"] = self.column
        base["table"] = self.table
        return base


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-FOUND-SEC-EXC",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["core", "exceptions", "security", "sql", "injection"],
    "keywords": ["exception", "error", "security", "sql", "table", "operation"],
    "last_modified": "2026-02-16T18:00:00Z",
}
# ============================================================================
