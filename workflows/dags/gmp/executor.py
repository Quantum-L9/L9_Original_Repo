"""
GMP Executor — Executor class and CLI for GMP workflow
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

from workflows.dags.gmp.graph import build_gmp_graph
from workflows.dags.gmp.state import GMPState

logger = structlog.get_logger(__name__)


class GMPLangGraphExecutor:
    """
    Executor for GMP workflow using LangGraph.

    This provides a clean interface for running the GMP DAG
    with proper state management and checkpointing.
    """

    def __init__(self):
        """Initialize the executor."""
        self.graph = build_gmp_graph()
        self.checkpointer = MemorySaver()
        self.compiled = self.graph.compile(checkpointer=self.checkpointer)

    def run(
        self,
        task: str,
        tier: str = "RUNTIME",
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the GMP workflow."""
        if thread_id is None:
            thread_id = f"gmp-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        initial_state = GMPState(task=task, tier=tier)
        config = {"configurable": {"thread_id": thread_id}}
        result = self.compiled.invoke(initial_state, config)

        return result

    def resume(
        self,
        thread_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume execution with user input."""
        config = {"configurable": {"thread_id": thread_id}}
        state = self.compiled.get_state(config)

        current_state = state.values
        for key, value in updates.items():
            if hasattr(current_state, key):
                setattr(current_state, key, value)

        result = self.compiled.invoke(current_state, config)
        return result

    def get_state(self, thread_id: str) -> GMPState | None:
        """Get current state for a thread."""
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
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GMP LangGraph Executor")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--tier", default="RUNTIME", help="KERNEL|RUNTIME|INFRA|UX")
    parser.add_argument("--resume", help="Thread ID to resume")
    parser.add_argument("--status", help="Get status for thread ID")
    parser.add_argument("--mermaid", action="store_true", help="Print Mermaid diagram")

    args = parser.parse_args()

    executor = GMPLangGraphExecutor()

    if args.mermaid:
        logger.info("output", value=executor.get_mermaid())
        return

    if args.status:
        state = executor.get_state(args.status)
        if state:
            logger.info("phase: {state.phase}")
            logger.info("task: {state.task}")
            for msg in state.messages[-10:]:
                logger.info("output", value=msg)
        else:
            logger.info("no state found for thread: {args.status}")
        return

    if not args.task and not args.resume:
        parser.print_help()
        return

    if args.resume:
        state = executor.resume(args.resume, {})
    else:
        state = executor.run(args.task, args.tier)

    messages = (
        state.get("messages", [])
        if isinstance(state, dict)
        else getattr(state, "messages", [])
    )
    for msg in messages:
        logger.info("output", value=msg)

    phase = (
        state.get("phase", "unknown")
        if isinstance(state, dict)
        else getattr(state, "phase", "unknown")
    )
    gmp_id = (
        state.get("gmp_id", "")
        if isinstance(state, dict)
        else getattr(state, "gmp_id", "")
    )
    logger.info("\ngmp id: gmp id", gmp_id=gmp_id)
    logger.info("phase: phase", phase=phase)
    logger.info("thread id: gmp-{datetime.now().strftime('%y%m%d%h%m%s')}")
    logger.info("use --resume <thread_id> to continue")


if __name__ == "__main__":
    main()
