"""
L9 Core - Resilience Utilities
==============================

Retry logic, backoff strategies, and fault tolerance utilities.
Includes Protocol + Mixin for DIP-based resilience (ADR-0014).

Version: 1.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Resilience Utilities",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "core",
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

from core.resilience.mixin import ResilienceMixin
from core.resilience.protocols import ResilientService
from core.resilience.retry import AsyncRetryConfig, RetryExhaustedError, async_retry

__all__ = [
    "AsyncRetryConfig",
    "ResilienceMixin",
    # DIP Protocol + Mixin (ADR-0014)
    "ResilientService",
    "RetryExhaustedError",
    # Retry utilities
    "async_retry",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-165",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.resilience.mixin",
        "core.resilience.protocols",
        "core.resilience.retry",
    ],
    "tags": ["core", "foundation", "utility"],
    "keywords": ["resilience", "utilities"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:47Z",
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
