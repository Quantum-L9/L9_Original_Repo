"""
Custom exceptions for symbolic computation module.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Exceptions",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "exceptions",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


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


class CodeGenerationError(SymbolicComputationError):
    """Exception raised when code generation fails."""


class ValidationError(SymbolicComputationError):
    """Exception raised when input validation fails."""


class CacheError(SymbolicComputationError):
    """Exception raised when cache operations fail."""


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-054",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "error-handling", "exception", "foundation", "messaging"],
    "keywords": [
        "cache",
        "computation",
        "evaluation",
        "exceptions",
        "generation",
        "module",
        "symbolic",
        "validation",
    ],
    "business_value": "Provides exceptions components including SymbolicComputationError, EvaluationError, CodeGenerationError",
    "last_modified": "2026-01-17T23:47:56Z",
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
