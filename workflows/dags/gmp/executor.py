"""
GMP Executor — Executor class and CLI for GMP workflow

Provides both programmatic (SDK) and CLI interfaces.
Uses Redis-backed checkpointing when available for resume/audit.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

from workflows.dags.gmp.graph import build_gmp_graph
from workflows.dags.gmp.state import GMPState

logger = structlog.get_logger(__name__)


def _build_checkpointer():
    """Build the best available checkpointer.

    Prefers Redis for production (resume, audit trail, cross-process).
    Falls back to MemorySaver for local dev / tests.
    """
    redis_url = os.getenv("REDIS_URL") or os.getenv("C1_REDIS_URL")
    if redis_url:
        try:
            from langgraph.checkpoint.redis import RedisSaver

            checkpointer = RedisSaver(redis_url=redis_url)
            logger.info("gmp_checkpointer", backend="redis", url=redis_url[:30])
            return checkpointer
        except ImportError:
            logger.info(
                "gmp_checkpointer",
                backend="memory",
                reason="langgraph-checkpoint-redis not installed",
            )
        except Exception as exc:
            logger.warning(
                "gmp_checkpointer",
                backend="memory",
                reason=f"Redis connection failed: {exc}",
            )

    logger.info("gmp_checkpointer", backend="memory")
    return MemorySaver()


class GMPLangGraphExecutor:
    """
    Executor for GMP workflow using LangGraph.

    Provides:
    - run(): Execute GMP end-to-end with checkpointing
    - resume(): Resume from a checkpoint after failure
    - get_state(): Inspect execution state at any point
    - get_mermaid(): Generate visual diagram

    Checkpoints are first-class:
    - Every node transition is checkpointed
    - Failed runs can resume from last successful node
    - State history provides audit trail
    """

    def __init__(self):
        """Initialize the executor with graph and checkpointer."""
        self.graph = build_gmp_graph()
        self.checkpointer = _build_checkpointer()
        self.compiled = self.graph.compile(checkpointer=self.checkpointer)

    def run(
        self,
        task: str,
        tier: str = "RUNTIME",
        agent_id: str = "",
        tenant_id: str = "",
        thread_id: str | None = None,
        todo_plan: list[dict[str, str]] | None = None,
        file_budget_may: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the GMP workflow end-to-end.

        Args:
            task: Task description
            tier: KERNEL | RUNTIME | INFRA | UX
            agent_id: Calling agent identity (auto-injected by SDK)
            tenant_id: Tenant context (auto-injected by SDK)
            thread_id: Optional thread ID for checkpointing
            todo_plan: List of TODO items with file, action, description
            file_budget_may: List of files allowed to be modified

        Returns:
            Final state as dict
        """
        if thread_id is None:
            thread_id = f"gmp-{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"

        initial_state = GMPState(
            task=task,
            tier=tier,
            agent_id=agent_id,
            tenant_id=tenant_id,
            todo_plan=todo_plan or [],
            file_budget_may=file_budget_may or [],
        )

        config = {"configurable": {"thread_id": thread_id}}

        logger.info(
            "gmp_run_start",
            task=task[:80],
            tier=tier,
            agent_id=agent_id,
            thread_id=thread_id,
            todo_items=len(initial_state.todo_plan),
        )

        result = self.compiled.invoke(initial_state, config)

        logger.info(
            "gmp_run_complete",
            thread_id=thread_id,
            phase=result.get("phase", "unknown")
            if isinstance(result, dict)
            else getattr(result, "phase", "unknown"),
        )

        return result

    def resume(
        self,
        thread_id: str,
        updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resume execution from a checkpoint.

        Useful after:
        - Validation failure (fix files, then resume)
        - Process restart (pick up where left off)
        - Manual state correction

        Args:
            thread_id: Thread ID to resume
            updates: Optional state updates to apply before resuming

        Returns:
            Final state as dict
        """
        config = {"configurable": {"thread_id": thread_id}}
        state = self.compiled.get_state(config)

        if not state or not state.values:
            logger.warning("gmp_resume_no_state", thread_id=thread_id)
            return {"error": f"No state found for thread: {thread_id}"}

        current_state = state.values
        if updates:
            for key, value in updates.items():
                if hasattr(current_state, key):
                    setattr(current_state, key, value)

        update_keys = list((updates or {}).keys())
        logger.info("gmp_resume", thread_id=thread_id, updates=update_keys)

        result = self.compiled.invoke(current_state, config)
        return result

    def get_state(self, thread_id: str) -> GMPState | None:
        """Get current state for a thread.

        Returns the full GMPState including messages, phase,
        validation results, etc.
        """
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = self.compiled.get_state(config)
            return state.values if state else None
        except Exception:
            return None

    def get_mermaid(self) -> str:
        """Get Mermaid diagram of the graph."""
        return self.compiled.get_graph().draw_mermaid()


def main():
    """CLI entry point for direct execution."""
    import argparse

    parser = argparse.ArgumentParser(description="GMP LangGraph Executor")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--tier", default="RUNTIME", help="KERNEL|RUNTIME|INFRA|UX")
    parser.add_argument("--agent-id", default="cli", help="Agent identity")
    parser.add_argument("--resume", help="Thread ID to resume")
    parser.add_argument("--status", help="Get status for thread ID")
    parser.add_argument("--mermaid", action="store_true", help="Print Mermaid diagram")
    parser.add_argument(
        "--todo",
        action="append",
        default=[],
        help="TODO item as 'file|action|description' (repeatable)",
    )

    args = parser.parse_args()

    executor = GMPLangGraphExecutor()

    if args.mermaid:
        logger.info("mermaid_output", diagram=executor.get_mermaid())
        return

    if args.status:
        state = executor.get_state(args.status)
        if state:
            logger.info("gmp_status", phase=state.phase, task=state.task)
            for msg in state.messages[-10:]:
                logger.info("gmp_message", msg=msg)
        else:
            logger.info("gmp_status", error=f"No state for thread: {args.status}")
        return

    if not args.task and not args.resume:
        parser.print_help()
        return

    # Parse TODO items from CLI
    todo_plan = []
    for todo_str in args.todo:
        parts = todo_str.split("|", 2)
        if len(parts) >= 2:
            todo_plan.append(
                {
                    "file": parts[0],
                    "action": parts[1],
                    "description": parts[2] if len(parts) > 2 else "",
                }
            )

    if args.resume:
        result = executor.resume(args.resume)
    else:
        result = executor.run(
            args.task,
            args.tier,
            agent_id=args.agent_id,
            todo_plan=todo_plan,
        )

    # Display results
    messages = (
        result.get("messages", [])
        if isinstance(result, dict)
        else getattr(result, "messages", [])
    )
    for msg in messages:
        logger.info("gmp_output", msg=msg)

    phase = (
        result.get("phase", "unknown")
        if isinstance(result, dict)
        else getattr(result, "phase", "unknown")
    )
    gmp_id = (
        result.get("gmp_id", "")
        if isinstance(result, dict)
        else getattr(result, "gmp_id", "")
    )
    logger.info("gmp_complete", gmp_id=gmp_id, phase=phase)


if __name__ == "__main__":
    main()
