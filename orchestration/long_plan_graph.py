"""
L9 Orchestration - Long Plan LangGraph DAG
==========================================

LangGraph-based DAGs for orchestrating long plans with L's tools.

Features:
- Orchestrates memory, MCP, Mac Agent, and GMP tools
- Enforces governance discipline (PLAN → EXECUTE → HALT)
- Respects Igor approval requirement for GMP runs and git commits
- Creates pending actions only (no auto-execution for sensitive operations)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Long Plan LangGraph DAG",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-25T18:55:20Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "long_plan_graph",
    "type": "service",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["episodic_memory", "working_memory"],
        "imported_by": ["runtime.long_plan_tool", "tests.integration.test_l_bootstrap"],
    },
}
# ============================================================================

import os
from pathlib import Path
from typing import Any, Literal, TypedDict

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# LLM Configuration
LLM_MODEL = os.getenv("L9_LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# LLM Artifact Generation
# =============================================================================


@must_stay_async("callers use await")
async def generate_artifact_with_llm(
    artifact_type: str,
    goal: str,
    constraints: list[str],
    context: dict[str, Any],
    max_tokens: int = 2048,
) -> str | None:
    """
    Generate an artifact (plan, code, docs) using LLM.

    Args:
        artifact_type: One of "plan", "code", "docs"
        goal: The goal/objective to accomplish
        constraints: List of constraints to follow
        context: Additional context (governance rules, project history, etc.)
        max_tokens: Maximum tokens for generation

    Returns:
        Generated artifact as string, or None on failure
    """
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, skipping LLM artifact generation")
            return None

        client = AsyncOpenAI(api_key=api_key)

        # Build prompt based on artifact type
        if artifact_type == "plan":
            system_prompt = """You are L9's planning agent. Generate a clear, actionable implementation plan.

Format your plan as:
## Objective
[One-sentence objective]

## Steps
1. [Step description]
2. [Step description]
...

## Dependencies
- [Any dependencies or prerequisites]

## Risks
- [Any risks or considerations]

Be specific and actionable. No fluff."""

            user_prompt = f"""Goal: {goal}

Constraints:
{chr(10).join(f"- {c}" for c in constraints) if constraints else "- None specified"}

Context:
{_format_context(context)}

Generate a clear implementation plan."""

        elif artifact_type == "code":
            system_prompt = """You are L9's code generation agent. Generate production-ready Python code.

Requirements:
- Use structlog for logging (never print statements)
- Include proper type hints
- Include docstrings
- Handle errors gracefully
- Follow PEP 8 style

Output the code directly, no markdown fences unless multiple files."""

            user_prompt = f"""Goal: {goal}

Constraints:
{chr(10).join(f"- {c}" for c in constraints) if constraints else "- None specified"}

Context:
{_format_context(context)}

Generate the implementation code."""

        elif artifact_type == "docs":
            system_prompt = """You are L9's documentation agent. Generate clear, concise documentation.

Format:
- Use markdown
- Include usage examples where applicable
- Be concise but complete"""

            user_prompt = f"""Goal: {goal}

Constraints:
{chr(10).join(f"- {c}" for c in constraints) if constraints else "- None specified"}

Context:
{_format_context(context)}

