# ============================================================================
__dora_meta__ = {
    "component_name": "Enforcement and rejection recording.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "security",
    "domain": "governance",
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

# governance/__init__.py
"""
Governance Module - Enforcement and rejection recording.

Provides tools for recording governance violations, test failures,
and other negative memory (patterns to NOT repeat).
"""

from governance.rejection_recorder import (
    record_governance_violation,
    record_rejection,
    record_test_failure,
)

__all__ = [
    "record_governance_violation",
    "record_rejection",
    "record_test_failure",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "GOV-SECU-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["governance", "security", "testing", "utility"],
    "keywords": ["enforcement", "recording.", "rejection"],
    "business_value": "Provides tools for recording governance violations, test failures, and other negative memory (patterns to NOT repeat).",
    "last_modified": "2026-01-31T22:21:56Z",
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
