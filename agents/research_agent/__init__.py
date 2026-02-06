"""
L9 Research Agent SDK
=====================

Simplified interface to L9's research infrastructure.

This module provides:
- Easy-to-use research functions for Cursor/scripts
- Superprompt generation for Perplexity workflows
- CLI commands for research tasks

Architecture:
- This is an SDK over `services.research/` (production implementation)
- Does NOT duplicate LangGraph logic, memory integration, etc.
- Provides simpler entry points for common use cases

Usage:
    from agents.research_agent import run_research, generate_superprompt

    # Run full research pipeline
    result = await run_research("What are LLM memory architectures?")

    # Generate superprompt for Perplexity
    prompt = generate_superprompt("agents/cursor", template="readme")

See Also:
- `services/research/` - Full implementation
- `orchestrators/research_swarm/` - Concurrent orchestration
- `codegen/README-CodeGen/` - README generation templates
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T17:12:30Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "__init__",
    "type": "utility",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# SDK functions (simple interface)
from agents.research_agent.research_sdk import (
    extract_facts,
    generate_superprompt,
    run_quick_research,
    run_research,
)

# Re-export from services.research for advanced use
from services.research import (
    Evidence,
    ResearchGraphRuntime,
    ResearchGraphState,
    ResearchMemoryAdapter,
    ResearchStep,
    build_research_graph,
    create_initial_state,
    get_memory_adapter,
    get_runtime,
    init_runtime,
    shutdown_runtime,
)
from services.research import (
    run_research as run_research_full,  # State; Memory; Graph; Runtime
)

__all__ = [
    "Evidence",
    "ResearchGraphRuntime",
    # Advanced (from services.research)
    "ResearchGraphState",
    "ResearchMemoryAdapter",
    "ResearchStep",
    "build_research_graph",
    "create_initial_state",
    "extract_facts",
    "generate_superprompt",
    "get_memory_adapter",
    "get_runtime",
    "init_runtime",
    "run_quick_research",
    # SDK (simple)
    "run_research",
    "run_research_full",
    "shutdown_runtime",
]

__version__ = "1.0.0"
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-023",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.research_agent.research_sdk"],
    "tags": ["agent-execution", "intelligence", "utility"],
    "keywords": [
        "agent",
        "agents",
        "codegen",
        "cursor",
        "sdk",
        "full",
        "generation",
        "implementation",
    ],
    "business_value": "Easy-to-use research functions for Cursor/scripts Superprompt generation for Perplexity workflows CLI commands for research tasks This is an SDK over `services.research/` (production implementation)",
    "last_modified": "2026-01-31T22:21:54Z",
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
