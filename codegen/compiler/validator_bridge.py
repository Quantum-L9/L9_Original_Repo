# ============================================================================
__dora_meta__ = {
    "component_name": "Validator Bridge",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-08T14:06:12Z",
    "updated_at": "2026-01-13T13:44:24Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "validator_bridge",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# codegen/compiler/validator_bridge.py
"""
Validator bridge for transcript compiler outputs.

Validates all generated artifacts and enforces hard fail conditions
for critical invariants.
"""

from .schemas import validate_schema


def validate_outputs(artifacts: dict):
    for name, artifact in artifacts.items():
        validate_schema(name, artifact)

    # HARD FAIL CONDITIONS
    for inv in artifacts.get("typed_invariants.yaml", {}).get("typed_invariants", []):
        if not inv["enforced_by"]:
            raise RuntimeError(f"Invariant {inv['id']} has no enforcement target")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "code-generation", "foundation"],
    "keywords": ["bridge", "outputs", "validate", "validator"],
    "business_value": "Utility module for validator bridge",
    "last_modified": "2026-01-13T13:44:24Z",
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
