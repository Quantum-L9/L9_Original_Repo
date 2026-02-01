"""L9 Memory Substrate - Semantic Storage & Retrieval.

Bounded Context: Memory Substrate
Domain: Semantic/vector search, graph storage, working memory.
Owner: L (CTO)

Memory Substrate is responsible for:
  1. Vector embeddings (OpenAI/local models)
  2. Semantic search over knowledge bases
  3. Temporal memory operations (decay, TTL)
  4. Graph relationships (Neo4j integration)
  5. Memory lifecycle (save, search, delete, compound)

Memory Substrate MUST implement:
  - SubstrateService interface
  - Adapter pattern for embedding providers
  - Abstract repository layer (no direct SQL)

Memory Substrate MUST NOT:
  - Enforce safety policies (Safety does that)
  - Implement business logic (Orchestrator does that)
  - Manage user auth (Kernel/Safety do that)

Memory operations flow through PacketEnvelope (kernel.protocol).
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Semantic Storage & Retrieval.",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-25T05:32:53Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "integration",
    "domain": "mcp_integration",
    "module_name": "__init__",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from memory_substrate.repository import AbstractMemoryRepository
from memory_substrate.service import SubstrateConfig, SubstrateService

__all__ = [
    "AbstractMemoryRepository",
    "SubstrateConfig",
    "SubstrateService",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MCP-INTE-011",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "integration", "mcp-integration"],
    "keywords": [
        "does",
        "graph",
        "implement",
        "kernel",
        "memory",
        "must",
        "operations",
        "orchestrator",
    ],
    "business_value": "Utility module for   init  ",
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
