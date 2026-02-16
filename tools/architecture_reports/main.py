from __future__ import annotations

import structlog

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Main",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "main",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse

from .architecture_report import generate_architecture
from .async_function_map_report import generate_async_function_map
from .class_definitions_report import generate_class_definitions
from .config import RepoLayout, default_layout
from .config_files_report import generate_config_files
from .file_metrics_report import generate_file_metrics
from .function_signatures_report import generate_function_signatures
from .imports_report import generate_imports
from .inheritance_graph_report import generate_inheritance_graph
from .pydantic_models_report import generate_pydantic_models
from .route_handlers_report import generate_route_handlers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def generate_all_reports(layout: RepoLayout | None = None) -> None:
    """Generate all architecture/* reports in a single run."""
    layout = layout or default_layout()

    generators: dict[str, Callable[[RepoLayout], None]] = {
        "architecture": generate_architecture,
        "function_signatures": generate_function_signatures,
        "class_definitions": generate_class_definitions,
        "file_metrics": generate_file_metrics,
        "async_function_map": generate_async_function_map,
        "inheritance_graph": generate_inheritance_graph,
        "pydantic_models": generate_pydantic_models,
        "config_files": generate_config_files,
        "route_handlers": generate_route_handlers,
        "imports": generate_imports,
    }

    for name, fn in generators.items():
        logger.info("[architecture reports] generating name...", name=name)
        fn(layout)
    logger.info("[architecture_reports] done.")


def main() -> None:
    """
    Generates architecture reports based on command-line arguments.
    Raises:
        argparse.ArgumentError: If invalid arguments are provided.
    """
    parser = argparse.ArgumentParser(
        description="Generate L9 architecture reports under reports/architecture/."
    )
    parser.add_argument(
        "--only",
        choices=[
            "architecture",
            "function_signatures",
            "class_definitions",
            "file_metrics",
            "async_function_map",
            "inheritance_graph",
            "pydantic_models",
            "config_files",
            "route_handlers",
            "imports",
        ],
        help="Generate only a single report type instead of all.",
    )
    args = parser.parse_args()

    layout = default_layout()

    if args.only:
        single = {
            "architecture": generate_architecture,
            "function_signatures": generate_function_signatures,
            "class_definitions": generate_class_definitions,
            "file_metrics": generate_file_metrics,
            "async_function_map": generate_async_function_map,
            "inheritance_graph": generate_inheritance_graph,
            "pydantic_models": generate_pydantic_models,
            "config_files": generate_config_files,
            "route_handlers": generate_route_handlers,
            "imports": generate_imports,
        }[args.only]
        single(layout)
    else:
        generate_all_reports(layout)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-026",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["cli", "metrics", "operations", "tools"],
    "keywords": ["all", "generate", "reports"],
    "business_value": "Utility module for main",
    "last_modified": "2026-01-31T22:21:45Z",
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
