"""
Custom exceptions for symbolic computation module.
"""


# ============================================================================
__dora_meta__ = {
    "component_name": "Symbolic Computation Exceptions",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-01T13:15:17Z",
    "updated_at": "2026-01-15T15:48:34Z",
    "layer": "operations",
    "domain": "error_handling",
    "module_name": "symbolic_computation_exceptions",
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-031",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "error-handling", "exception", "messaging", "operations"],
    "keywords": ["cache", "computation", "evaluation", "exceptions", "generation", "module", "symbolic", "validation"],
    "business_value": "Provides symbolic computation exceptions components including SymbolicComputationError, EvaluationError, CodeGenerationError",
    "last_modified": "2026-01-15T15:48:34Z",
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
