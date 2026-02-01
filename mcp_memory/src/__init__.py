"""
L9 MCP Memory Server.

Semantic memory service for Cursor IDE integration.
Provides MCP (Model Context Protocol) tools for saving, querying,
and managing context memories via OpenAI embeddings + pgvector.

Created: 2025-12-27
Modified: 2026-01-01
Author: L9 Team
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-11T18:13:39Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "__init__",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

try:
    # Relative import (when imported as mcp_memory.src)
    from .rate_limiter import RateLimiter
except ImportError:
    # Absolute import (when running inside mcp_memory directory)
    from src.rate_limiter import RateLimiter

__version__ = "1.0.0"

__all__ = ["RateLimiter"]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "integration", "mcp-integration", "service"],
    "keywords": ["memory", "service"],
    "business_value": "Provides MCP (Model Context Protocol) tools for saving, querying, and managing context memories via OpenAI embeddings + pgvector. Created: 2025-12-27 Modified: 2026-01-01 Author: L9 Team",
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
