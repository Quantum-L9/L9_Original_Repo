"""
L9 Research Factory - Research Graph
Version: 1.1.0

LangGraph DAG for multi-agent research orchestration.
Includes Memory Substrate integration via store_insights node.

Flow:
  START → planning_node → research_node → merge_node → critic_node →
         ↳ (if retry) → planning_node
         ↳ (if approved) → finalize_node → store_insights → END
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Graph",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "research_graph",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "services.research.__init__",
            "services.research.graph_runtime",
            "tests.test_research_graph",
        ],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, START, END

from services.research.graph_state import (
    ResearchGraphState,
    Evidence,
    create_initial_state,
)
from services.research.agents import PlannerAgent, ResearcherAgent, CriticAgent
from services.research.memory_adapter import get_memory_adapter
from services.research.tools import get_tool_registry
from services.research.insight_extractor import InsightExtractorAgent

# Memory client for substrate writes
from clients.memory_client import get_memory_client, PacketWriteResult

logger = structlog.get_logger(__name__)

# =============================================================================
# Node Implementations
# =============================================================================


async def planning_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Planning node - Decompose query into research steps.

    Uses PlannerAgent to create a structured research plan.
    Persists plan to memory substrate.
    """
    logger.info(f"Planning node: thread={state.get('thread_id')}")

    try:
        # Initialize planner
        planner = PlannerAgent()

        # Refine the goal
        refined_goal = await planner.refine_goal(state["original_query"])

        # Create plan
        plan = await planner.run(refined_goal)

        # Log to memory substrate
        adapter = get_memory_adapter()
        await adapter.log_memory_event(
            agent_id="research_planner",
            event_type="planning_completed",
            content={
                "query": state["original_query"],
                "refined_goal": refined_goal,
                "plan_steps": len(plan),
            },
        )

        return {
            **state,
            "refined_goal": refined_goal,
            "plan": plan,
            "current_step_idx": 0,
        }

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        return {
            **state,
            "errors": state.get("errors", []) + [f"Planning failed: {str(e)}"],
        }


async def research_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Research node - Execute research steps and gather evidence.

    Iterates through plan steps, calling ResearcherAgent for each.
    Accumulates evidence for synthesis.
    """
    logger.info(f"Research node: thread={state.get('thread_id')}")

    try:
        researcher = ResearcherAgent()

        # Set tool registry
        registry = get_tool_registry()
        researcher.set_tool_registry(registry)

        plan = state.get("plan", [])
        evidence: list[Evidence] = list(state.get("evidence", []))

        # Execute research steps
        for i, step in enumerate(plan):
            if step.get("agent") == "researcher":
                logger.info(
                    f"Executing research step {i + 1}/{len(plan)}: {step.get('step_id')}"
                )

                # Update step status
                step["status"] = "in_progress"

                # Execute step
                new_evidence = await researcher.run(
                    step=step,
                    previous_evidence=evidence,
                )

                # Mark complete
                step["status"] = "completed"
                step["result"] = dict(new_evidence)

                evidence.append(new_evidence)

        # Log to memory substrate
        adapter = get_memory_adapter()
        await adapter.log_memory_event(
            agent_id="research_worker",
            event_type="research_completed",
            content={
                "steps_executed": len(
                    [s for s in plan if s.get("status") == "completed"]
                ),
                "evidence_gathered": len(evidence),
            },
        )

        return {
            **state,
            "plan": plan,
            "evidence": evidence,
            "sources": list(
                set(
                    src
                    for ev in evidence
                    for src in ev.get("metadata", {}).get("sources", [])
                )
            ),
        }

    except Exception as e:
        logger.error(f"Research failed: {e}")
        return {
            **state,
            "errors": state.get("errors", []) + [f"Research failed: {str(e)}"],
        }


async def merge_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Merge node - Synthesize evidence into summary.

    Combines all gathered evidence into a coherent summary.
    """
    logger.info(f"Merge node: thread={state.get('thread_id')}")

    try:
        researcher = ResearcherAgent()

        evidence = state.get("evidence", [])
        query = state.get("refined_goal", state.get("original_query", ""))

        # Synthesize evidence
        summary = await researcher.synthesize_evidence(evidence, query)

        return {
            **state,
            "final_summary": summary,
        }

    except Exception as e:
        logger.error(f"Merge failed: {e}")
        return {
            **state,
            "final_summary": "Failed to synthesize evidence",
            "errors": state.get("errors", []) + [f"Merge failed: {str(e)}"],
        }


