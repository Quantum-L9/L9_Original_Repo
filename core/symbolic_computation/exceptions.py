"""
Custom exceptions for symbolic computation module.
"""


class SymbolicComputationError(Exception):
    """Base exception for symbolic computation errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EvaluationError(SymbolicComputationError):
    """Exception raised when expression evaluation fails."""

    pass


class CodeGenerationError(SymbolicComputationError):
    """Exception raised when code generation fails."""

    pass


class ValidationError(SymbolicComputationError):
    """Exception raised when input validation fails."""

    pass


class CacheError(SymbolicComputationError):
    """Exception raised when cache operations fail."""

    pass