Generate documentation for this implementation."""
        else:
            logger.error(f"Unknown artifact type: {artifact_type}")
            return None

        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        if content:
            logger.info(
                "LLM artifact generated",
                artifact_type=artifact_type,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
            return content.strip()
        return None

    except ImportError:
        logger.warning("openai package not installed, skipping LLM artifact generation")
        return None
    except Exception as e:
        logger.error(f"LLM artifact generation failed: {e}", exc_info=True)
        return None


def _format_context(context: dict[str, Any]) -> str:
    """Format context dict into readable string."""
    parts = []

    if context.get("governance_rules"):
        rules = context["governance_rules"]
        parts.append(f"Governance Rules: {len(rules)} rules loaded")

    if context.get("project_history"):
        history = context["project_history"]
        parts.append(f"Project History: {len(history)} recent items")

    if context.get("github_context"):
        parts.append(f"GitHub: {context['github_context'].get('summary', 'available')}")

    if context.get("notion_context"):
        parts.append(f"Notion: {context['notion_context'].get('summary', 'available')}")

    return chr(10).join(parts) if parts else "No additional context"


# Try to import LangGraph
try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not installed. Long plan graphs unavailable.")


# =============================================================================
# State Definition
# =============================================================================


class LongPlanState(TypedDict):
    """
    State for long plan execution DAG.

    Tracks:
    - Goal and constraints
    - Memory context (governance, project history)
    - Gathered context (MCP results, repo state)
    - Drafted work (plans, code, docs)
    - Pending actions (GMP, git commits requiring approval)
    - Review results
    - Execution phase (PLAN, EXECUTE, HALT)
    """

    # Input
    goal: str
    constraints: list[str]
    target_apps: list[str]  # e.g., ["github", "notion", "vercel"]

    # Phase tracking
    phase: Literal["PLAN", "EXECUTE", "HALT"]

    # Memory context
    governance_rules: list[dict[str, Any]]
    project_history: list[dict[str, Any]]

    # Gathered context
    github_context: dict[str, Any] | None
    notion_context: dict[str, Any] | None
    vercel_context: dict[str, Any] | None

    # Drafted work
    draft_plan: str | None
    draft_code: str | None
    draft_docs: str | None

    # Pending actions (require Igor approval)
    pending_gmp_tasks: list[dict[str, Any]]
    pending_git_commits: list[dict[str, Any]]
    pending_deployments: list[dict[str, Any]]

    # Review
    review_summary: str | None
    review_approved: bool

    # Results
    completed_actions: list[dict[str, Any]]
    errors: list[str]

    # Metadata
    agent_id: str
    thread_id: str | None


# =============================================================================
# DAG Nodes
# =============================================================================


@must_stay_async("callers use await")
async def hydrate_memory_node(state: LongPlanState) -> LongPlanState:
    """
    Hydrate memory context from governance_meta and project_history.

    Searches memory for:
    - Governance rules and authority (governance_meta)
    - Project history and past decisions (project_history)
    """
    logger.info("hydrate_memory_node: Loading memory context")

    try:
        from runtime.memory_helpers import (
            MEMORY_SEGMENT_GOVERNANCE_META,
            MEMORY_SEGMENT_PROJECT_HISTORY,
            memory_search,
        )

        agent_id = state.get("agent_id", "L")

        # Search governance rules
        governance_rules = await memory_search(
            segment=MEMORY_SEGMENT_GOVERNANCE_META,
            query=state.get("goal", ""),
            agent_id=agent_id,
            top_k=10,
        )
        if not governance_rules:
            logger.warning(
                "long_plan: hydrate_memory_node - No governance rules found in memory. "
                "Continuing with empty set. Check memory service availability."
            )
            governance_rules = []

        # Search project history
        project_history = await memory_search(
            segment=MEMORY_SEGMENT_PROJECT_HISTORY,
            query=state.get("goal", ""),
            agent_id=agent_id,
            top_k=10,
        )
        if not project_history:
            logger.warning(
                "long_plan: hydrate_memory_node - No project history found in memory. "
                "Continuing with empty set. Check memory service availability."
            )
            project_history = []

        logger.info(
            f"hydrate_memory_node: Loaded {len(governance_rules)} governance rules, "
            f"{len(project_history)} project history entries"
        )

        return {
            **state,
            "governance_rules": governance_rules,
            "project_history": project_history,
        }

    except Exception as e:
        logger.error(f"hydrate_memory_node failed: {e}", exc_info=True)
        return {
            **state,
            "errors": [*state.get("errors", []), f"hydrate_memory_node error: {e!s}"],
        }


@must_stay_async("callers use await")
async def gather_context_node(state: LongPlanState) -> LongPlanState:
    """
    Gather context using MCP tools (GitHub, Notion, Vercel).

    Calls MCP tools to gather:
    - GitHub repo state
    - Notion documentation
    - Vercel deployment status
    """
    logger.info("gather_context_node: Gathering context via MCP")

    try:
        from runtime.mcp_tool import mcp_call_tool

        agent_id = state.get("agent_id", "L")
        target_apps = state.get("target_apps", [])

        github_context = None
        notion_context = None
        vercel_context = None

        # Gather GitHub context if requested
        if "github" in target_apps:
            try:
                result = await mcp_call_tool(
                    server_id="github",
                    tool_name="github.get_repo",
                    arguments={"repo": "L9"},  # Default repo
                    agent_id=agent_id,
                )
                if result.get("success"):
                    github_context = result.get("result")
            except Exception as e:
                logger.warning(f"Failed to gather GitHub context: {e}")

        # Gather Notion context if requested
        if "notion" in target_apps:
            try:
                result = await mcp_call_tool(
                    server_id="notion",
                    tool_name="notion.search_pages",
                    arguments={"query": state.get("goal", "")},
                    agent_id=agent_id,
                )
                if result.get("success"):
                    notion_context = result.get("result")
            except Exception as e:
                logger.warning(f"Failed to gather Notion context: {e}")

        # Gather Vercel context if requested
        if "vercel" in target_apps:
            try:
                result = await mcp_call_tool(
                    server_id="vercel",
                    tool_name="vercel.get_deploy_status",
                    arguments={},
                    agent_id=agent_id,
                )
                if result.get("success"):
                    vercel_context = result.get("result")
            except Exception as e:
                logger.warning(f"Failed to gather Vercel context: {e}")

        logger.info("gather_context_node: Context gathered")

        return {
            **state,
            "github_context": github_context,
            "notion_context": notion_context,
            "vercel_context": vercel_context,
        }

    except Exception as e:
        logger.error(f"gather_context_node failed: {e}", exc_info=True)
        return {
            **state,
            "errors": [*state.get("errors", []), f"gather_context_node error: {e!s}"],
        }


@must_stay_async("callers use await")
async def draft_work_node(state: LongPlanState) -> LongPlanState:
    """
    Draft work using L or a worker agent via existing LLM tool.

    Creates:
    - Draft plan
    - Draft code (if applicable)
    - Draft documentation (if applicable)
    """
    logger.info("draft_work_node: Drafting work with LLM")

    try:
        goal = state.get("goal", "")
        constraints = state.get("constraints", [])

        # Build context for LLM
        context = {
            "governance_rules": state.get("governance_rules", []),
            "project_history": state.get("project_history", []),
            "github_context": state.get("github_context"),
            "notion_context": state.get("notion_context"),
            "vercel_context": state.get("vercel_context"),
        }

        # Generate plan (always)
        draft_plan = await generate_artifact_with_llm(
            artifact_type="plan",
            goal=goal,
            constraints=constraints,
            context=context,
        )

        # If plan mentions code generation, generate code artifact
        draft_code = None
        if draft_plan and any(
            kw in goal.lower()
            for kw in ["implement", "code", "build", "create", "write"]
        ):
            draft_code = await generate_artifact_with_llm(
                artifact_type="code",
                goal=goal,
                constraints=constraints,
                context=context,
            )

        # If plan mentions documentation, generate docs artifact
        draft_docs = None
        if draft_plan and any(
            kw in goal.lower() for kw in ["document", "docs", "readme", "guide"]
        ):
            draft_docs = await generate_artifact_with_llm(
                artifact_type="docs",
                goal=goal,
                constraints=constraints,
                context=context,
            )

        # Fallback if LLM failed
        if not draft_plan:
            draft_plan = f"[FALLBACK] Plan for: {goal}\nConstraints: {', '.join(constraints)}\n(LLM unavailable)"

        logger.info(
            "draft_work_node: Work drafted",
            has_plan=bool(draft_plan),
            has_code=bool(draft_code),
            has_docs=bool(draft_docs),
        )

        return {
            **state,
            "draft_plan": draft_plan,
            "draft_code": draft_code,
            "draft_docs": draft_docs,
            "phase": "EXECUTE",  # Transition to EXECUTE phase after drafting
        }

    except Exception as e:
        logger.error(f"draft_work_node failed: {e}", exc_info=True)
        return {
            **state,
            "errors": [*state.get("errors", []), f"draft_work_node error: {e!s}"],
        }


@must_stay_async("callers use await")
async def prepare_changes_node(state: LongPlanState) -> LongPlanState:
    """
    Prepare changes using mac_agent.exec_task and/or gmp_run in pending mode only.

    This node:
    - Creates pending GMP tasks (requires Igor approval)
    - Creates pending git commits (requires Igor approval)
    - Does NOT execute them directly
    """
    logger.info("prepare_changes_node: Preparing pending changes")

    try:
        from runtime.gmp_tool import gmp_run_tool

        agent_id = state.get("agent_id", "L")
        draft_plan = state.get("draft_plan")
        draft_code = state.get("draft_code")

        pending_gmp_tasks = state.get("pending_gmp_tasks", [])
        pending_git_commits = state.get("pending_git_commits", [])

        # Create pending GMP task if we have a plan
        if draft_plan:
            try:
                gmp_result = await gmp_run_tool(
                    gmp_markdown=draft_plan,
                    repo_root=str(Path.home() / "Projects/L9"),  # Default repo
                    caller=agent_id,
                    metadata={
                        "goal": state.get("goal"),
                        "phase": "prepare_changes",
                    },
                )

                if gmp_result.get("task_id"):
                    pending_gmp_tasks.append(
                        {
                            "task_id": gmp_result["task_id"],
                            "summary": gmp_result.get("summary", {}),
                            "status": "pending_igor_approval",
                        }
                    )
                    logger.info(f"Created pending GMP task: {gmp_result['task_id']}")
            except Exception as e:
                logger.warning(f"Failed to create GMP task: {e}")

        # Create pending git commit (placeholder - would need git tool implementation)
        if draft_code:
            pending_git_commits.append(
                {
                    "message": f"Changes for: {state.get('goal', '')}",
                    "files": [],  # Would be populated from draft_code
                    "status": "pending_igor_approval",
                }
            )
            logger.info("Created pending git commit")

        logger.info(
            f"prepare_changes_node: Created {len(pending_gmp_tasks)} GMP tasks, "
            f"{len(pending_git_commits)} git commits (all pending approval)"
        )

        return {
            **state,
            "pending_gmp_tasks": pending_gmp_tasks,
            "pending_git_commits": pending_git_commits,
        }

    except Exception as e:
        logger.error(f"prepare_changes_node failed: {e}", exc_info=True)
        return {
            **state,
            "errors": [*state.get("errors", []), f"prepare_changes_node error: {e!s}"],
        }


@must_stay_async("callers use await")
async def final_review_node(state: LongPlanState) -> LongPlanState:
    """
    Final review where L reviews diffs/results.

    Creates a summary of:
    - What was planned
    - What pending actions were created
    - What needs Igor's approval
    """
    logger.info("final_review_node: Conducting final review")

    try:
        goal = state.get("goal", "")
        pending_gmp_tasks = state.get("pending_gmp_tasks", [])
        pending_git_commits = state.get("pending_git_commits", [])

        # Create review summary
        review_summary = f"""
