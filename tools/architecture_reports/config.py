from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "config",
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

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoLayout:
    root: Path
    src_dirs: tuple[Path, ...]
    api_dirs: tuple[Path, ...]
    config_dirs: tuple[Path, ...]
    reports_dir: Path


def detect_root(start: Path | None = None) -> Path:
    """Resolve repo root as the directory containing pyproject.toml.

    Raises:
        RuntimeError: if pyproject.toml is not found walking upwards.
    """
    current = (start or Path(__file__)).resolve()
    for parent in (current,) + tuple(current.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Unable to locate repo root (pyproject.toml not found).")


def default_layout() -> RepoLayout:
    root = detect_root()
    src_dirs: tuple[Path, ...] = (
        root / "core",
        root / "services",
        root / "orchestrators",
        root / "api",
        root / "workers",
        root / "memory",
        root / "world_model",
        root / "ir_engine",
        root / "graph_adapter",
        root / "domain_tensor_bridge",
    )
    api_dirs: tuple[Path, ...] = (root / "api",)
    config_dirs: tuple[Path, ...] = (
        root / "config",
        root / "deploy",
        root / "docker",
    )
    reports_dir = root / "reports" / "architecture"
    return RepoLayout(
        root=root,
        src_dirs=src_dirs,
        api_dirs=api_dirs,
        config_dirs=config_dirs,
        reports_dir=reports_dir,
    )


def iter_python_files(dirs: Iterable[Path]) -> Iterable[Path]:
    """Yield all .py files under the given directories, excluding __pycache__."""
    for base in dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "caching", "dataclass", "filesystem", "operations", "tools"],
    "keywords": ["default", "detect", "files", "layout", "python", "repo", "root"],
    "business_value": "Implements RepoLayout for config functionality",
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
