"""
L9 Config Schemas Package
Version: 1.0.0

Configuration schemas for L9 governance, ADRs, and other structured data.

SCHEMAS
=======
- adr_schema.yaml: Canonical format for Architecture Decision Records
"""

from pathlib import Path

__dora_meta__ = {
    "component_name": "Config Schemas",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T00:00:00Z",
    "updated_at": "2026-01-20T00:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "config.schemas",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.governance.session_startup"],
    },
}

SCHEMAS_DIR = Path(__file__).parent


def get_adr_schema_path() -> Path:
    """Get path to ADR schema YAML."""
    return SCHEMAS_DIR / "adr_schema.yaml"


__all__ = ["SCHEMAS_DIR", "get_adr_schema_path"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-011",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["configuration", "filesystem", "foundation", "utility"],
    "keywords": ["adr", "governance", "schema", "schemas"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:50Z",
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
