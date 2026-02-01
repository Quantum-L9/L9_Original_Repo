"""
Symbolic Computation Module for AIOS

Production-ready SymPy utilities integration for semi-autonomous agents.
Provides symbolic-to-numeric conversion, code generation, and high-performance
mathematical computation capabilities.

Author: AIOS
Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .computation import CodeGenerator, ExpressionEvaluator, SymbolicComputation
from .exceptions import CodeGenerationError, EvaluationError, SymbolicComputationError
from .models import (
    BackendType,
    CodeGenRequest,
    CodeGenResult,
    CodeLanguage,
    ComputationRequest,
    ComputationResult,
)

__version__ = "1.0.0"
__all__ = [
    "BackendType",
    "CodeGenRequest",
    "CodeGenResult",
    "CodeGenerationError",
    "CodeGenerator",
    "CodeLanguage",
    "ComputationRequest",
    "ComputationResult",
    "EvaluationError",
    "ExpressionEvaluator",
    "SymbolicComputation",
    "SymbolicComputationError",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-020",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "operations", "symbolic-computation", "utility"],
    "keywords": ["aios", "computation", "module", "symbolic"],
    "business_value": "Provides symbolic-to-numeric conversion, code generation, and high-performance mathematical computation capabilities. Author: AIOS Version: 1.0.0",
    "last_modified": "2026-01-31T22:22:00Z",
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
