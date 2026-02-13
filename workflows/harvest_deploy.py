"""
Harvest-Deploy Workflow — LangGraph StateGraph
===============================================

Production-grade workflow for:
1. Extract code blocks from markdown documents
2. Deploy full files to target locations
3. Inject diffs into existing files
4. Validate all changes
5. Generate report

Usage:
    from workflows.harvest_deploy import create_harvest_deploy_graph, run_harvest_deploy

    # Programmatic
    graph = create_harvest_deploy_graph()
    result = await graph.ainvoke(initial_state)

    # High-level API
    result = await run_harvest_deploy(
        source_document="current_work/01-25-2026/Plan Files To Harvest.md",
        harvest_directory="current_work/01-25-2026/harvested-files",
        extraction_patterns=[...],
        file_mappings=[...],
    )

Graph Structure:

    ┌─────────────┐
    │   START     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │   extract   │──────────────┐
    └──────┬──────┘              │
           │                     │ (on error)
           ▼                     │
    ┌─────────────┐              │
    │   deploy    │              │
    └──────┬──────┘              │
           │                     │
           ▼                     │
    ┌─────────────┐              │
    │   inject    │              │
    └──────┬──────┘              │
           │                     │
           ▼                     │
    ┌─────────────┐              │
    │  validate   │              │
    └──────┬──────┘              │
           │                     │
           ▼                     │
    ┌─────────────┐              │
    │   report    │◄─────────────┘
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    END      │
    └─────────────┘

Author: L9 Team
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.graph import END, START, StateGraph

from core.decorators import must_stay_async
from workflows.nodes import (
    deploy_files_node,
    extract_files_node,
    inject_files_node,
    report_node,
    validate_node,
)
from workflows.state import (
    ExtractionPattern,
    FileMapping,
    ValidationCheck,
    WorkflowState,
    create_initial_state,
)

# =============================================================================
# Routing Functions
# =============================================================================


def route_after_extract(state: WorkflowState) -> Literal["deploy", "report"]:
    """Route after extraction: deploy if successful, report otherwise."""
    if state.get("should_continue", True) and not state.get("error"):
        return "deploy"
    return "report"


def route_after_deploy(state: WorkflowState) -> Literal["inject", "validate", "report"]:
    """Route after deploy: inject if needed, else validate."""
    if not state.get("should_continue", True) or state.get("error"):
        return "report"

    # Check if there are inject/replace operations
    mappings = state.get("file_mappings", [])
    has_inject = any(m.get("operation") in ("inject", "replace") for m in mappings)

    return "inject" if has_inject else "validate"


def route_after_inject(state: WorkflowState) -> Literal["validate", "report"]:
    """Route after inject: validate if successful, report otherwise."""
    if state.get("should_continue", True) and not state.get("error"):
        return "validate"
    return "report"


def route_after_validate(state: WorkflowState) -> Literal["report"]:
    """Route after validate: always go to report."""
    return "report"


# =============================================================================
# Graph Builder
# =============================================================================


def create_harvest_deploy_graph() -> StateGraph:
    """
    Create the Harvest-Deploy workflow graph.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph with state schema
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("extract", extract_files_node)
    graph.add_node("deploy", deploy_files_node)
    graph.add_node("inject", inject_files_node)
    graph.add_node("validate", validate_node)
    graph.add_node("report", report_node)

    # Add edges
    graph.add_edge(START, "extract")

    # Conditional routing
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {"deploy": "deploy", "report": "report"},
    )

    graph.add_conditional_edges(
        "deploy",
        route_after_deploy,
        {"inject": "inject", "validate": "validate", "report": "report"},
    )

    graph.add_conditional_edges(
        "inject",
        route_after_inject,
        {"validate": "validate", "report": "report"},
    )

    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"report": "report"},
    )

    graph.add_edge("report", END)

    return graph.compile()


# =============================================================================
# High-Level API
# =============================================================================


@must_stay_async("callers use await")
async def run_harvest_deploy(
    source_document: str,
    harvest_directory: str,
    working_directory: str | None = None,
    extraction_patterns: list[ExtractionPattern] | None = None,
    file_mappings: list[FileMapping] | None = None,
    validation_checks: list[ValidationCheck] | None = None,
    plan_document: str | None = None,
    workflow_id: str | None = None,
) -> WorkflowState:
    """
    Run the harvest-deploy workflow.

    High-level API for running the complete workflow.

    Args:
        source_document: Path to markdown with code blocks
        harvest_directory: Where to extract files
        working_directory: Project root (defaults to cwd)
        extraction_patterns: Patterns for extracting code
        file_mappings: Mappings from extracted to target files
        validation_checks: Custom validation checks
        plan_document: Optional plan document path
        workflow_id: Optional workflow ID

    Returns:
        Final workflow state with all results

    Example:
        result = await run_harvest_deploy(
            source_document="current_work/01-25-2026/Plan Files To Harvest.md",
            harvest_directory="current_work/01-25-2026/harvested-files",
            extraction_patterns=[
                {"start_line": 22, "end_line": 141, "output_file": "migration.sql", "strip_backticks": True},
            ],
            file_mappings=[
                {"source": "harvested/migration.sql", "destination": "migrations/new.sql", "operation": "copy"},
            ],
        )
    """
    working_dir = working_directory or str(Path.cwd())
    wf_id = (
        workflow_id
        or f"hd-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    )

    initial_state = create_initial_state(
        workflow_id=wf_id,
        source_document=source_document,
        harvest_directory=harvest_directory,
        working_directory=working_dir,
        extraction_patterns=extraction_patterns,
        file_mappings=file_mappings,
        validation_checks=validation_checks,
        plan_document=plan_document,
    )

    graph = create_harvest_deploy_graph()

    # Run the graph
    return await graph.ainvoke(initial_state)


# =============================================================================
# CLI Entry Point
# =============================================================================


def _parse_args():
    """Parse CLI arguments."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Harvest-Deploy Workflow")
    parser.add_argument("--config", "-c", type=Path, help="YAML config file")
    parser.add_argument("--source", "-s", help="Source document path")
    parser.add_argument("--harvest-dir", "-o", help="Harvest directory")
    parser.add_argument("--working-dir", "-w", type=Path, help="Working directory")
    return parser.parse_args(), parser


async def main():
    """CLI entry point for running harvest-deploy workflow."""
    import sys

    import yaml

    args, parser = _parse_args()

    config: dict = {}
    if args.config:
        # Read config file synchronously before async context
        config = yaml.safe_load(args.config.read_text())

    if config:
        result = await run_harvest_deploy(
            source_document=config.get("source_document", args.source),
            harvest_directory=config.get("harvest_directory", args.harvest_dir),
            working_directory=str(
                config.get("working_directory", args.working_dir or Path.cwd())
            ),
            extraction_patterns=config.get("extraction_patterns"),
            file_mappings=config.get("file_mappings"),
            validation_checks=config.get("validation_checks"),
            plan_document=config.get("plan_document"),
        )
    else:
        if not args.source or not args.harvest_dir:
            parser.error("--source and --harvest-dir required when not using --config")

        result = await run_harvest_deploy(
            source_document=args.source,
            harvest_directory=args.harvest_dir,
            working_directory=str(args.working_dir) if args.working_dir else None,
        )

    # Exit with appropriate code
    success = result.get("validation_passed", False) and not result.get("error")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
