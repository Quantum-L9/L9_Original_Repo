"""
L9 Research Department - Tools Module
Version: 2.0.0

In-memory tool registry and wrappers for research tools.
Includes production Perplexity client with best practices codified.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Tools Module",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "__init__",
    "type": "adapter",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.tools.base_registry import (
    ToolMetadata,
    ToolRegistry,
    ToolType,
    get_tool_registry,
)
from services.research.tools.perplexity_client import (
    PerplexityClient,
    PerplexityModel,
    PerplexityRequest,
    PerplexityResponse,
    SearchContextSize,
    get_perplexity_client,
)
from services.research.tools.tool_resolver import ToolResolver, get_tool_resolver
from services.research.tools.tool_wrappers import (
    BaseTool,
    HTTPTool,
    MockSearchTool,
    PerplexityTool,
)

__all__ = [
    # Wrappers
    "BaseTool",
    "HTTPTool",
    "MockSearchTool",
    # Perplexity Client (production)
    "PerplexityClient",
    "PerplexityModel",
    "PerplexityRequest",
    "PerplexityResponse",
    "PerplexityTool",
    "SearchContextSize",
    "ToolMetadata",
    "ToolRegistry",
    # Resolver
    "ToolResolver",
    # Registry
    "ToolType",
    "get_perplexity_client",
    "get_tool_registry",
    "get_tool_resolver",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-026",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.tools.base_registry"],
    "tags": ["adapter", "mocking", "operations", "research-services"],
    "keywords": ["memory", "module", "research", "tools"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:22:00Z",
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
