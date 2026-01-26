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
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SuperpackLayout:
    """Configuration for superpack generation."""

    root: Path
    reports_dir: Path
    architecture_dir: Path  # For .txt inventory files

    # Tier T3 (High-Impact) directories
    governance_dirs: tuple[Path, ...]
    core_dirs: tuple[Path, ...]
    memory_dirs: tuple[Path, ...]
    orchestration_dirs: tuple[Path, ...]

    # Tier T2 directories
    api_dirs: tuple[Path, ...]
    telemetry_dirs: tuple[Path, ...]

    # Tier T3 (Infra)
    deploy_dirs: tuple[Path, ...]

    # Tier T1 directories
    tools_dirs: tuple[Path, ...]
    simulation_dirs: tuple[Path, ...]
    prompts_dirs: tuple[Path, ...]

    # Workers
    workers_dirs: tuple[Path, ...]

    # Protected files (cannot be modified without approval)
    protected_files: tuple[str, ...] = field(
        default=(
            "runtime/websocket_orchestrator.py",
            "core/agents/executor.py",
            "memory/substrate_service.py",
            "docker-compose.yml",
            "core/singleton_registry.py",
        )
    )


def detect_root(start: Path | None = None) -> Path:
    """Resolve repo root as the directory containing pyproject.toml."""
    current = (start or Path(__file__)).resolve()
    for parent in (current, *tuple(current.parents)):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Unable to locate repo root (pyproject.toml not found).")


def default_layout() -> SuperpackLayout:
    """Return the default L9 superpack layout."""
    root = detect_root()

    return SuperpackLayout(
        root=root,
        reports_dir=root / "reports",
        architecture_dir=root / "reports" / "architecture",
        # T3 Governance
        governance_dirs=(
            root / "core" / "governance",
            root / "core" / "packet_envelope",
        ),
        # T3 Core
        core_dirs=(
            root / "core" / "runtime",
            root / "core" / "kernels",
            root / "core" / "agents",
        ),
        # T3 Memory
        memory_dirs=(
            root / "memory",
            root / "world_model",
        ),
        # T3 Orchestration
        orchestration_dirs=(
            root / "orchestrators",
            root / "orchestration",
        ),
        # T2 API
        api_dirs=(
            root / "api",
            root / "clients",
            root / "adapters",
        ),
        # T2 Telemetry
        telemetry_dirs=(
            root / "telemetry",
            root / "grafana",
        ),
        # T3 Deploy
        deploy_dirs=(
            root / "deploy",
            root / "docker",
        ),
        # T1 Tools
        tools_dirs=(
            root / "tools",
            root / "scripts",
        ),
        # T1 Simulation
        simulation_dirs=(
            root / "simulation",
            root / "examples",
            root / "_archived",
        ),
        # T1 Prompts/Docs
        prompts_dirs=(
            root / "prompts",
            root / "private",
            root / "readme",
        ),
        # Workers
        workers_dirs=(root / "workers",),
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
    "component_id": "TOO-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "dataclass",
        "filesystem",
        "operations",
        "realtime",
        "tools",
    ],
    "keywords": ["default", "detect", "files", "layout", "python", "root", "superpack"],
    "business_value": "Implements SuperpackLayout for config functionality",
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
