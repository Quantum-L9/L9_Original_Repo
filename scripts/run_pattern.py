#!/usr/bin/env python3
"""
L9 Pattern Orchestrator CLI
===========================

Command-line interface for executing architecture patterns.

Usage:
    python scripts/run_pattern.py "Build a user authentication system"
    python scripts/run_pattern.py --config config/patterns/pipeline_v1.yaml "Design API"
    python scripts/run_pattern.py --dry-run "Test prompt"
    python scripts/run_pattern.py --help

Version: 1.0.0
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute L9 architecture patterns via PatternOrchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Execute with default configs
    python scripts/run_pattern.py "Build a user authentication system"
    
    # Execute with custom config
    python scripts/run_pattern.py --config config/patterns/pipeline_v1.yaml "Design API"
    
    # Dry run (validate without agent execution)
    python scripts/run_pattern.py --dry-run "Test prompt"
    
    # Use direct LLM agent (no consensus loop)
    python scripts/run_pattern.py --agent direct "Build X"
    
    # Multiple prompts
    python scripts/run_pattern.py "Prompt 1" "Prompt 2" "Prompt 3"
    
    # Output as JSON
    python scripts/run_pattern.py --json "Build a caching layer"
        """,
    )

    parser.add_argument(
        "prompts",
        nargs="+",
        help="User prompts/requirements to process",
    )

    parser.add_argument(
        "--config",
        "-c",
        default="config/patterns/pipeline_v1.yaml",
        help="Path to pattern config YAML (default: config/patterns/pipeline_v1.yaml)",
    )

    parser.add_argument(
        "--subsystem",
        "-s",
        default="config/subsystems/code_mutation.yaml",
        help="Path to subsystem config YAML (default: config/subsystems/code_mutation.yaml)",
    )

    parser.add_argument(
        "--agent",
        "-a",
        choices=["cell", "direct", "stub"],
        default="stub",
        help="Agent type: cell (consensus loop), direct (single LLM), stub (mock)",
    )

    parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o",
        help="Model to use for agents (default: gpt-4o)",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Validate configuration without executing agents",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--trace-id",
        "-t",
        default=None,
        help="Trace ID for distributed tracing",
    )

    return parser.parse_args()


def create_agent(agent_type: str, model: str):
    """Create agent based on type."""
    if agent_type == "cell":
        from orchestrators.pattern.cell_adapter import CellAgentAdapter

        return CellAgentAdapter(model=model)

    elif agent_type == "direct":
        from orchestrators.pattern.cell_adapter import DirectLLMAgent

        return DirectLLMAgent(model=model)

    else:  # stub
        return None  # PatternOrchestrator will use StubAgent


async def run_pattern(args: argparse.Namespace) -> dict:
    """Execute pattern with given arguments."""
    from orchestrators.pattern import PatternOrchestrator

    # Create agent
    agent = create_agent(args.agent, args.model)

    # Check if config files exist
    config_path = Path(args.config)
    subsystem_path = Path(args.subsystem)

    if not config_path.exists():
        logger.warning(f"Pattern config not found: {config_path}, using defaults")
        config_path = None

    if not subsystem_path.exists():
        logger.warning(f"Subsystem config not found: {subsystem_path}, using defaults")
        subsystem_path = None

    # Create orchestrator
    orchestrator = PatternOrchestrator(
        pattern_path=str(config_path) if config_path else None,
        subsystem_config_path=str(subsystem_path) if subsystem_path else None,
        agent=agent,
    )

    logger.info(
        "Starting pattern execution",
        prompts=args.prompts,
        agent_type=args.agent,
        dry_run=args.dry_run,
    )

    # Execute
    context = {"trace_id": args.trace_id} if args.trace_id else None
    result = await orchestrator.execute(
        user_prompts=args.prompts,
        dry_run=args.dry_run,
        context=context,
    )

    return {
        "success": result.is_success,
        "pipeline_id": str(result.trace_id),
        "status": result.status.value
        if hasattr(result.status, "value")
        else str(result.status),
        "nodes_executed": len(result.node_results),
        "node_results": [
            {
                "node_id": nr.node_id,
                "status": nr.status.value
                if hasattr(nr.status, "value")
                else str(nr.status),
                "duration_ms": nr.duration_ms,
                "error": nr.error,
            }
            for nr in result.node_results
        ],
        "final_output": result.artifacts or {},
        "duration_ms": result.total_duration_ms,
        "error": result.error,
    }


def print_result(result: dict, as_json: bool):
    """Print execution result."""
    if as_json:
        print(json.dumps(result, indent=2, default=str))
        return

    # Human-readable output
    print("\n" + "=" * 60)
    print("PATTERN EXECUTION RESULT")
    print("=" * 60)

    status_icon = "✅" if result["success"] else "❌"
    print(f"\nStatus: {status_icon} {result['status']}")
    print(f"Pipeline ID: {result['pipeline_id']}")
    print(f"Duration: {result['duration_ms']}ms")
    print(f"Nodes Executed: {result['nodes_executed']}")

    if result["node_results"]:
        print("\nNode Results:")
        for nr in result["node_results"]:
            node_icon = "✅" if nr["status"] == "success" else "❌"
            print(
                f"  {node_icon} {nr['node_id']}: {nr['status']} ({nr['duration_ms']:.1f}ms)"
            )
            if nr.get("error"):
                print(f"      ⚠️  {nr['error']}")

    if result.get("error"):
        print(f"\nError: {result['error']}")

    if result["final_output"]:
        print("\nFinal Output:")
        print(json.dumps(result["final_output"], indent=2, default=str)[:500])
        if len(json.dumps(result["final_output"])) > 500:
            print("  ... (truncated)")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG
        )
    else:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        )

    try:
        result = asyncio.run(run_pattern(args))
        print_result(result, args.json)

        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Execution cancelled by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
