# ============================================================================
__dora_meta__ = {
    "component_name": "Lexer",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-08T13:58:11Z",
    "updated_at": "2026-01-08T13:58:28Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "lexer",
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

import re


def extract_claims(text: str) -> list[str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # sentence-level segmentation
    claims = []
    for line in lines:
        claims.extend(re.split(r"[.;]\s+", line))

    return [c.strip() for c in claims if len(c.strip()) > 8]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["code-generation", "foundation", "utility"],
    "keywords": ["claims", "extract", "lexer"],
    "business_value": "Utility module for lexer",
    "last_modified": "2026-01-08T13:58:28Z",
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
