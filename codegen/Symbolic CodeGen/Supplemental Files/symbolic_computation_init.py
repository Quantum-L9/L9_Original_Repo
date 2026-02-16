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
    "component_name": "Symbolic Computation Init",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-01T13:15:00Z",
    "updated_at": "2026-01-15T15:48:34Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "symbolic_computation_init",
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

from .core import (
    SymbolicComputation,
    ExpressionEvaluator,
    CodeGenerator,
)
from .models import (
    ComputationRequest,
    ComputationResult,
    CodeGenRequest,
    CodeGenResult,
)
from .exceptions import (
    SymbolicComputationError,
    EvaluationError,
    CodeGenerationError,
)

__version__ = "1.0.0"
__all__ = [
    "SymbolicComputation",
    "ExpressionEvaluator",
    "CodeGenerator",
    "ComputationRequest",
    "ComputationResult",
    "CodeGenRequest",
    "CodeGenResult",
    "SymbolicComputationError",
    "EvaluationError",
    "CodeGenerationError",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "current-work", "operations", "utility"],
    "keywords": ["aios", "computation", "module", "symbolic"],
    "business_value": "Provides symbolic-to-numeric conversion, code generation, and high-performance mathematical computation capabilities. Author: AIOS Version: 1.0.0",
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
