"""
L9 Extraction Suite - Extractors Module

Contains all extraction implementations:
- CodeExtractor: Extracts code files from chat logs
- MemoryExtractor: Extracts structured memory for Supabase
- AgentConfigExtractor: Extracts preferences, SOPs, roles
- ModuleSchemaExtractor: Extracts L9 module definitions
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Extractors Module",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:48Z",
    "layer": "learning",
    "domain": "memory_substrate",
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

from .agent_config_extractor import AgentConfigExtractor
from .code_extractor import CodeExtractor
from .memory_extractor import MemoryExtractor
from .module_schema_extractor import ModuleSchemaExtractor

__all__ = [
    "AgentConfigExtractor",
    "CodeExtractor",
    "MemoryExtractor",
    "ModuleSchemaExtractor",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-074",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["learning", "memory-substrate", "utility"],
    "keywords": ["extraction", "extractors", "extracts", "memory", "module"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:48Z",
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
