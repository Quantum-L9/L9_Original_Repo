# ============================================================================
__dora_meta__ = {
    "component_name": "Schemas",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-13T13:44:10Z",
    "updated_at": "2026-01-13T13:44:10Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "schemas",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# codegen/compiler/schemas.py
"""
Schema validation for transcript compiler outputs.

Validates the structure of generated YAML artifacts:
- decisions.yaml
- ial_candidates.yaml
- typed_invariants.yaml
- work_packets.yaml
"""

from typing import Any

# Expected schema structure for each artifact type
ARTIFACT_SCHEMAS = {
    "decisions.yaml": {"decisions": list},
    "ial_candidates.yaml": {"ial_candidates": list},
    "typed_invariants.yaml": {"typed_invariants": list},
    "work_packets.yaml": {"work_packets": list},
}


def validate_schema(artifact_name: str, artifact: dict[str, Any]) -> None:
    """
    Validate artifact structure against expected schema.

    Args:
        artifact_name: Name of the artifact (e.g., "decisions.yaml")
        artifact: The artifact dictionary to validate

    Raises:
        ValueError: If artifact structure is invalid
    """
    if not isinstance(artifact, dict):
        raise ValueError(
            f"{artifact_name}: Expected dict, got {type(artifact).__name__}"
        )

    expected = ARTIFACT_SCHEMAS.get(artifact_name)
    if expected is None:
        # Unknown artifact type - allow it
        return

    for key, expected_type in expected.items():
        if key not in artifact:
            raise ValueError(f"{artifact_name}: Missing required key '{key}'")
        if not isinstance(artifact[key], expected_type):
            raise ValueError(
                f"{artifact_name}: Key '{key}' expected {expected_type.__name__}, "
                f"got {type(artifact[key]).__name__}"
            )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["code-generation", "foundation", "schema"],
    "keywords": ["schema", "schemas", "validate"],
    "business_value": "decisions.yaml ial_candidates.yaml typed_invariants.yaml work_packets.yaml",
    "last_modified": "2026-01-13T13:44:10Z",
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
