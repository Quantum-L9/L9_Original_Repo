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

from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Lazy import to avoid circular dependencies
_research_agent = None


def _get_research_agent():
    """Lazy-load ResearchAgent singleton."""
    global _research_agent
    if _research_agent is None:
        try:
            from agents.research_agent import create_research_agent

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
# ============================================================================


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
# ============================================================================

RESEARCH_TOOL_EXECUTORS = {
    "research_agent_synthesize": research_agent_synthesize,
    "research_agent_discover": research_agent_discover,
    "research_agent_generate_spec": research_agent_generate_spec,
}


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "research_agent_synthesize",
    "research_agent_discover",
    "research_agent_generate_spec",
    "RESEARCH_TOOL_EXECUTORS",
]
