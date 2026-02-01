"""
L9 Research Agent Facade
========================

Simplified interface to L9's research infrastructure.

This facade provides easy-to-use functions for:
1. Running research queries
2. Generating superprompts for Perplexity
3. Extracting code facts from modules

Architecture Note:
- This is a thin wrapper over `services.research/`
- The heavy lifting is done by the LangGraph-based research system
- This facade simplifies common workflows
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Facade",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T17:12:30Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "research_facade",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API"],
        "memory_layers": [],
        "imported_by": ["agents.research_agent.__init__"],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

log = structlog.get_logger(__name__)


# =============================================================================
# Research Execution
# =============================================================================


async def run_research(
    query: str,
    user_id: str = "cursor_agent",
    deep: bool = False,
) -> dict[str, Any]:
    """
    Run a research query through the full LangGraph pipeline.

    This executes:
    1. PlannerAgent → decompose query into steps
    2. ResearcherAgent → gather evidence (Perplexity, web, etc.)
    3. CriticAgent → evaluate quality
    4. InsightExtractor → store to memory substrate

    Args:
        query: Research question
        user_id: User identifier for tracking
        deep: If True, use sonar-deep-research (slower, more comprehensive)

    Returns:
        Research result dict with:
        - summary: Synthesized findings
        - sources: List of source URLs
        - evidence_count: Number of evidence items
        - quality_score: Critic's quality score (0-1)
        - thread_id: Thread for follow-up queries

    Example:
        result = await run_research("What are LLM memory architectures?")
        print(result["summary"])  # noqa: ADR-0019
    """
    from services.research import run_research as _run_research

    log.info("Starting research via facade", query=query[:50], deep=deep)

    return await _run_research(
        query=query,
        user_id=user_id,
        thread_id=str(uuid4()),
    )


async def run_quick_research(
    query: str,
    model: str = "sonar-pro",
) -> str:
    """
    Run a quick Perplexity query without the full pipeline.

    Use for:
    - Quick fact checks
    - Simple questions
    - When you don't need the full research graph

    Args:
        query: Question to ask
        model: Perplexity model (sonar, sonar-pro, sonar-reasoning)

    Returns:
        String response from Perplexity

    Example:
        answer = await run_quick_research("What is LangGraph?")
    """
    from services.research.tools.perplexity_client import (
        PerplexityClient,
        PerplexityModel,
        PerplexityRequest,
    )

    client = PerplexityClient()

    model_enum = PerplexityModel(model) if model else PerplexityModel.SONAR_PRO

    request = PerplexityRequest(
        query=query,
        model=model_enum,
    )

    response = await client.query(request)

    return response.content


# =============================================================================
# Superprompt Generation
# =============================================================================


def generate_superprompt(
    path: str,
    template: str = "readme",
    title: str | None = None,
) -> str:
    """
    Generate a superprompt for Perplexity by extracting facts from code.

    This uses AST parsing to extract:
    - Classes (with methods, fields, types)
    - Functions (with signatures, docstrings)
    - API routes
    - Pydantic models
    - Constants

    Then embeds these facts into a superprompt template.

    Args:
        path: Module path (e.g., "agents/cursor", "memory/")
        template: Template type: "readme", "analysis", "research"
        title: Optional custom title

    Returns:
        Complete superprompt ready to paste into Perplexity

    Example:
        prompt = generate_superprompt("agents/cursor", template="readme")
        # Copy prompt to Perplexity

    See Also:
        scripts/generate_readme_superprompt.py for CLI version
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

    try:
        from generate_readme_superprompt import extract_subsystem_facts
        from generate_readme_superprompt import (
            generate_superprompt as _generate_superprompt,
        )

        repo_root = Path(__file__).parent.parent.parent

        # Generate title if not provided
        if not title:
            parts = path.strip("/").split("/")
            title = parts[-1].replace("_", " ").replace("-", " ").title() + " Module"

        # Extract facts
        facts = extract_subsystem_facts(repo_root, path)

        # Generate superprompt
        return _generate_superprompt(facts, title)

    except ImportError as e:
        log.error("Failed to import superprompt generator", error=str(e))
        raise ImportError(
            "Could not import generate_readme_superprompt.py. "
            "Ensure scripts/generate_readme_superprompt.py exists."
        ) from e