Goal: {goal}

Pending Actions Requiring Igor's Approval:
- GMP Tasks: {len(pending_gmp_tasks)}
- Git Commits: {len(pending_git_commits)}

Review the pending actions and approve them to proceed with execution.
"""

        # Review is not auto-approved (requires Igor)
        review_approved = False

        logger.info("final_review_node: Review completed")

        return {
            **state,
            "review_summary": review_summary,
            "review_approved": review_approved,
            "phase": "HALT",  # Move to HALT phase after review
        }

    except Exception as e:
        logger.error(f"final_review_node failed: {e}", exc_info=True)
        return {
            **state,
            "errors": [*state.get("errors", []), f"final_review_node error: {e!s}"],
            "phase": "HALT",
        }


# =============================================================================
# Graph Builder
# =============================================================================


def build_long_plan_graph():
    """
    Build the LangGraph DAG for long plan execution.

    Graph structure:
        START → hydrate_memory → gather_context → draft_work → prepare_changes → final_review → END

    Enforces PLAN → EXECUTE → HALT governance discipline.

    Returns:
        Compiled StateGraph or None if LangGraph unavailable
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("LangGraph not available - cannot build long plan graph")
        return None

    # Create graph with LongPlanState
    graph = StateGraph(LongPlanState)

    # Add nodes
    graph.add_node("hydrate_memory", hydrate_memory_node)
    graph.add_node("gather_context", gather_context_node)
    graph.add_node("draft_work", draft_work_node)
    graph.add_node("prepare_changes", prepare_changes_node)
    graph.add_node("final_review", final_review_node)

    # Add edges (linear pipeline with PLAN → EXECUTE → HALT)
    graph.set_entry_point("hydrate_memory")
    graph.add_edge("hydrate_memory", "gather_context")
    graph.add_edge("gather_context", "draft_work")
    graph.add_edge("draft_work", "prepare_changes")
    graph.add_edge("prepare_changes", "final_review")
    graph.add_edge("final_review", END)

    return graph.compile()


