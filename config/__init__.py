"""L9 Configuration Module."""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "foundation",
    "domain": "configuration",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from config.ai_eval_settings import (
    AIEvalSettings,
    get_ai_eval_settings,
    reset_ai_eval_settings,
)
from config.memory_substrate_settings import (
    MemorySubstrateSettings,
    get_settings,
    reset_settings,
)
from config.research_settings import (
    ResearchSettings,
    get_research_settings,
    reset_research_settings,
)
from config.settings import (
    IntegrationSettings,
    get_integration_settings,
    reset_integration_settings,
    settings,
)

__all__ = [
    # AI Eval Settings
    "AIEvalSettings",
    # Integration Settings
    "IntegrationSettings",
    # Memory Substrate Settings
    "MemorySubstrateSettings",
    # Research Settings
    "ResearchSettings",
    "get_ai_eval_settings",
    "get_integration_settings",
    "get_research_settings",
    "get_settings",
    "reset_ai_eval_settings",
    "reset_integration_settings",
    "reset_research_settings",
    "reset_settings",
    "settings",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-003",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["configuration", "foundation", "utility"],
    "keywords": ["module"],
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
