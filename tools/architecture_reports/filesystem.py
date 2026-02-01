from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Filesystem",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "filesystem",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from pathlib import Path
from typing import TextIO


def ensure_reports_dir(path: Path) -> None:
    """
    Ensures that the reports directory exists at the specified path to facilitate report file creation.
    Args:
        path: Path object representing the directory where reports should be stored.
    """
    path.mkdir(parents=True, exist_ok=True)


def open_report(path: Path) -> TextIO:
    """
    Performs setup and opens a report file for writing within the filesystem report management context.

    Args:
        path: Path to the report file to be created or overwritten.

    Returns:
        A writable text stream for the specified report file.

    Raises:
        OSError: If the directory creation or file opening fails.
    """
    ensure_reports_dir(path.parent)
    # Overwrite atomically via write-then-replace if needed; here we keep simple.
    return path.open("w", encoding="utf-8")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-017",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["filesystem", "operations", "streaming", "tools", "utility"],
    "keywords": ["dir", "ensure", "filesystem", "open", "report", "reports"],
    "business_value": "Utility module for filesystem",
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