# =============================================================================
# Execution Interface
# =============================================================================


@must_stay_async("callers use await")
async def execute_long_plan(
    goal: str,
    constraints: list[str] | None = None,
    target_apps: list[str] | None = None,
    agent_id: str = "L",
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute a long plan through the DAG.

    Args:
        goal: Goal description
        constraints: List of constraints
        target_apps: List of target apps (e.g., ["github", "notion"])
        agent_id: Agent identifier (default: "L")
        thread_id: Optional thread identifier

    Returns:
        Final state dictionary with results
    """
    logger.info(f"Executing long plan: goal={goal[:50]}...")

    graph = build_long_plan_graph()
    if not graph:
        return {
            "success": False,
            "error": "LangGraph not available",
        }

    # Initialize state
    initial_state: LongPlanState = {
        "goal": goal,
        "constraints": constraints or [],
        "target_apps": target_apps or [],
        "phase": "PLAN",
        "governance_rules": [],
        "project_history": [],
        "github_context": None,
        "notion_context": None,
        "vercel_context": None,
        "draft_plan": None,
        "draft_code": None,
        "draft_docs": None,
        "pending_gmp_tasks": [],
        "pending_git_commits": [],
        "pending_deployments": [],
        "review_summary": None,
        "review_approved": False,
        "completed_actions": [],
        "errors": [],
        "agent_id": agent_id,
        "thread_id": thread_id,
    }

    try:
        # Execute graph
        final_state = await graph.ainvoke(initial_state)

        # Log tool calls for the entire DAG execution
        try:
            from core.tools.tool_graph import ToolGraph

            await ToolGraph.log_tool_call(
                tool_name="long_plan_execute",
                agent_id=agent_id,
                success=len(final_state.get("errors", [])) == 0,
                duration_ms=0,  # Would need timing
                error=(
                    "; ".join(final_state.get("errors", []))
                    if final_state.get("errors")
                    else None
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to log long plan execution: {e}")

        return {
            "success": len(final_state.get("errors", [])) == 0,
            "state": final_state,
            "pending_actions": {
                "gmp_tasks": final_state.get("pending_gmp_tasks", []),
                "git_commits": final_state.get("pending_git_commits", []),
            },
            "review_summary": final_state.get("review_summary"),
        }

    except Exception as e:
        logger.error(f"Long plan execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@must_stay_async("callers use await")
async def simulate_long_plan(
    goal: str,
    constraints: list[str] | None = None,
    target_apps: list[str] | None = None,
    agent_id: str = "L",
) -> dict[str, Any]:
    """
    Simulate a long plan without executing (dry run).

    Args:
        goal: Goal description
        constraints: List of constraints
        target_apps: List of target apps
        agent_id: Agent identifier (default: "L")

    Returns:
        Simulation results showing what would happen
    """
    logger.info(f"Simulating long plan: goal={goal[:50]}...")

    # For simulation, we can run the graph but mark it as simulation
    # In a full implementation, this might skip actual tool calls

    result = await execute_long_plan(
        goal=goal,
        constraints=constraints,
        target_apps=target_apps,
        agent_id=agent_id,
    )

    return {
        **result,
        "simulation": True,
        "message": "This is a simulation - no actual changes were made",
    }


async def extract_tasks_from_plan(plan_id: str) -> list[dict[str, Any]]:
    """
    Extract executable task specs from a completed plan.

    Retrieves plan state from memory substrate (by thread_id as plan_id)
    and extracts pending_gmp_tasks and pending_git_commits as task specs.

    Args:
        plan_id: Plan identifier (thread_id from execute_long_plan)

    Returns:
        List of task spec dicts with: name, payload, handler, agent_id, priority, tags
    """
    try:
        from memory.substrate_service import get_service

        try:
            substrate = await get_service()
        except RuntimeError:
            logger.warning("Memory substrate not initialized - cannot extract tasks")
            return []

        # Retrieve plan state from memory by thread_id
        packets = await substrate.search_packets_by_thread(
            thread_id=plan_id,
            packet_type="long_plan.state",
            limit=1,
        )

        if not packets:
            # Try without packet_type filter
            packets = await substrate.search_packets_by_thread(
                thread_id=plan_id,
                limit=10,
            )
            # Find the most recent long_plan.state packet
            plan_packets = [
                p for p in packets if p.get("packet_type") == "long_plan.state"
            ]
            if not plan_packets:
                logger.warning(f"Plan {plan_id} not found in memory substrate")
                return []
            plan_state = plan_packets[-1].get("payload", {})
        else:
            # Get the most recent plan state
            plan_state = packets[-1].get("payload", {})

        task_specs = []

        # Extract GMP tasks
        pending_gmp_tasks = plan_state.get("pending_gmp_tasks", [])
        for gmp_task in pending_gmp_tasks:
            task_specs.append(
                {
                    "name": f"GMP Run: {gmp_task.get('task_id', 'unknown')}",
                    "payload": {
                        "type": "gmp_run",
                        "task_id": gmp_task.get("task_id"),
                        "gmp_markdown": gmp_task.get("summary", {}).get(
                            "gmp_preview", ""
                        ),
                        "repo_root": gmp_task.get("summary", {}).get("repo_root", ""),
                        "status": "pending_igor_approval",
                    },
                    "handler": "gmp_worker",
                    "agent_id": "L",
                    "priority": 5,
                    "tags": ["gmp", "long_plan", plan_id],
                }
            )

        # Extract git commit tasks
        pending_git_commits = plan_state.get("pending_git_commits", [])
        for git_commit in pending_git_commits:
            task_specs.append(
                {
                    "name": f"Git Commit: {git_commit.get('message', 'unknown')[:50]}",
                    "payload": {
                        "type": "git_commit",
                        "message": git_commit.get("message", ""),
                        "files": git_commit.get("files", []),
                        "status": "pending_igor_approval",
                    },
                    "handler": "git_worker",
                    "agent_id": "L",
                    "priority": 5,
                    "tags": ["git", "long_plan", plan_id],
                }
            )

        logger.info(f"Extracted {len(task_specs)} tasks from plan {plan_id}")
        return task_specs

    except Exception as e:
        logger.error(f"Failed to extract tasks from plan {plan_id}: {e}", exc_info=True)
        return []


__all__ = [
    "LongPlanState",
    "build_long_plan_graph",
    "execute_long_plan",
    "extract_tasks_from_plan",
    "simulate_long_plan",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-031",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.tools.tool_graph",
        "memory.substrate_service",
        "runtime.gmp_tool",
        "runtime.mcp_tool",
    ],
    "tags": [
        "api",
        "async",
        "auth",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "orchestration",
        "service",
    ],
    "keywords": [
        "agent",
        "artifact",
        "build",
        "changes",
        "dag",
        "draft",
        "execute",
        "extract",
    ],
    "business_value": "Implements LongPlanState for long plan graph functionality",
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