def extract_facts(path: str) -> dict[str, Any]:
    """
    Extract code facts from a module using AST parsing.

    Returns a dictionary with:
    - classes: List of class info (name, methods, fields, etc.)
    - functions: List of function info (name, signature, docstring)
    - routes: API routes (method, path, handler)
    - pydantic_models: Pydantic/dataclass models
    - files: List of Python files
    - imports: List of imports

    Args:
        path: Module path relative to repo root

    Returns:
        Dict with extracted facts

    Example:
        facts = extract_facts("core/agents")
        print(f"Found {len(facts['classes'])} classes")  # noqa: ADR-0019
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

    try:
        from generate_readme_superprompt import extract_subsystem_facts

        repo_root = Path(__file__).parent.parent.parent
        facts = extract_subsystem_facts(repo_root, path)

        # Convert dataclasses to dicts for JSON serialization
        return {
            "path": facts.path,
            "files": facts.files,
            "classes": [
                {
                    "name": c.name,
                    "file": c.file,
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                    "docstring": c.docstring,
                    "bases": c.bases,
                    "is_pydantic": c.is_pydantic,
                    "methods": c.methods,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.type_annotation,
                            "default": f.default,
                        }
                        for f in c.fields
                    ],
                }
                for c in facts.classes
            ],
            "functions": [
                {
                    "name": f.name,
                    "file": f.file,
                    "line": f.line,
                    "signature": f.signature,
                    "docstring": f.docstring,
                    "is_async": f.is_async,
                    "return_type": f.return_type,
                }
                for f in facts.functions
            ],
            "routes": [
                {
                    "method": r.method,
                    "path": r.path,
                    "function": r.function_name,
                    "file": r.file,
                }
                for r in facts.routes
            ],
            "pydantic_models": [m.name for m in facts.pydantic_models],
            "imports": facts.imports,
            "constants": facts.constants,
        }

    except ImportError as e:
        log.error("Failed to import fact extractor", error=str(e))
        raise


# =============================================================================
# Perplexity Workflow Helpers
# =============================================================================


def save_perplexity_output(
    content: str,
    project: str,
    filename: str,
) -> Path:
    """
    Save Perplexity output to the research results folder.

    SOP: All research outputs go to:
    agents/cursor/perplexity_research_results/<date> - <project>/

    Args:
        content: Perplexity response content
        project: Project/folder name (without date prefix)
        filename: File name for the output

    Returns:
        Path to saved file

    Example:
        path = save_perplexity_output(
            content=perplexity_response,
            project="readme-generation-gmp100",
            filename="README-core-agents.md"
        )
    """
    from datetime import datetime

    # Build path per SOP
    repo_root = Path(__file__).parent.parent.parent
    date_str = datetime.now().strftime("%m-%d-%Y")
    folder_name = f"{date_str} - {project}"

    output_dir = repo_root / "agents/cursor/perplexity_research_results" / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename
    output_path.write_text(content)

    log.info("Saved Perplexity output", path=str(output_path))

    return output_path


# =============================================================================
# CLI Entry Points (for shell scripts)
# =============================================================================


def main():
    """CLI entry point."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="L9 Research Agent")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # research command
    research_parser = subparsers.add_parser("research", help="Run research query")
    research_parser.add_argument("query", help="Research question")
    research_parser.add_argument(
        "--deep", action="store_true", help="Use deep research"
    )

    # quick command
    quick_parser = subparsers.add_parser("quick", help="Quick Perplexity query")
    quick_parser.add_argument("query", help="Question")

    # superprompt command
    superprompt_parser = subparsers.add_parser(
        "superprompt", help="Generate superprompt"
    )
    superprompt_parser.add_argument("path", help="Module path")
    superprompt_parser.add_argument("--output", "-o", help="Output file")

    # facts command
    facts_parser = subparsers.add_parser("facts", help="Extract code facts")
    facts_parser.add_argument("path", help="Module path")

    args = parser.parse_args()

    if args.command == "research":
        result = asyncio.run(run_research(args.query, deep=args.deep))
        print(result.get("summary", "No summary"))  # noqa: ADR-0019

    elif args.command == "quick":
        answer = asyncio.run(run_quick_research(args.query))
        print(answer)  # noqa: ADR-0019

    elif args.command == "superprompt":
        prompt = generate_superprompt(args.path)
        if args.output:
            Path(args.output).write_text(prompt)
            print(f"Written to {args.output}")  # noqa: ADR-0019
        else:
            print(prompt)  # noqa: ADR-0019

    elif args.command == "facts":
        import json

        facts = extract_facts(args.path)
        print(json.dumps(facts, indent=2, default=str))  # noqa: ADR-0019

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-022",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "agent-execution",
        "api",
        "async",
        "cli",
        "filesystem",
        "intelligence",
        "logging",
        "serialization",
    ],
    "keywords": [
        "agent",
        "extract",
        "facade",
        "facts",
        "generate",
        "perplexity",
        "quick",
        "research",
    ],
    "business_value": "1. Running research queries 2. Generating superprompts for Perplexity 3. Extracting code facts from modules This is a thin wrapper over `services.research/` The heavy lifting is done by the LangGraph-",
    "last_modified": "2026-01-31T22:27:11Z",
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
