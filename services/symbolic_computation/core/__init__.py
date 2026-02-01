"""
SymPy Symbolic Computation Core Module
======================================

Core computation modules for expression evaluation, code generation,
optimization, caching, metrics, and validation.

Version: 6.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "6.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "symbolic_computation",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from services.symbolic_computation.core.cache_manager import CacheManager
from services.symbolic_computation.core.code_generator import CodeGenerator
from services.symbolic_computation.core.expression_evaluator import ExpressionEvaluator
from services.symbolic_computation.core.metrics import MetricsCollector
from services.symbolic_computation.core.models import (
    BackendType,
    CodeGenRequest,
    CodeGenResult,
    CodeLanguage,
    ComputationRequest,
    ComputationResult,
    HealthStatus,
    ValidationResult,
)
from services.symbolic_computation.core.optimizer import Optimizer
from services.symbolic_computation.core.validator import ExpressionValidator

__all__ = [
    "BackendType",
    "CacheManager",
    "CodeGenRequest",
    "CodeGenResult",
    "CodeGenerator",
    "CodeLanguage",
    "ComputationRequest",
    "ComputationResult",
    "ExpressionEvaluator",
    "ExpressionValidator",
    "HealthStatus",
    "MetricsCollector",
    "Optimizer",
    "ValidationResult",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-042",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "metrics", "operations", "symbolic-computation", "utility"],
    "keywords": ["computation", "core", "module"],
    "business_value": "Utility module for   init  ",
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
