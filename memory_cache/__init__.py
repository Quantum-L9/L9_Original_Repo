# ============================================================================
__dora_meta__ = {
    "component_name": "Ephemeral working memory for Cursor sessions.",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T22:45:42Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "memory_cache",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

# memory_cache/__init__.py
"""
Memory Cache Module - Ephemeral working memory for Cursor sessions.

Provides TTL-based, Redis-backed working memory that expires naturally.
No auto-promotion to long-term memory without explicit signals.
"""

from memory_cache.cursor_working_memory_service import (
    CursorWorkingMemoryService,
    MemoryEventType,
    WorkingMemorySnapshot,
)

__all__ = [
    "CursorWorkingMemoryService",
    "MemoryEventType",
    "WorkingMemorySnapshot",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["caching", "event-driven", "memory-cache", "operations", "utility"],
    "keywords": ["cursor", "ephemeral", "memory", "sessions.", "working"],
    "business_value": "Provides TTL-based, Redis-backed working memory that expires naturally. No auto-promotion to long-term memory without explicit signals.",
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
