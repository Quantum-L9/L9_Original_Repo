"""
Thin wrapper around ADREnforcementValidator for CI and CLI use.
"""

from __future__ import annotations

import structlog

# ============================================================================

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Adr Scanner",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-24T16:03:39Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "adr_scanner",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import sys
from pathlib import Path

from .adr_enforcer import ADREnforcementValidator


def main() -> int:
    """
    Performs ADR repository scanning using ADREnforcementValidator with CLI options.


    Returns:
        Exit status code as integer, where 0 indicates success.

    Raises:
        argparse.ArgumentError: If argument parsing fails.
    """
    import argparse

    parser = argparse.ArgumentParser(description="L9 ADR Repository Scanner")
    parser.add_argument(
        "--output",
        type=str,
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any violations are found.",
    )

    args = parser.parse_args()

    validator = ADREnforcementValidator(repo_root=Path.cwd())
    report = validator.scan_repo()
    data = report.to_dict()
    logger.info("output", value=json.dumps(data, indent=2))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    if args.strict and report.total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "cli", "filesystem", "operations", "serialization", "tools"],
    "keywords": ["adr", "scanner"],
    "business_value": "Utility module for adr scanner",
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
