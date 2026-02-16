"""
L9 Core Governance - Protected Files Policy Loader
===================================================

Single source of truth for protected file definitions.

Loads protected file policies from config/policies/protected_files.yaml.

GMP-104: Consolidates PROTECTED_BY_LCTO and SUBSYSTEM_PROTECTED definitions.

Version: 1.0.0
"""

from __future__ import annotations

import fnmatch

# ============================================================================
__dora_meta__ = {
    "component_name": "Protected Files Policy",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-19T22:00:00Z",
    "updated_at": "2026-01-19T22:00:00Z",
    "layer": "foundation",
    "domain": "governance",
    "module_name": "protected_files_policy",
    "type": "utility",
    "status": "active",
}
# ============================================================================

from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Cached Policy Data
# =============================================================================

_PROTECTED_FILES_POLICY: dict = {}


def _load_protected_files_policy() -> dict:
    """Load protected files policy from YAML file."""
    global _PROTECTED_FILES_POLICY

    if _PROTECTED_FILES_POLICY:
        return _PROTECTED_FILES_POLICY

    policy_path = (
        Path(__file__).parent.parent.parent
        / "config"
        / "policies"
        / "protected_files.yaml"
    )

    if policy_path.exists():
        try:
            with open(policy_path) as f:
                data = yaml.safe_load(f)
                _PROTECTED_FILES_POLICY = data.get("protected_files", {})
                logger.debug(
                    "protected_files_policy.loaded",
                    path=str(policy_path),
                    lcto_count=len(_PROTECTED_FILES_POLICY.get("lcto_controlled", [])),
                    subsystems=list(
                        _PROTECTED_FILES_POLICY.get("subsystems", {}).keys()
                    ),
                )
        except Exception as e:
            logger.warning(
                "protected_files_policy.load_failed",
                path=str(policy_path),
                error=str(e),
            )

    # Fallback to hardcoded defaults
    if not _PROTECTED_FILES_POLICY:
        _PROTECTED_FILES_POLICY = {
            "lcto_controlled": [
                {"path": "runtime/websocket_orchestrator.py"},
                {"path": "runtime/kernel_loader.py"},
                {"path": "docker-compose.yml"},
                {"path": "runtime/redis_client.py"},
                {"path": "core/agents/executor.py"},
            ],
            "subsystems": {
                "agents": {
                    "files": [
                        "core/agents/executor.py",
                        "core/agents/registry.py",
                        "core/agents/__init__.py",
                    ]
                },
                "memory": {
                    "files": [
                        "memory/substrate_service.py",
                        "memory/substrate_dag.py",
                        "memory/__init__.py",
                    ]
                },
                "tools": {
                    "files": [
                        "core/tools/registry_adapter.py",
                        "core/tools/tool_graph.py",
                        "core/tools/__init__.py",
                    ]
                },
            },
            "protected_patterns": [
                {"pattern": "Dockerfile", "reason": "Root container image"},
                {"pattern": "Dockerfile.*", "reason": "Variant container images"},
                {
                    "pattern": ".github/workflows/*.yml",
                    "reason": "CI pipeline definitions",
                },
                {
                    "pattern": ".github/scripts/*.py",
                    "reason": "CI and governance scripts",
                },
                {
                    "pattern": "requirements*.txt",
                    "reason": "Python dependency lockfiles",
                },
                {"pattern": "pyproject.toml", "reason": "Project and tool config"},
                {"pattern": "Makefile", "reason": "Build and task entrypoints"},
                {"pattern": "runtime/*", "reason": "Runtime core"},
                {
                    "pattern": "scripts/deployment/*",
                    "reason": "Deploy and release scripts",
                },
            ],
        }
        logger.debug("protected_files_policy.using_fallback")

    return _PROTECTED_FILES_POLICY


def _get_protected_patterns() -> list[str]:
    """Return list of fnmatch-style patterns from policy."""
    policy = _load_protected_files_policy()
    raw = policy.get("protected_patterns", [])
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict) and "pattern" in item:
            out.append(item["pattern"])
        elif isinstance(item, str):
            out.append(item)
    return out


# =============================================================================
# Public API
# =============================================================================


def get_protected_patterns() -> list[str]:
    """Get protected file patterns (fnmatch-style). Applies to all including L."""
    return _get_protected_patterns()


def get_lcto_controlled_files() -> set[str]:
    """Get set of LCTO-controlled file paths.

    Returns:
        Set of file paths that L (CTO) controls
    """
    policy = _load_protected_files_policy()
    lcto = policy.get("lcto_controlled", [])
    return {item["path"] if isinstance(item, dict) else item for item in lcto}


def get_subsystem_protected_files() -> dict[str, set[str]]:
    """Get subsystem-protected files by subsystem name.

    Returns:
        Dict mapping subsystem name to set of protected file paths
    """
    policy = _load_protected_files_policy()
    subsystems = policy.get("subsystems", {})
    return {name: set(config.get("files", [])) for name, config in subsystems.items()}


def get_all_protected_files() -> set[str]:
    """Get all protected file paths.

    Returns:
        Set of all protected file paths (LCTO + subsystem)
    """
    lcto = get_lcto_controlled_files()
    subsystem_files = set()
    for files in get_subsystem_protected_files().values():
        subsystem_files |= files
    return lcto | subsystem_files


def is_protected(file_path: str) -> bool:
    """Check if a file is protected.

    Applies to everyone including L (CTO). Checks exact paths and fnmatch patterns.

    Args:
        file_path: Path to check (use forward slashes, no leading ./)

    Returns:
        True if file is protected
    """
    # Normalize: strip leading ./ only (do not strip leading . so .github/ is preserved)
    normalized = file_path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in get_all_protected_files():
        return True
    for pat in _get_protected_patterns():
        if fnmatch.fnmatch(normalized, pat):
            return True
    return False


def is_lcto_controlled(file_path: str) -> bool:
    """Check if a file is LCTO-controlled.

    Args:
        file_path: Path to check

    Returns:
        True if file is LCTO-controlled
    """
    return file_path in get_lcto_controlled_files()


def get_file_subsystem(file_path: str) -> str | None:
    """Get the subsystem that owns a file.

    Args:
        file_path: Path to check

    Returns:
        Subsystem name or None if not in a subsystem
    """
    for subsystem, files in get_subsystem_protected_files().items():
        if file_path in files:
            return subsystem
    return None


# =============================================================================
# Module-level constants (backward compatibility)
# =============================================================================

PROTECTED_BY_LCTO: set[str] = get_lcto_controlled_files()
SUBSYSTEM_PROTECTED: dict[str, set[str]] = get_subsystem_protected_files()
ALL_PROTECTED: set[str] = get_all_protected_files()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-168",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "config",
        "debugging",
        "filesystem",
        "foundation",
        "governance",
        "logging",
        "realtime",
        "utility",
    ],
    "keywords": [
        "all",
        "controlled",
        "definitions",
        "files",
        "governance",
        "lcto",
        "loader",
        "policies",
    ],
    "business_value": "Utility module for protected files policy",
    "last_modified": "2026-01-31T22:21:47Z",
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
