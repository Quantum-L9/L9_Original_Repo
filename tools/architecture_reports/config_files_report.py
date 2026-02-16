from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Config Files Report",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-31T22:21:45Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "config_files_report",
    "type": "config",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from typing import TYPE_CHECKING

from .filesystem import open_report

if TYPE_CHECKING:
    from .config import RepoLayout

_CONFIG_EXT = {".yml", ".yaml", ".toml", ".ini", ".json", ".env", ".cfg"}


def generate_config_files(layout: RepoLayout) -> None:
    """Generate config_files.txt listing config-like files and their paths."""
    output = layout.reports_dir / "config_files.txt"

    entries: list[str] = []

    for base in layout.config_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in _CONFIG_EXT:
                entries.append(path.relative_to(layout.root).as_posix())

    # top-level configs
    for name in (
        "pyproject.toml",
        "pytest.ini",
        "codecov.yml",
        "sonar-project.properties",
    ):
        path = layout.root / name
        if path.is_file():
            entries.append(path.relative_to(layout.root).as_posix())

    entries.sort()

    with open_report(output) as f:
        for rel in entries:
            f.write(f"{rel}\n")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-014",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["config", "operations", "testing", "tools"],
    "keywords": ["files", "generate", "report"],
    "business_value": "Utility module for config files report",
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
