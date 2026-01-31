from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "File Metrics Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "file_metrics_report",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


@dataclass
class FileMetrics:
    """
    Calculates and stores code metrics for a source file, including relative path, lines of code, and complexity.

    Args:
        rel_path: The relative file path within the project.
        loc: The total number of lines of code in the file.
        complexity: The cyclomatic complexity measure of the file.
    """

    rel_path: str
    loc: int
    complexity: int


def _compute_loc(text: str) -> int:
    """
    Calculates the number of lines of code in a source text excluding comments and blank lines for code metrics analysis.

    Args:
        text: The source code as a string to analyze.

    Returns:
        The count of code lines excluding comments and empty lines.
    """
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def _compute_complexity(text: str) -> int:
    """Very rough cyclomatic complexity heuristic."""
    keywords = ("if ", "for ", "while ", "and ", "or ", "elif ", "except ", "with ")
    complexity = 1
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        complexity += sum(1 for kw in keywords if kw in stripped)
    return complexity


def generate_file_metrics(layout: RepoLayout) -> None:
    """Generate file_metrics.txt with LOC and complexity per Python file."""
    output = layout.reports_dir / "file_metrics.txt"
    metrics: list[FileMetrics] = []

    for path in iter_python_files(layout.src_dirs):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        loc = _compute_loc(text)
        complexity = _compute_complexity(text)
        rel = path.relative_to(layout.root).as_posix()
        metrics.append(FileMetrics(rel, loc, complexity))

    metrics.sort(key=lambda m: m.loc, reverse=True)

    with open_report(output) as f:
        for m in metrics:
            f.write(f"{m.rel_path}  LOC={m.loc}  complexity={m.complexity}\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-006",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["dataclass", "metrics", "operations", "tools"],
    "keywords": ["generate", "metrics", "report"],
    "business_value": "Implements FileMetrics for file metrics report functionality",
    "last_modified": "2026-01-25T14:49:28Z",
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