async def critic_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Critic node - Evaluate research quality.

    Uses CriticAgent to score the research and provide feedback.
    Determines whether to approve or request retry.
    """
    logger.info(f"Critic node: thread={state.get('thread_id')}")

    try:
        critic = CriticAgent()

        evaluation = await critic.run(
            query=state.get("refined_goal", state.get("original_query", "")),
            evidence=state.get("evidence", []),
            summary=state.get("final_summary", ""),
        )

        # Log to memory substrate
        adapter = get_memory_adapter()
        await adapter.log_memory_event(
            agent_id="research_critic",
            event_type="evaluation_completed",
            content={
                "score": evaluation["score"],
                "approved": evaluation["approved"],
            },
        )

        return {
            **state,
            "critic_score": evaluation["score"],
            "critic_feedback": evaluation["feedback"],
        }

    except Exception as e:
        logger.error(f"Critic evaluation failed: {e}")
        return {
            **state,
            "critic_score": 0.5,
            "critic_feedback": f"Evaluation failed: {str(e)}",
            "errors": state.get("errors", []) + [f"Critic failed: {str(e)}"],
        }


async def finalize_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Finalize node - Package final output.

    Creates the final output structure and saves checkpoint.
    """
    logger.info(f"Finalize node: thread={state.get('thread_id')}")

    # Build final output
    final_output = {
        "query": state.get("original_query", ""),
        "refined_goal": state.get("refined_goal", ""),
        "summary": state.get("final_summary", ""),
        "sources": state.get("sources", []),
        "evidence_count": len(state.get("evidence", [])),
        "quality_score": state.get("critic_score", 0.0),
        "feedback": state.get("critic_feedback", ""),
        "thread_id": state.get("thread_id", ""),
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Save checkpoint to memory substrate
    try:
        adapter = get_memory_adapter()
        await adapter.save_checkpoint(state)
        await adapter.save_state_as_packet(
            state,
            packet_type="research_result",
            agent_id="research_graph",
        )
    except Exception as e:
        logger.warning(f"Failed to save checkpoint: {e}")

    return {
        **state,
        "final_output": final_output,
    }


async def store_insights_node(state: ResearchGraphState) -> ResearchGraphState:
    """
    Store Insights node - Extract and persist insights to Memory Substrate.

    Uses InsightExtractorAgent to turn final research results into structured insights.
    Each insight is written as a PacketEnvelope v1.0.1 via MemoryClient.

    Packet structure (Memory.yaml v1.0.1):
      - packet_type: "insight"
      - payload: {insight_type, content, evidence_refs, ...}
      - metadata: {schema_version, agent, domain}
      - provenance: {source_agent}
      - confidence: {score, rationale}
    """
    logger.info(f"Store insights node: thread={state.get('thread_id')}")

    stored_insights: list[dict[str, Any]] = []

    try:
        # Extract insights from final output
        extractor = InsightExtractorAgent()
        insights = await extractor.extract_insights(
            query=state.get("original_query", ""),
            summary=state.get("final_summary", ""),
            evidence=state.get("evidence", []),
            quality_score=state.get("critic_score", 0.0),
        )

        if not insights:
            logger.info("No insights extracted")
            return {**state, "stored_insights": []}

        # Get memory client
        memory_client = get_memory_client()

        # Write each insight as a PacketEnvelope
        for insight in insights:
            try:
                result: PacketWriteResult = await memory_client.write_packet(
                    packet_type="insight",
                    payload={
                        "insight_type": insight.get("type", "general"),
                        "content": insight.get("content", ""),
                        "summary": insight.get("summary", ""),
                        "evidence_refs": insight.get("evidence_refs", []),
                        "tags": insight.get("tags", []),
                        "source_query": state.get("original_query", ""),
                        "thread_id": state.get("thread_id", ""),
                    },
                    metadata={
                        "schema_version": "1.0.1",
                        "agent": "insight_extractor",
                        "domain": "research",
                    },
                    provenance={
                        "source_agent": "research_graph",
                    },
                    confidence={
                        "score": insight.get(
                            "confidence", state.get("critic_score", 0.5)
                        ),
                        "rationale": insight.get(
                            "rationale", "Derived from research synthesis"
                        ),
                    },
                )

                stored_insights.append(
                    {
                        "packet_id": str(result.packet_id),
                        "insight_type": insight.get("type", "general"),
                        "status": result.status,
                        "written_tables": result.written_tables,
                    }
                )

                logger.debug(f"Stored insight: {result.packet_id}")

            except Exception as e:
                logger.error(f"Failed to store insight: {e}")
                stored_insights.append(
                    {
                        "insight_type": insight.get("type", "general"),
                        "status": "error",
                        "error": str(e),
                    }
                )

        logger.info(
            f"Stored {len([i for i in stored_insights if i.get('status') == 'ok'])} insights"
        )

    except Exception as e:
        logger.error(f"Insight extraction failed: {e}")
        return {
            **state,
            "stored_insights": [],
            "errors": state.get("errors", []) + [f"Insight storage failed: {str(e)}"],
        }

    return {
        **state,
        "stored_insights": stored_insights,
    }


# =============================================================================
# Conditional Routing
# =============================================================================


def should_retry(
    state: ResearchGraphState,
) -> Literal["planning_node", "finalize_node"]:
    """
    Decide whether to retry or finalize.

    Based on:
    - Critic score vs threshold
    - Retry count vs max retries
    """
    from config.research_settings import get_research_settings

    settings = get_research_settings()

    score = state.get("critic_score", 0.0)
    retry_count = state.get("retry_count", 0)

    if score < settings.critic_threshold and retry_count < settings.max_retries:
        logger.info(f"Retry triggered: score={score:.2f}, retry={retry_count + 1}")
        # Increment retry count for next iteration
        state["retry_count"] = retry_count + 1
        return "planning_node"
    else:
        logger.info(f"Proceeding to finalize: score={score:.2f}")
        return "finalize_node"


# =============================================================================
# Graph Builder
# =============================================================================


def build_research_graph() -> StateGraph:
    """
    Build and compile the research graph.

    Flow:
      START → planning_node → research_node → merge_node → critic_node →
             ↳ (if retry) → planning_node
             ↳ (if approved) → finalize_node → store_insights → END

    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(ResearchGraphState)

    # Add nodes
    graph.add_node("planning_node", planning_node)
    graph.add_node("research_node", research_node)
    graph.add_node("merge_node", merge_node)
    graph.add_node("critic_node", critic_node)
    graph.add_node("finalize_node", finalize_node)
    graph.add_node("store_insights", store_insights_node)

    # Add edges
    graph.add_edge(START, "planning_node")
    graph.add_edge("planning_node", "research_node")
    graph.add_edge("research_node", "merge_node")
    graph.add_edge("merge_node", "critic_node")

    # Conditional: retry or finalize
    graph.add_conditional_edges(
        "critic_node",
        should_retry,
        {
            "planning_node": "planning_node",
            "finalize_node": "finalize_node",
        },
    )

    # finalize → store_insights → END
    graph.add_edge("finalize_node", "store_insights")
    graph.add_edge("store_insights", END)

    # Compile
    compiled = graph.compile()

    logger.info("Research graph compiled successfully (with store_insights node)")
    return compiled


# =============================================================================
# Execution Functions
# =============================================================================


async def run_research(
    query: str,
    user_id: str = "anonymous",
    thread_id: str = None,
) -> dict:
    """
    Execute the research graph.

    Args:
        query: Research query
        user_id: User identifier
        thread_id: Optional thread ID (generated if not provided)

    Returns:
        Final output dict from the graph
    """
    # Create initial state
    state = create_initial_state(
        query=query,
        thread_id=thread_id or str(uuid4()),
        request_id=str(uuid4()),
        user_id=user_id,
    )

    logger.info(f"Starting research: thread={state['thread_id']}")

    # Build and run graph
    graph = build_research_graph()

    try:
        # Execute graph
        result = await graph.ainvoke(state)

        logger.info(f"Research completed: thread={state['thread_id']}")
        return result.get("final_output", {})

    except Exception as e:
        logger.error(f"Research graph failed: {e}")
        return {
            "error": str(e),
            "query": query,
            "thread_id": state["thread_id"],
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "debugging",
        "event-driven",
        "logging",
        "operations",
        "research-services",
        "service",
    ],
    "keywords": [
        "agent",
        "build",
        "critic",
        "finalize",
        "graph",
        "insights",
        "memory",
        "merge",
    ],
    "business_value": "Utility module for research graph",
    "last_modified": "2026-01-07T13:35:58Z",
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
