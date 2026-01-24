"""
L9 Research Agent Tools
=======================

Tool executors that wrap ResearchAgent for use by L-CTO Research mode.
Enables L-CTO to call ResearchAgent for external web research via Perplexity.

Tools:
- research_agent_synthesize: Fast multi-perspective synthesis (~10 min)
- research_agent_discover: Deep 5-stage research (hours)
- research_agent_generate_spec: Module-Spec-v2.4 YAML generation

Version: 1.0.0
GMP: wire_research_lcto_integration
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Tools",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "research_tools",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["runtime.l_tools"],
    },
}
# ============================================================================

from typing import Any, Optional

import structlog

from runtime.tool_registry import register_tool

logger = structlog.get_logger(__name__)

# Lazy import to avoid circular dependencies
_research_agent = None


def _get_research_agent():
    """Load ResearchAgent singleton on first access."""
    global _research_agent
    if _research_agent is None:
        try:
            from agents.research_agent_impl import create_research_agent

            _research_agent = create_research_agent()
            logger.info(
                "research_tools: ResearchAgent initialized",
                agent_id=_research_agent.agent_id,
            )
        except ValueError as e:
            logger.warning(
                f"research_tools: ResearchAgent unavailable (missing API key): {e}"
            )
            return None
        except Exception as e:
            logger.error(f"research_tools: Failed to initialize ResearchAgent: {e}")
            return None
    return _research_agent


# ============================================================================
# Tool Executors


@register_tool(category="research", priority=10, description="run_research_query tool")
@register_tool(category="research", priority=10, description="run_research_query tool")
async def run_research_query(
    query: str,
    user_id: str = "l_agent",
    thread_id: Optional[str] = None,
    **kwargs,
) -> dict[str, Any]:
    """
    Execute a research query through the full LangGraph pipeline.

    This is the PRIMARY research tool that triggers:
    1. PlannerAgent → Decompose query into research steps
    2. ResearcherAgent → Gather evidence (Perplexity web search)
    3. MergerAgent → Synthesize findings
    4. CriticAgent → Evaluate quality (may trigger retry)
    5. FinalizerAgent → Package output
    6. GraphPersistence → Store findings as Neo4j nodes

    Use this tool when you need to:
    - Research external topics (web search)
    - Gather evidence for decisions
    - Answer questions requiring current information
    - Build knowledge for architecture decisions

    Args:
        query: Research question (1-5000 chars)
        user_id: User identifier for tracking (default: l_agent)
        thread_id: Optional thread ID for correlation

    Returns:
        Dict with research results:
        - success: bool
        - thread_id: str (for follow-up)
        - summary: str (synthesized findings)
        - sources: list[str] (URLs cited)
        - evidence_count: int
        - quality_score: float (0-1)
        - feedback: str (critic feedback)
        - error: str (if failed)

    Example:
        result = await run_research_query(
            query="What are the latest advances in LLM memory architectures?"
        )
        # result["summary"] contains the synthesized findings
    """
    try:
        from services.research import run_research

        logger.info("run_research_query", query=query[:50], user_id=user_id)

        result = await run_research(
            query=query,
            user_id=user_id,
            thread_id=thread_id,
        )

        return {
            "success": True,
            "thread_id": result.get("thread_id", ""),
            "summary": result.get("summary", ""),
            "sources": result.get("sources", []),
            "evidence_count": result.get("evidence_count", 0),
            "quality_score": result.get("quality_score", 0.0),
            "feedback": result.get("feedback", ""),
        }
    except ImportError as e:
        logger.error(
            "run_research_query: services.research not available", error=str(e)
        )
        return {
            "success": False,
            "error": f"Research service not available: {e}",
        }
    except Exception as e:
        logger.error("run_research_query failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@register_tool(
    category="research", priority=10, description="research_agent_synthesize tool"
)
@register_tool(
    category="research", priority=10, description="research_agent_synthesize tool"
)
async def research_agent_synthesize(
    topic: str,
    context: Optional[dict[str, Any]] = None,
    **kwargs,
) -> dict[str, Any]:
    """
    Execute fast multi-perspective synthesis via ResearchAgent.

    Runs 5 parallel prompt variations and synthesizes consensus:
    - v1_pragmatic: Implementation-first engineering
    - v2_research: Theory-first academic
    - v3_systems: DevOps/systems integration
    - v4_agents: Autonomous agent integration
    - v5_multimodal: Cross-modality specifics

    Args:
        topic: Research topic to synthesize
        context: Optional additional context

    Returns:
        Dict with synthesis results including:
        - success: bool
        - timestamp: str
        - total_variations: int
        - consensus_patterns: dict
        - unique_insights: list
        - recommended_architecture: dict
        - implementation_roadmap: list
        - confidence_scores: dict
        - error: str (if failed)
    """
    agent = _get_research_agent()
    if agent is None:
        return {
            "success": False,
            "error": "ResearchAgent not available (PERPLEXITY_API_KEY not set)",
        }

    try:
        logger.info("research_agent_synthesize", topic=topic)
        result = await agent.synthesize(topic=topic, context=context)

        return {
            "success": True,
            "timestamp": result.timestamp,
            "total_variations": result.total_variations,
            "consensus_patterns": result.consensus_patterns,
            "unique_insights": result.unique_insights,
            "recommended_architecture": result.recommended_architecture,
            "implementation_roadmap": result.implementation_roadmap,
            "confidence_scores": result.confidence_scores,
        }
    except Exception as e:
        logger.error("research_agent_synthesize failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@register_tool(
    category="research", priority=10, description="research_agent_discover tool"
)
@register_tool(
    category="research", priority=10, description="research_agent_discover tool"
)
async def research_agent_discover(
    topic: str,
    domain: str = "general",
    stages: Optional[list[str]] = None,
    **kwargs,
) -> dict[str, Any]:
    """
    Execute deep 5-stage academic research via ResearchAgent.

    Stages:
    1. landscape: Map research landscape (3-5 hours)
    2. deep_dive: Vertical deep-dives on themes (4-6 hours)
    3. comparative: Compare leading approaches (3-5 hours)
    4. gaps: Identify research gaps (3-4 hours)
    5. hypotheses: Generate testable hypotheses (2-3 hours)

    WARNING: This is a long-running operation (15-25 hours total).
    Consider running specific stages only.

    Args:
        topic: Research topic
        domain: Research domain (default: general)
        stages: Specific stages to run (default: all 5)

    Returns:
        Dict with discovery results including:
        - success: bool
        - topic: str
        - domain: str
        - stages_completed: list
        - total_sources: int
        - summary: str
        - hypotheses_count: int
        - gaps_count: int
        - error: str (if failed)
    """
    agent = _get_research_agent()
    if agent is None:
        return {
            "success": False,
            "error": "ResearchAgent not available (PERPLEXITY_API_KEY not set)",
        }

    try:
        logger.info(
            "research_agent_discover",
            topic=topic,
            domain=domain,
            stages=stages,
        )
        result = await agent.discover(topic=topic, domain=domain, stages=stages)

        return {
            "success": True,
            "topic": result.topic,
            "domain": result.domain,
            "stages_completed": result.stages_completed,
            "total_sources": result.total_sources,
            "summary": result.summary,
            "hypotheses_count": len(result.hypotheses),
            "gaps_count": len(result.gaps),
        }
    except Exception as e:
        logger.error("research_agent_discover failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@register_tool(
    category="research", priority=10, description="research_agent_generate_spec tool"
)
@register_tool(
    category="research", priority=10, description="research_agent_generate_spec tool"
)
async def research_agent_generate_spec(
    topic: str,
    description: Optional[str] = None,
    run_synthesis_first: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """
    Generate Module-Spec-v2.4 YAML via ResearchAgent.

    If run_synthesis_first=True (default), runs synthesis first
    to inform the spec generation with research insights.

    Args:
        topic: Module topic
        description: Module description
        run_synthesis_first: Whether to run synthesis before spec gen

    Returns:
        Dict with spec generation results including:
        - success: bool
        - module_id: str
        - output_path: str
        - is_valid: bool
        - validation_errors: list
        - error: str (if failed)
    """
    agent = _get_research_agent()
    if agent is None:
        return {
            "success": False,
            "error": "ResearchAgent not available (PERPLEXITY_API_KEY not set)",
        }

    try:
        logger.info(
            "research_agent_generate_spec",
            topic=topic,
            run_synthesis_first=run_synthesis_first,
        )

        synthesis = None
        if run_synthesis_first:
            synthesis = await agent.synthesize(topic=topic)

        result = await agent.generate_spec(
            synthesis=synthesis,
            topic=topic,
            description=description,
        )

        return {
            "success": True,
            "module_id": result.module_id,
            "output_path": str(result.output_path),
            "is_valid": result.is_valid,
            "validation_errors": result.validation_errors,
        }
    except Exception as e:
        logger.error("research_agent_generate_spec failed", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Tool Executor Registry (for runtime.l_tools integration)

RESEARCH_TOOL_EXECUTORS = {
    "run_research_query": run_research_query,  # PRIMARY: Full LangGraph pipeline
    "research_agent_synthesize": research_agent_synthesize,
    "research_agent_discover": research_agent_discover,
    "research_agent_generate_spec": research_agent_generate_spec,
}

# ============================================================================
# Public API

__all__ = [
    "run_research_query",
    "research_agent_synthesize",
    "research_agent_discover",
    "research_agent_generate_spec",
    "RESEARCH_TOOL_EXECUTORS",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.research_agent"],
    "tags": [
        "api",
        "async",
        "engine",
        "foundation",
        "logging",
        "testing",
        "tool-registry",
    ],
    "keywords": [
        "agent",
        "discover",
        "generate",
        "module",
        "research",
        "researchagent",
        "spec",
        "synthesize",
    ],
    "business_value": "Utility module for research tools",
    "last_modified": "2026-01-17T23:47:56Z",
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
