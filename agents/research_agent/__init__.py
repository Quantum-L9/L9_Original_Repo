"""
L9 Research Agent Facade
========================

Simplified interface to L9's research infrastructure.

This module provides:
- Easy-to-use research functions for Cursor/scripts
- Superprompt generation for Perplexity workflows
- CLI commands for research tasks

Architecture:
- This is a FACADE over `services.research/` (production implementation)
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

# Facade functions (simple interface)
from agents.research_agent.research_facade import (extract_facts,
                                                   generate_superprompt,
                                                   run_quick_research,
                                                   run_research)
# Re-export from services.research for advanced use
from services.research import (Evidence, ResearchGraphRuntime,
                               ResearchGraphState, ResearchMemoryAdapter,
                               ResearchStep, build_research_graph,
                               create_initial_state, get_memory_adapter,
                               get_runtime, init_runtime)
from services.research import \
    run_research as run_research_full  # State; Memory; Graph; Runtime
from services.research import shutdown_runtime

__all__ = [
    # Facade (simple)
    "run_research",
    "run_quick_research",
    "generate_superprompt",
    "extract_facts",
    # Advanced (from services.research)
    "ResearchGraphState",
    "ResearchStep",
    "Evidence",
    "create_initial_state",
    "ResearchMemoryAdapter",
    "get_memory_adapter",
    "build_research_graph",
    "run_research_full",
    "ResearchGraphRuntime",
    "get_runtime",
    "init_runtime",
    "shutdown_runtime",
]

__version__ = "1.0.0"
