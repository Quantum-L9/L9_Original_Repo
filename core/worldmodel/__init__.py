"""
L9 Core - World Model
======================

World model population and reasoning for L9 operational entities.

Provides:
- L9-specific entity schemas (agents, tools, infrastructure)
- Relationship types for entity connections
- Insight emission from agent events
- Query API for world model access

Version: 1.0.0 (GMP-18)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "World Model",
    "module_version": "1.0.0 (GMP-18)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-31T22:21:47Z",
    "layer": "foundation",
    "domain": "world_model",
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

from core.worldmodel.insight_emitter import InsightEmitter
from core.worldmodel.l9_schema import (
    L9Agent,
    L9ExternalSystem,
    L9Infrastructure,
    L9MemorySegment,
    L9Relationship,
    L9RelationshipType,
    L9Repository,
    L9Tool,
)
from core.worldmodel.service import WorldModelService

__all__ = [
    # Services
    "InsightEmitter",
    # Entity types
    "L9Agent",
    "L9ExternalSystem",
    "L9Infrastructure",
    "L9MemorySegment",
    # Relationships
    "L9Relationship",
    "L9RelationshipType",
    "L9Repository",
    "L9Tool",
    "WorldModelService",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-161",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.worldmodel.insight_emitter",
        "core.worldmodel.l9_schema",
        "core.worldmodel.service",
    ],
    "tags": ["api", "event-driven", "foundation", "utility", "world-model"],
    "keywords": ["agent", "entity", "model", "world"],
    "business_value": "L9-specific entity schemas (agents, tools, infrastructure) Relationship types for entity connections Insight emission from agent events Query API for world model access Version: 1.0.0 (GMP-18)",
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
